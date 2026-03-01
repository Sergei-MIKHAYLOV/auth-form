from passlib.context import CryptContext
import hashlib
from jose import jwt, ExpiredSignatureError, JWTError
from datetime import datetime, timedelta, timezone
from fastapi.security import OAuth2PasswordBearer
from fastapi import Depends, HTTPException, status, UploadFile
from environs import Env
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from db.models import User, UserRole, Role, AccessRule, SqlModel
from api.models import PydanticModel
from typing import Type
from uuid import uuid4
import logging
from pathlib import Path
import aiofiles


logger = logging.getLogger(__name__)


ctx = CryptContext(schemes=['bcrypt'])
env = Env()
env.read_env()

SECRET_KEY = env.str('SECRET_KEY')
ALGORITHM = env.str('ALGORITHM')

oauth2_scheme = OAuth2PasswordBearer(tokenUrl='/login')


async def save_file_on_disc(file: UploadFile,
                            upload_dir: str = 'app/uploads/covers') -> str:
    '''
    Сохраняет загруженный файл на диск.
    
    Аргументы:
        `file` — загружаемый файл
        `upload_dir` — директория для сохранения
    
    Возвращает:
        `str` — уникальное имя файла
    '''

    file_extension = file.filename.split('.')[-1]
    unique_filename = f"{uuid4()}.{file_extension}"
    
    upload_path = Path(upload_dir)
    upload_path.mkdir(parents=True, exist_ok=True)

    file_path = upload_path / unique_filename
    
    async with aiofiles.open(file_path, 'wb') as buffer:
        content = await file.read()
        await buffer.write(content)
    
    return unique_filename
 


def hash_password(password: str) -> str:
    pre_hashed = hashlib.sha256(password.encode('utf-8')).hexdigest()

    return ctx.hash(secret=pre_hashed)



def verify_password(plain: str, hashed: str) -> bool:
    pre_hashed = hashlib.sha256(plain.encode('utf-8')).hexdigest()

    return ctx.verify(pre_hashed, hashed)



def generate_access_token(data: dict, 
                          exp_time: timedelta | None = timedelta(minutes=15),
                          token_type: str = 'access') -> tuple[str, str]:
    '''Генерирует jwt-токен

    Параметры:
        `data` - словарь с данными для кодирования
        `exp_time` - время валидности токена, (default=15 мин.)
        `token_type` - тип токена access / refresh (default=access)

    Возвращает:
        `tuple[str, str]` - (JWT строка, jti UUID)
    '''

    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + exp_time
    token_uuid = str(uuid4())
    to_encode.update({'exp': expire, 
                      'type': token_type,
                      'jti': token_uuid})
    
    token=jwt.encode(to_encode, SECRET_KEY, algorithm=ALGORITHM)

    return token, token_uuid, expire




def generate_token_pair(email: str) -> dict:
    access_token, access_jti, access_expire = generate_access_token(data={'sub': email},
                                                     exp_time=timedelta(minutes=30),
                                                     token_type='access')

    refresh_token, refresh_jti, refresh_expire = generate_access_token(data={'sub': email},
                                                       exp_time=timedelta(days=7),
                                                       token_type='refresh')
    
    return {'access_token': access_token,
            'access_jti': access_jti,
            'access_expire': access_expire,
            'refresh_token': refresh_token,
            'refresh_jti': refresh_jti,
            'refresh_expire': refresh_expire,
            'token_type': 'bearer',
            }


async def get_user(email: str, db: AsyncSession) -> User | None:  
      
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    return user



async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:
    '''
    Получение текущего пользователя с подгрузкой прав доступа
    '''

    try:
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        email = payload.get('sub')
        if not email:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Токен не содержит email')
        
        result = await db.execute(select(User)
                                  .options(
                                      selectinload(User.user_roles)
                                      .selectinload(UserRole.role)
                                      .selectinload(Role.access_rules)
                                      .selectinload(AccessRule.resource)
                                      )
                                      .where(User.email == email))
        
        user = result.scalar_one_or_none()

        if not user:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Пользователь не найден')
        
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Аккаунт пользователя заблокирован')
        
        return user
        
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Срок действия токена истек. Требуется повторный вход.')
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Неверный токен.')
    



def check_has_role(roles: list[str] | tuple[str] | str = 'admin') -> User:
    '''
    Проверяет есть ли среди ролей пользователя требуемая

    `current_user` - текущий пользователь  
    `roles` - проверяемая роль ('admin', 'moderator', 'user')

    '''
    if isinstance(roles, str):
        roles = [roles]

    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        for user_role in current_user.user_roles:
            if user_role.role.name in roles:
                return current_user
            
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'Недостаточно прав доступа. Необходимо быть `{roles[0]}`')
    
    return dependency
    

def check_not_last_role(user: User) -> bool:
    '''
    Проверяет не является ли роль единственной

    `user` - проверяемый пользователь   
    '''
    roles_count =  len(user.user_roles)
    if roles_count > 1:
        return True
    
    return False
            
    



def is_staff_account(user: User) -> bool:
    '''
    Проверяет не является ли аккаун пользователя служебным `admin` / `moderator`

    `user` - проверяемый пользователь

    '''

    forbidden_roles = ['admin', 'moderator']

    for user_role in user.user_roles:
        if user_role.role.name in forbidden_roles:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f'Служебный аккаунт не подлежит самостоятельной блокировке')
    return False




def is_owner(obj: SqlModel, user: User) -> bool:    
    '''
    Проверяет является ли пользователь создателем сообщения
    
    '''
    # Проверка наличия поля 'owner_id' в модели
    logger.debug(f'hasattr(obj, "owner_id"): {hasattr(obj, "owner_id")}')   
    if hasattr(obj, 'owner_id'):
        logger.debug(f'obj.owner_id: {obj.owner_id}') 
        logger.debug(f'user.id: {user.id}') 
        if obj.owner_id == user.id:
            return True   
    return False




def has_permission(user: User, resource: str, action: str) -> bool:
    
    '''
    Проверяет есть ли у пользователя хотя бы одна роль с `permission_type` для ресурса.
    
    Аргументы:
        `user` - Проверяемый пользователь  
        `resource` - Проверяемая таблица ('users', 'messages', 'roles', 'access_rules')  
        `action` - действие ('read', 'create', 'update', 'delete', 'read_all', 'update_all', 'delete_all', 'change_role', 'user_ban')
    
    Возвращает `True` / `False`

    '''
    permission_field = f'{action}_permission'
        
    for user_role in user.user_roles:
        # Если одна из ролей не активна - пропускаем
        if not user_role.role.is_active:
            continue
        
        # Просматривем правила для ресурса
        for rule in user_role.role.access_rules:
            # Если находим совпадение и правило не отменено
            if rule.resource.name == resource and rule.is_active:
                # Запрашиваем атрибут, не получили - возвращаем False
                if getattr(rule, permission_field, False):
                    return True
                
    return False


def has_all_permission(user: User, resource: str, action: str) -> bool:
    
    '''
    Проверяет есть ли у пользователя хотя бы одна роль с `permission_type` для ресурса.
    
    Аргументы:
        `user` - Проверяемый пользователь  
        `resource` - Проверяемая таблица ('users', 'messages', 'roles', 'access_rules' и т.д.)  
        `action` - действие ('read', 'create', 'update', 'delete')
    
    Возвращает `True` / `False`

    '''
    action_all = f'{action}_all'
    if has_permission(user, resource, action_all):
        return True
                    
    return False




def check_permission(resource: str, action: str) -> User:
    '''
    Обертка над `has_permission` для проверки прав текущего пользователя.  
    Если права есть - возвращает `User`, если нет - `HTTP_403_FORBIDDEN`
    
    Аргументы:
        `resource` - Проверяемая таблица ('users', 'messages', 'roles', 'access_rules')  
        `action` - действие ('read', 'create', 'update', 'delete', 'read_all', 'update_all', 'delete_all', 'change_role', 'user_ban')
    
    '''
    async def dependency(current_user: User = Depends(get_current_user)) -> User:
        if not has_permission(current_user, resource, action):      
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f'Недостаточно прав для действия `{action}` c {resource}')
        return current_user
    
    return dependency
    



def check_is_owner_or_has_all_permission(model: SqlModel, 
                                               user: User, 
                                               resource: str, 
                                               action: str) -> User:
    
    '''
    Проверка прав доступа: `создатель` или имеет `_all_permission` для действия `action`.  
    Если права есть - возвращает `True`, если нет - `HTTP_403_FORBIDDEN`
    
    Аргументы:
        `model` - Модель таблицы где есть поле `owner_id` (Message, Book) 
        `user` - Проверяемый пользователь  
        `resource` - Проверяемая таблица ('users', 'messages', 'roles', 'access_rules')  
        `action` - действие ('read', 'create', 'update', 'delete', 'read_all', 'update_all', 'delete_all', 'change_role', 'user_ban')
    
    '''

    if is_owner(model, user) or has_all_permission(user, resource, action):
        return user
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f'Недостаточно прав для действия `{action}` c {resource}')
    



async def get_object_or_404(db: AsyncSession, 
                            model: Type[SqlModel], 
                            id: int,
                            detail='Объект не найден') -> SqlModel:
    '''
    Получение записи из таблицы или выдачи `HTTP_404_NOT_FOUND`
    '''
    result = await db.execute(select(model).where(model.id == id))
    obj = result.scalar_one_or_none()
    
    if not obj:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=detail)
    
    return obj



def check_not_self(current_user_id: int, 
                   target_user_id: int,
                   action: str = 'заблокировать'):
    '''
    Проверка, что админ не пытается случайно изменить себя (удалить / заблокировать)
    '''
    if current_user_id == target_user_id:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail=f'Нельзя выполнять действие `{action}` со своей учетной записью')




def serialize_model(model: Type[SqlModel], 
                    schema: Type[PydanticModel]) -> PydanticModel:
    '''
    Конвертация модели sqlalchemy.orm -> pydantic
    '''
    return schema.model_validate(model).model_dump()