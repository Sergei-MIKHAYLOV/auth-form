from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from db.models import User, UserRole, Role
from api.models import UserSchema
from api.deps import get_object_or_404, is_staff_account, check_not_self, check_not_last_role
from dataclasses import dataclass


@dataclass
class RolesInfo:
    user: User
    role: Role
    user_role: UserRole


class UserRoleService:
    def __init__(self, db: AsyncSession):
        self.db = db
    
    
    async def request_role_change(self,
                                  user_id: int,
                                  role_id: int,
                                  current_user_id: int,
                                  action: str) -> RolesInfo:
        
        user = await get_object_or_404(self.db, User, user_id, 'Пользователь не существует')
        role = await get_object_or_404(self.db, Role, role_id, 'Роль не найдена')
        check_not_self(current_user_id, user_id, action=action)

        query = await self.db.execute(select(UserRole)
                                      .where(UserRole.user_id == user_id,
                                             UserRole.role_id == role_id))
        user_role = query.scalar_one_or_none()

        result = RolesInfo(user, role, user_role)

        return result

    

    async def search(self,
                     email: str | None,
                     name: str | None) -> User:
        
        query = select(User).options(selectinload(User.user_roles).selectinload(UserRole.role))
    
        if email:
            query = query.where(User.email.ilike(f'%{email}%'))
        if name:
            query = query.where(User.name.ilike(f'%{name}%'))
        
        result = await self.db.execute(query)
        users = result.scalars().all()    
        users_list = [UserSchema.model_validate(u) for u in users]

        return users_list
    

    async def block_user(self, 
                         user_id: int, 
                         is_active: bool, 
                         current_user_id: int) -> User:

        check_not_self(current_user_id, user_id, action='заблокировать')

        user = await get_object_or_404(self.db, User, user_id, 'Пользователь не найден')

        if not is_active and is_staff_account(user):
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f'Аккаунты с ролями `admin` и `moderator` не подлежат блокировке. Сначала необходимо убрать роль.')
        
        user.is_active = is_active
        await self.db.commit()
        await self.db.refresh(user)
        
        return user
    
    
    async def add_role(self, 
                       user_id: int, 
                       role_id: int, 
                       current_user_id: int) -> UserRole:
        
        response = await self.request_role_change(user_id, role_id, current_user_id, action='изменить роль')
        
        if response.user_role:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='У пользователя уже есть эта роль')
        
        user_role = UserRole(user_id=user_id, role_id=role_id)
        self.db.add(user_role)
        await self.db.commit()
        
        return RolesInfo(response.user, response.role, user_role)
    
    
    async def delete_role(self, 
                          user_id: int, 
                          role_id: int, 
                          current_user_id: int) -> UserRole:
        
        response = await self.request_role_change(user_id, role_id, current_user_id, action='удалить роль')
        many_roles = check_not_last_role(response.user)
        
        if not many_roles:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                        detail=f'Нельзя удалить единственную роль пользователя. Добавьте другую роль для удаления текущей')
        
        if not response.user_role:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f'У пользователя {response.user.name} ({response.user.email}) нет роли `{response.role.name}`')
        
        
        await self.db.delete(response.user_role)
        await self.db.commit()
        
        return RolesInfo(response.user, response.role, response.user_role)
    

    async def delete_user(self,
                          user_id: int,
                          current_user_id: int) -> str:

        check_not_self(current_user_id, user_id, action='удалить аккаунт')
        user = await get_object_or_404(self.db, User, user_id)
        user_info = f'{user.family_name} {user.name} {user.patronymic}, e-mail: {user.email}'

        await self.db.delete(user)
        await self.db.commit()
        
        return user_info