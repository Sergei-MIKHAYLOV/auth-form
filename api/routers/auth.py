from fastapi import APIRouter, Depends, Form, HTTPException, status, Header
from fastapi.security import OAuth2PasswordRequestForm
from environs import Env
from api.deps import hash_password, verify_password, generate_access_token, generate_token_pair, get_user
from jose import jwt, ExpiredSignatureError, JWTError
from api.utils import is_correct_email

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.db_init import get_db
from db.models import User, UserRole, UserSession, RoleEnum




auth_router = APIRouter()

env = Env()
env.read_env()

SECRET_KEY = env.str('SECRET_KEY')
ALGORITHM = env.str('ALGORITHM')



@auth_router.post('/register', summary='Регистрация новых пользователей')
async def register_user(family_name: str = Form(''),
                  name: str = Form(...),
                  patronymic: str = Form(''),
                  email: str = Form(...),
                  password1: str = Form(...),
                  password2: str = Form(...),
                  db: AsyncSession = Depends(get_db)):     
  
    is_correct_email(email)

    user_exists = await get_user(email, db)    
    if user_exists:
        raise HTTPException(status_code=status.HTTP_409_CONFLICT, detail='Пользователь с таким email уже зарегистрирован')
    
    if password1 != password2:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Пароли не совпадают')  
    
    hashed_password = hash_password(password1)
    user_entry = User(email=email,
                      password=hashed_password,
                      family_name=family_name,
                      name=name,
                      patronymic=patronymic)
    
    db.add(user_entry)
    await db.commit()

    user = await get_user(email, db)

    user_role = UserRole(user_id=user.id,
                         role_id=RoleEnum.USER)
    db.add(user_role)
    await db.commit()
    
    token = generate_token_pair(email)
    token_entry = UserSession(user_id=user_entry.id,
                              token_jti=token['refresh_jti'],
                              token_type='refresh',
                              expires_at=token['refresh_expire'])
    db.add(token_entry)
    await db.commit()

    return {'access_token': token['access_token'], 
            'refresh_token': token['refresh_token'], 
            'token_type': 'bearer', 
            'message': 'User successfully registered'}




@auth_router.post('/login', summary='Вход пользователя в систему')
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(),
                     db: AsyncSession = Depends(get_db)):
    user = await get_user(form_data.username, db)
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
    db.add(token_entry)
    await db.commit()

    return {'access_token': token['access_token'], 
            'refresh_token': token['refresh_token'],   
            'token_type': 'bearer', 
            'message': 'Login successful'}




@auth_router.post('/refresh', summary='Обновление access-токена')
async def refresh_token(refresh_token: str, db: AsyncSession = Depends(get_db)):
    try:
        payload: dict = jwt.decode(refresh_token, SECRET_KEY, algorithms=[ALGORITHM])

        if payload.get('token_type') != 'refresh':
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail='Неправильный тип токена. Требуется `refresh` токен.')
               
        email = payload.get('sub')
        if not email:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail='Токен не содержит данных.')
        
        user: User = await get_user(email, db)
        if user is None or not user.is_active:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail='Акаунт пользователя неактивен или отсутствует в базе')
        
        result = await db.execute(select(UserSession).where(UserSession.token_jti == payload.get('jti')))
        session = result.scalar_one_or_none()
        if session is None or session.is_revoked == True:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, 
                                detail='Токен `refresh` более недействителен')
        
        access_token, *_ = generate_access_token(data={'sub': email},
                                                 token_type='access')
        
        return {'access_token': access_token,
                'token_type': 'bearer', 
                'message': 'New access token was issued'}
    
    except ExpiredSignatureError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Срок действия `refresh` токена истек. Требуется повторный вход.')
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED,
                            detail='Неверный `refresh` токен.') 





@auth_router.get('/logout', summary='Выход пользователя из системы')
async def logout_user(authorization: str = Header(...),
                      db: AsyncSession = Depends(get_db)):
    try:
        token = authorization.replace('Bearer ', '')
        payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])
        token_jti = payload.get('jti')

        if not token_jti:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, 
                                detail='Токен не содержит UUID')


        result = await db.execute(select(UserSession).where(UserSession.token_jti == token_jti))
        session = result.scalar_one_or_none()

        if session:
            session.is_revoked = True
            await db.commit()

        return {'message': 'Logout successful'}
    
    except ExpiredSignatureError:
        return {'message': 'Logout successful'}
    
    except JWTError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                            detail='Неверный формат токена')