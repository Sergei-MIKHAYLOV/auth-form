from fastapi import APIRouter, Depends, Form
from api.deps import get_current_user
from api.utils import validate_email_or_400
from api.services.user_profile_service import UserProfileService
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from db.models import User
from api.models import UserSchema

import logging

logger = logging.getLogger(__name__)


users_router = APIRouter()

@users_router.get('/me', summary='Вывод информации пользователя "О себе"')
async def read_own_info(current_user: User = Depends(get_current_user)):
    
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
    
    service = UserProfileService(db)
    user_profile = await service.edit_profile(email, name, family_name, patronymic, password1, password2, current_user)

    return {'message': 'Профиль успешно обновлен',
            'user': user_profile}



@users_router.delete('/me', summary='Блокировка своего аккаунта пользователем')
async def block_account(current_user: User = Depends(get_current_user),
                        db: AsyncSession = Depends(get_db)):

    service = UserProfileService(db)
    await service.block_user(current_user)

    return {'message': 'Ваш аккаунт заблокирован. Для разблокировки обратитесь в тех. поддержку'}



@users_router.post('/validate-email', summary='Проверка корректности email')
def validate_email(email: str = Form(...)):
    return validate_email_or_400(email)
