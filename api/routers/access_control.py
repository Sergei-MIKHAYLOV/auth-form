# api/routers/access_control.py
from fastapi import APIRouter, Depends, HTTPException, status, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from db.db_init import get_db
from db.models import User, UserRole, Role, AccessRule, Resource
from api.models import UserSchema, AccessRuleCreateRequest, AccessRuleUpdateRequest, AccessRuleResponse
from api.deps import check_has_role, check_permission, get_object_or_404, check_not_self, check_not_last_role, is_staff_account
from api.utils import create_crud_router


access_control_router = APIRouter(prefix='/admin')

# ------------- Роутеры из фабрики ('roles', 'resources') -------------

roles_router = create_crud_router(model=Role, 
                                  resource_name='roles',
                                  dependencies=[Depends(check_has_role(roles='admin'))])

resources_router = create_crud_router(model=Resource,
                                      resource_name='resources',
                                      dependencies=[Depends(check_has_role(roles='admin'))])

access_control_router.include_router(roles_router)
access_control_router.include_router(resources_router)





# ---------------------------- Роутеры 'users' ----------------------------

@access_control_router.get('/users/search', summary='Поиск пользователей по email/name',
                           dependencies=[Depends(check_has_role(roles=['admin', 'moderator']))])
async def search_users(email: str | None = Query(None),
                       name: str | None = Query(None),
                       db: AsyncSession = Depends(get_db)): 
    '''
    Поиск пользователей по email или имени (только для `admin` или `moderator`).
    '''
    
    query = select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))
    
    if email:
        query = query.where(User.email.ilike(f'%{email}%'))
    if name:
        query = query.where(User.name.ilike(f'%{name}%'))
    
    result = await db.execute(query)
    users = result.scalars().all()    
    users_list = [UserSchema.model_validate(u) for u in users]
    
    return {'count': len(users_list), 'users': users_list}





@access_control_router.patch('/users/{user_id}/status', summary='Заблокировать/разблокировать пользователя')
async def change_user_status(user_id: int,
                             is_active: bool = Form(...),
                             current_user: User = Depends(check_permission('users', 'user_ban')),
                             db: AsyncSession = Depends(get_db)):
    '''
    Блокировка / разблокировка аккаунта пользователя.
    Нельзя заблокировать самого себя или `admin` / `moderator`.
    '''
    
    check_not_self(current_user.id, user_id, action='заблокировать')
    user = await get_object_or_404(db, User, user_id, 'Пользователь не найден')

    if not is_active and is_staff_account(user):
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'Аккаунты с ролями `admin` и `moderator` не подлежат блокировке. Сначала необходимо убрать роль.')

    user.is_active = is_active
    await db.commit()
    
    action = 'разблокирован' if is_active else 'заблокирован'
    return {'message': f'Пользователь {user.name} ({user.email}) - {action.upper()}'}




@access_control_router.patch('/users/{user_id}/role', summary='Добавить роль пользователю')
async def add_user_role(user_id: int,
                        role_id: int = Form(...),
                        current_user: User = Depends(check_has_role(roles='admin')),
                        db: AsyncSession = Depends(get_db)):
    '''
    Добавить роль пользователю (только для `admin`).  
    `admin` не может изменить роль самому себе.
    '''
    
    check_not_self(current_user.id, user_id, action='изменить роль')
    user = await get_object_or_404(db, User, user_id, 'Пользователь не существует')
    role = await get_object_or_404(db, Role, role_id, 'Роль не найдена')
    
    # Проверка, нет ли уже такой роли
    result = await db.execute(select(UserRole)
                              .where(UserRole.user_id == user_id,
                                     UserRole.role_id == role_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='У пользователя уже есть эта роль')
    
    user_role = UserRole(user_id=user_id, role_id=role_id)
    db.add(user_role)
    await db.commit()
    
    return {'message': f'Роль `{role.name}` добавлена пользователю {user.name} ({user.email})'}




@access_control_router.delete('/users/{user_id}/role/{role_id}', summary='Удалить роль у пользователя')
async def remove_user_role(user_id: int,
                           role_id: int,
                           current_user: User = Depends(check_has_role(roles='admin')),
                           db: AsyncSession = Depends(get_db)):
    '''
    Удалить роль пользователю (только для `admin`).  
    `admin` не может удалить роль самому себе.
    '''
    user = await get_object_or_404(db, User, user_id, 'Пользователь не существует')
    role = await get_object_or_404(db, Role, role_id, 'Роль не найдена')
    check_not_self(current_user.id, user_id, action='удалить роль')
    check_not_last_role(user)
    
    # Проверка наличия удаляемой роли
    result = await db.execute(select(UserRole)
                              .where(UserRole.user_id == user_id,
                                     UserRole.role_id == role_id))
    user_role = result.scalar_one_or_none()
    if not user_role:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'У пользователя {user.name} ({user.email}) нет роли `{role.name}`')
    
    await db.delete(user_role)
    await db.commit()
    
    return {'message': f'Роль `{role.name}` удалена у пользователя {user.name} ({user.email})'}




@access_control_router.delete('/users/{user_id}', summary='Перманентное удаление пользователя')
async def delete_user(user_id: int,
                      current_user: User = Depends(check_has_role(roles='admin')),
                      db: AsyncSession = Depends(get_db)):
    '''
    Полное удаление пользователя из БД (только для `admin`).
    `admin` не может удалить самого себя.
    '''
    
    check_not_self(current_user.id, user_id, action='удалить аккаунт')
    user = await get_object_or_404(db, User, user_id)
    
    await db.delete(user)
    await db.commit()
    user_info = f'{user.family_name} {user.name} {user.patronymic}, e-mail: {user.email}' 
    
    return {'message': f'Из базы данных удален пользователь `{user_info}`'}









# ---------------------------- Роутеры 'access-rules' ----------------------------


@access_control_router.get('/access-rules', summary='Получить список всех правил доступа',
                           dependencies=[Depends(check_has_role(roles=['admin']))])
async def get_access_rules(db: AsyncSession = Depends(get_db)):
    '''
    Получить список всех правил доступа с именами ролей и ресурсов (только для `admin`).
    '''
    
    result = await db.execute(select(AccessRule)
                              .options(selectinload(AccessRule.role),
                                       selectinload(AccessRule.resource)))
    rules = result.scalars().all()   
    rules_list = [AccessRuleResponse.model_validate(r) for r in rules]
    
    return {'count': len(rules_list), 'rules': rules_list}




@access_control_router.post('/access-rules', summary='Создать правило доступа',
                            dependencies=[Depends(check_has_role(roles=['admin']))])
async def create_access_rule(request: AccessRuleCreateRequest,
                             db: AsyncSession = Depends(get_db)):
    '''
    Создать новое правило доступа (только для `admin`).
    '''
    
    role = await get_object_or_404(db, Role, request.role_id, 'Роль не найдена')
    resource = await get_object_or_404(db, Resource, request.resource_id, 'Ресурс не найден')
    
    # Проверка дубликатов правила
    result = await db.execute(select(AccessRule)
                              .where(AccessRule.role_id == request.role_id,
                                     AccessRule.resource_id == request.resource_id))
    if result.scalar_one_or_none():
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f'Правило уже существует для роли `{role.name}` и ресурса `{resource.name}`')
    
    rule = AccessRule(**request.model_dump())
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    
    return {'message': f'Создано новое правило доступа для ресурса `{resource.name}`', 'rule_id': rule.id}




@access_control_router.patch('/access-rules/{rule_id}', summary='Обновить правило доступа',
                             dependencies=[Depends(check_has_role(roles=['admin']))])
async def update_access_rule(rule_id: int,
                             request: AccessRuleUpdateRequest,
                             db: AsyncSession = Depends(get_db)):
    '''
    Обновить существующее правило доступа (только для `admin`).
    '''
    
    rule = await get_object_or_404(db, AccessRule, rule_id)
    
    update_data = request.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    
    return {'message': 'Правило доступа обновлено', 'rule_id': rule.id}




@access_control_router.delete('/access-rules/{rule_id}', summary='Удалить правило доступа',
                              dependencies=[Depends(check_has_role(roles=['admin']))])
async def delete_access_rule(rule_id: int,
                             db: AsyncSession = Depends(get_db)):
    '''
    Удалить правило доступа (только для `admin`).
    '''
    
    rule = await get_object_or_404(db, AccessRule, rule_id)
    
    await db.delete(rule)
    await db.commit()
    
    return {'message': 'Правило доступа удалено'}