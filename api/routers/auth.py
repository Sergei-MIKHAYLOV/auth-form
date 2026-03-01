from fastapi import APIRouter, Depends, Form, Header
from fastapi.security import OAuth2PasswordRequestForm
from api.services.auth_service import AuthService
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db


auth_router = APIRouter()

@auth_router.post('/register', summary='Регистрация новых пользователей')
async def register_user(family_name: str = Form(''),
                        name: str = Form(...),
                        patronymic: str = Form(''),
                        email: str = Form(...),
                        password1: str = Form(...),
                        password2: str = Form(...),
                        db: AsyncSession = Depends(get_db)):     
  
    service = AuthService(db)
    token = await service.register_user(email, name, family_name, patronymic, password1, password2)

    return {'access_token': token['access_token'], 
            'refresh_token': token['refresh_token'], 
            'token_type': 'bearer', 
            'message': 'User successfully registered'}



@auth_router.post('/login', summary='Вход пользователя в систему')
async def login_user(form_data: OAuth2PasswordRequestForm = Depends(),
                     db: AsyncSession = Depends(get_db)):
    
    service = AuthService(db)
    token = await service.login_user(form_data)

    return {'access_token': token['access_token'], 
            'refresh_token': token['refresh_token'],   
            'token_type': 'bearer', 
            'message': 'Login successful'}



@auth_router.post('/refresh', summary='Обновление access-токена')
async def refresh_token(refresh_token: str = Form(...), 
                        db: AsyncSession = Depends(get_db)):
        
    service = AuthService(db)
    token = await service.refresh_token(refresh_token)
        
    return {'access_token': token,
            'token_type': 'bearer', 
            'message': 'New access token was issued'}




@auth_router.get('/logout', summary='Выход пользователя из системы')
async def logout_user(authorization: str = Header(...),
                      db: AsyncSession = Depends(get_db)):
        
    service = AuthService(db)
    await service.logout_user(authorization)

    return {'message': 'Logout successful'}
    
