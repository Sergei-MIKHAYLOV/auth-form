import pytest
from fastapi import status
from httpx import Response, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from api.deps import generate_token_pair
from db.models import User, UserSession

# =============================================================================
# ТЕСТЫ РЕГИСТРАЦИИ (POST /register)
# =============================================================================

@pytest.mark.asyncio
async def test_register_endpoint_success(test_client: AsyncClient, form_data_factory):
    '''
    Тест: успешная регистрация через API.
    '''
    user_data = form_data_factory(
        email='newuser@bookreviews.com',
        name='Uzver',
        family_name='Userator',
        patronymic='Useratovich',
        password1='TestPass123!',
        password2='TestPass123!'
    )
    
    response: Response = await test_client.post('/register', data=user_data)
    
    assert response.status_code == status.HTTP_200_OK
    data: dict = response.json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['token_type'] == 'bearer'
    assert 'successfully registered' in data['message'].lower()


@pytest.mark.asyncio
async def test_register_endpoint_duplicate_email(test_client: AsyncClient, known_users, form_data_factory):
    '''
    Тест: регистрация с существующим email → 409.
    '''
    user_data = form_data_factory(
        email=known_users['admin']['email'],  # Уже существует
        name='Test',
        family_name='User',
        password1='TestPass123!',
        password2='TestPass123!'
    )
    
    response: Response = await test_client.post('/register', data=user_data)
    
    assert response.status_code == status.HTTP_409_CONFLICT
    data = response.json()
    assert 'уже зарегистрирован' in data['detail'].lower()


@pytest.mark.asyncio
async def test_register_endpoint_passwords_mismatch(test_client: AsyncClient, form_data_factory):
    '''
    Тест: пароли не совпадают → 400.
    '''
    user_data = form_data_factory(
        email='test@bookreviews.com',
        name='Test',
        family_name='User',
        password1='Password123!',
        password2='DifferentPassword!'  # Не совпадает
    )
    
    response: Response = await test_client.post('/register', data=user_data)
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert 'Пароли не совпадают' in data['detail']


@pytest.mark.asyncio
async def test_register_endpoint_missing_required_fields(test_client: AsyncClient, form_data_factory):
    '''
    Тест: отсутствие обязательных полей → 422.
    '''
    user_data = form_data_factory(
        # email отсутствует
        name='Test',
        password1='Password123!',
        password2='Password123!'
    )
    
    response: Response = await test_client.post('/register', data=user_data)
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# =============================================================================
# ТЕСТЫ ВХОДА (POST /login)
# =============================================================================

@pytest.mark.asyncio
async def test_login_endpoint_success(test_client: AsyncClient, known_users):
    '''
    Тест: успешный вход через API.
    '''
    response: Response = await test_client.post('/login', data={
        'username': known_users['user1']['email'],
        'password': known_users['user1']['password']
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'access_token' in data
    assert 'refresh_token' in data
    assert data['token_type'] == 'bearer'
    assert 'Login successful' in data['message']


@pytest.mark.asyncio
async def test_login_endpoint_wrong_password(test_client: AsyncClient, known_users):
    '''
    Тест: неверный пароль → 400.
    '''
    response: Response = await test_client.post('/login', data={
        'username': known_users['user1']['email'],
        'password': 'wrong_password'
    })
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert 'пароль' in data['detail'].lower()


@pytest.mark.asyncio
async def test_login_endpoint_not_registered(test_client):
    '''
    Тест: незарегистрированный пользователь → 400.
    '''
    response: Response = await test_client.post('/login', data={
        'username': 'nonexistent@bookreviews.com',
        'password': '111'
    })
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert 'не зарегистрирован' in data['detail'].lower()


@pytest.mark.asyncio
async def test_login_endpoint_blocked_user(test_client: AsyncClient, known_users):
    '''
    Тест: заблокированный пользователь → 400.
    '''
    response: Response = await test_client.post('/login', data={
        'username': known_users['user5_blocked']['email'],
        'password': known_users['user5_blocked']['password']
    })
    
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    data = response.json()
    assert 'заблокирован' in data['detail'].lower()


# =============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ ТОКЕНА (POST /refresh)
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_endpoint_success(test_client: AsyncClient,
                                        known_users: dict,
                                        db_session: AsyncSession):
    '''
    Тест: успешное обновление токена через API.
    '''

    tokens = generate_token_pair(known_users['user1']['email'])
    
    user_result = await db_session.execute(select(User)
                                           .where(User.email == known_users['user1']['email']))
    user = user_result.scalar_one_or_none()
    
    token_entry = UserSession(user_id=user.id,
                              token_jti=tokens['refresh_jti'],
                              token_type='refresh',
                              expires_at=tokens['refresh_expire'])
    db_session.add(token_entry)
    await db_session.commit()
    
    response = await test_client.post('/refresh', data={
        'refresh_token': tokens['refresh_token']
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'access_token' in data



@pytest.mark.asyncio
async def test_refresh_endpoint_missing_token(test_client: AsyncClient):
    '''
    Тест: отсутствие refresh-токена → 422.
    '''
    response: Response = await test_client.post('/refresh', data={})
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# =============================================================================
# ТЕСТЫ ВЫХОДА (GET /logout)
# =============================================================================

@pytest.mark.asyncio
async def test_logout_endpoint_success(test_client: AsyncClient, known_users):
    '''
    Тест: успешный выход через API.
    '''
    from api.deps import generate_token_pair
    
    # Получаем токен
    tokens = generate_token_pair(known_users['user1']['email'])
    
    response: Response = await test_client.get('/logout', headers={
        'Authorization': f"Bearer {tokens['refresh_token']}"
    })
    
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert 'Logout successful' in data['message']


@pytest.mark.asyncio
async def test_logout_endpoint_missing_authorization(test_client):
    '''
    Тест: отсутствие заголовка Authorization → 422.
    '''
    response: Response = await test_client.get('/logout')
    
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT


# =============================================================================
# СКВОЗНЫЕ ТЕСТЫ (полный сценарий)
# =============================================================================

@pytest.mark.asyncio
async def test_full_auth_flow(test_client: AsyncClient, form_data_factory):
    '''
    Тест: полный сценарий — регистрация → логин → refresh → logout.
    '''
    # 1. Регистрация
    user_data = form_data_factory(
        email='flowtest@bookreviews.com',
        name='Flow',
        family_name='Test',
        password1='FlowTest123!',
        password2='FlowTest123!'
    )
    
    register_response: Response = await test_client.post('/register', data=user_data)
    assert register_response.status_code == status.HTTP_200_OK
    
    # 2. Логин
    login_response: Response = await test_client.post('/login', data={
        'username': user_data['email'],
        'password': user_data['password1']
    })
    assert login_response.status_code == status.HTTP_200_OK
    tokens = login_response.json()
    assert 'access_token' in tokens
    assert 'refresh_token' in tokens
    
    # 3. Refresh
    refresh_response: Response = await test_client.post('/refresh', data={
        'refresh_token': tokens['refresh_token']
    })
    assert refresh_response.status_code == status.HTTP_200_OK
    new_access_token = refresh_response.json()['access_token']
    assert new_access_token != tokens['access_token']
    
    # 4. Logout
    logout_response: Response = await test_client.get('/logout', headers={
        'Authorization': f"Bearer {tokens['refresh_token']}"
    })
    assert logout_response.status_code == status.HTTP_200_OK