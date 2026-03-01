from fastapi import APIRouter, Depends, Form, Query
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from db.models import User, Role, Resource
from api.models import AccessRuleCreateRequest, AccessRuleUpdateRequest
from api.services.user_role_service import UserRoleService
from api.services.access_rule_service import AccessRuleService
from api.deps import check_has_role, check_permission
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

    service = UserRoleService(db)
    users_list = await service.search(email, name)
    
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
    
    service = UserRoleService(db)
    user = await service.block_user(user_id, is_active, current_user.id)    
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
    
    service = UserRoleService(db)
    response = await service.add_role(user_id, role_id, current_user.id) 
    
    return {'message': f'Роль `{response.role.name}` добавлена пользователю {response.user.name} ({response.user.email})'}



@access_control_router.delete('/users/{user_id}/role/{role_id}', summary='Удалить роль у пользователя')
async def remove_user_role(user_id: int,
                           role_id: int,
                           current_user: User = Depends(check_has_role(roles='admin')),
                           db: AsyncSession = Depends(get_db)):
    '''
    Удалить роль пользователю (только для `admin`).  
    `admin` не может удалить роль самому себе.
    '''

    service = UserRoleService(db)
    response = await service.delete_role(user_id, role_id, current_user.id) 
    
    return {'message': f'Роль `{response.role.name}` удалена у пользователя {response.user.name} ({response.user.email})'}



@access_control_router.delete('/users/{user_id}', summary='Перманентное удаление пользователя')
async def delete_user(user_id: int,
                      current_user: User = Depends(check_has_role(roles='admin')),
                      db: AsyncSession = Depends(get_db)):
    '''
    Полное удаление пользователя из БД (только для `admin`).
    `admin` не может удалить самого себя.
    '''
    
    service = UserRoleService(db)
    user_info = await service.delete_user(user_id, current_user.id) 
    
    return {'message': f'Из базы данных удален пользователь `{user_info}`'}





# ---------------------------- Роутеры 'access-rules' ----------------------------


@access_control_router.get('/access-rules', summary='Получить список всех правил доступа',
                           dependencies=[Depends(check_has_role(roles=['admin']))])
async def get_access_rules(db: AsyncSession = Depends(get_db)):
    '''
    Получить список всех правил доступа с именами ролей и ресурсов (только для `admin`).
    '''
    
    service = AccessRuleService(db)
    rules_list = await service.get_access_rules()
    
    return {'count': len(rules_list), 'rules': rules_list}




@access_control_router.post('/access-rules', summary='Создать правило доступа',
                            dependencies=[Depends(check_has_role(roles=['admin']))])
async def create_access_rule(request: AccessRuleCreateRequest,
                             db: AsyncSession = Depends(get_db)):
    '''
    Создать новое правило доступа (только для `admin`).
    '''
    
    service = AccessRuleService(db)
    new_rule = await service.create_access_rule(request)
    
    return {'message': f'Создано новое правило доступа для ресурса `{new_rule.resource_name}`', 'rule_id': new_rule.rule_id}




@access_control_router.patch('/access-rules/{rule_id}', summary='Обновить правило доступа',
                             dependencies=[Depends(check_has_role(roles=['admin']))])
async def update_access_rule(rule_id: int,
                             request: AccessRuleUpdateRequest,
                             db: AsyncSession = Depends(get_db)):
    '''
    Обновить существующее правило доступа (только для `admin`).
    '''

    service = AccessRuleService(db)
    await service.update_access_rule(rule_id, request)
    
    return {'message': 'Правило доступа обновлено', 'rule_id': rule_id}




@access_control_router.delete('/access-rules/{rule_id}', summary='Удалить правило доступа',
                              dependencies=[Depends(check_has_role(roles=['admin']))])
async def delete_access_rule(rule_id: int,
                             db: AsyncSession = Depends(get_db)):
    '''
    Удалить правило доступа (только для `admin`).
    '''

    service = AccessRuleService(db)
    await service.delete_access_rule(rule_id)
    
    return {'message': 'Правило доступа удалено'}
