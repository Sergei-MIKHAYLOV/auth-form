from fastapi import APIRouter, HTTPException, status, Depends, Form
from api.models import UserSchema
from api.deps import hash_password, verify_password, get_current_user, is_staff_account
from api.utils import is_correct_email

from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from db.models import User

import logging

logger = logging.getLogger(__name__)


users_router = APIRouter()

@users_router.get('/me', summary='Вывод информации пользователя "О себе"')
def read_own_info(current_user: User = Depends(get_current_user)):
    self_info = UserSchema.model_validate(current_user)
    return {'message': 'Информация о текущем пользователе',
            'user': self_info.model_dump()}




@users_router.patch('/me', summary='Редактировать профиль пользователя')
async def update_profile(email: str = Form(...),
                   name: str = Form(...),
                   family_name: str = Form(''),
                   patronymic: str = Form(''),
                   password1: str = Form(''),
                   password2: str = Form(''),
                   current_user: User = Depends(get_current_user),
                   db: AsyncSession = Depends(get_db)):
    
    is_correct_email(email)

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

    await db.commit()
    user = UserSchema.model_validate(current_user)

    return {'message': 'Профиль успешно обновлен',
            'user': user.model_dump()}




@users_router.delete('/me', summary='Блокировка своего аккаунта пользователем')
async def block_account(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):

    if not is_staff_account(current_user):
        current_user.is_active = False
        await db.commit()
        return {'message': 'Ваш аккаунт заблокирован. Для разблокировки обратитесь в тех. поддержку'}
    
    raise HTTPException(status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                                detail='Непредвиденная ошибка при попытке блокировки аккаунта пользователем')
    



@users_router.post('/validate-email', summary='Проверка корректности email')
def validate_email(email: str = Form(...)):
    return is_correct_email(email)
