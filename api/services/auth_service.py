from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status
from fastapi.security import OAuth2PasswordRequestForm
from db.models import User, UserRole, UserSession, RoleEnum
from jose import jwt, ExpiredSignatureError, JWTError
from api.deps import get_user, verify_password, hash_password, generate_token_pair, generate_access_token
from api.utils import validate_email_or_400
from environs import Env


env = Env()
env.read_env()

SECRET_KEY = env.str('SECRET_KEY')
ALGORITHM = env.str('ALGORITHM')



class AuthService:
    def __init__(self, db: AsyncSession):
        self.db = db
    

    async def register_user(self,
                            email: str,
                            name: str,
                            family_name: str,
                            patronymic: str,
                            password1: str,
                            password2: str) -> dict:
        
        if email is None:
            raise HTTPException(status_code=status.HTTP_422_UNPROCESSABLE_CONTENT,
                                detail='Отсутствует обязательное поле `email`')
        
        validate_email_or_400(email)

        user_exists = await get_user(email, self.db)    
        if user_exists:
            raise HTTPException(status_code=status.HTTP_409_CONFLICT,
                                detail='Пользователь с таким email уже зарегистрирован')
        
        if password1 != password2:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Пароли не совпадают')  
        
        hashed_password = hash_password(password1)
        user_entry = User(email=email,
                        password=hashed_password,
                        family_name=family_name,
                        name=name,
                        patronymic=patronymic)
        
        self.db.add(user_entry)
        user = await get_user(email, self.db)

        user_role = UserRole(user_id=user.id,
                            role_id=RoleEnum.USER)
        self.db.add(user_role)
        
        token = generate_token_pair(email)
        token_entry = UserSession(user_id=user_entry.id,
                                token_jti=token['refresh_jti'],
                                token_type='refresh',
                                expires_at=token['refresh_expire'])
        self.db.add(token_entry)
        await self.db.commit()

        return token
    

    async def login_user(self,
                         form_data: OAuth2PasswordRequestForm) -> dict:
        
        user = await get_user(form_data.username, self.db)
        if not user:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Пользователь не зарегистрирован')
        
        
        if not verify_password(form_data.password, user.password):
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Неверный пароль')
        
        if not user.is_active:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Ваш аккаунт заблокирован. Для восстановления доступа обратитесь в тех. поддержку')
        
        token = generate_token_pair(user.email)
        token_entry = UserSession(user_id=user.id,
                                token_jti=token['refresh_jti'],
                                token_type='refresh',
                                expires_at=token['refresh_expire'])
        self.db.add(token_entry)
        await self.db.commit()

        return token
    

    async def refresh_token(self,
                            refresh_token: str) -> dict:
        
        try:
            payload: dict = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

            if payload.get('type') != 'refresh':
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail='Неправильный тип токена. Требуется `refresh` токен.')
                
            email = payload.get('sub')
            if not email:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail='Токен не содержит данных.')
            
            user: User = await get_user(email, self.db)
            if user is None or not user.is_active:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                    detail='Акаунт пользователя неактивен или отсутствует в базе')
            
            result = await self.db.execute(select(UserSession).where(UserSession.token_jti == payload.get('jti')))
            session = result.scalar_one_or_none()
            if session is None or session.is_revoked == True:
                raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                    detail='Токен `refresh` более недействителен')
            
            access_token, *_ = generate_access_token(data={'sub': email},
                                                    token_type='access')
            
            return access_token
        
        except ExpiredSignatureError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Срок действия `refresh` токена истек. Требуется повторный вход.')
        
        except JWTError:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                                detail='Неверный `refresh` токен.') 
        

            

    async def logout_user(self,
                          authorization: str) -> None:
        
        try:
            token = authorization.replace('Bearer ', '')
            payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
            token_jti = payload.get('jti')

            if not token_jti:
                raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                    detail='Токен не содержит UUID')


            result = await self.db.execute(select(UserSession).where(UserSession.token_jti == token_jti))
            session = result.scalar_one_or_none()

            if session:
                session.is_revoked = True
                await self.db.commit()

            return None
        
        except ExpiredSignatureError:
            return {'message': 'Logout successful'}
        
        except JWTError:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail='Неверный формат токена')
