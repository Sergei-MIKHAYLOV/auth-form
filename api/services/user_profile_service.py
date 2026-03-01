from sqlalchemy.ext.asyncio import AsyncSession
from fastapi import HTTPException, status
from db.models import User
from api.models import UserSchema
from api.deps import is_staff_account, verify_password, hash_password
from api.utils import validate_email_or_400


class UserProfileService:
    def __init__(self, db: AsyncSession):
        self.db = db
    

    async def edit_profile(self,
                           email: str,
                           name: str,
                           family_name: str,
                           patronymic: str,
                           password1: str,
                           password2: str,
                           current_user: User) -> dict:
        
        validate_email_or_400(email)

        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail='Поле "email" является обязательным')
        if not name:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Поле "Имя" является обязательным')
        
        if password1 or password2:
            if password1 != password2:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail='Пароли не совпадают')
            if len(password1) < 3:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail='Пароль должен быть не короче 3 символов')
            if verify_password(password1, current_user.password):
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                    detail='Новый пароль совпадает с текущим')
            current_user.password = hash_password(password1)

        current_user.email = email
        current_user.name = name
        current_user.family_name = family_name.strip() or None
        current_user.patronymic = patronymic.strip() or None

        await self.db.commit()
        user = UserSchema.model_validate(current_user)

        return user.model_dump()


    async def block_user(self,
                         current_user: User) -> None:

        if not is_staff_account(current_user):
            current_user.is_active = False
            await self.db.commit()
            return current_user
        
        raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                    detail='Непредвиденная ошибка при попытке блокировки аккаунта пользователем')