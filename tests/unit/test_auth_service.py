import pytest
from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from db.models import User, UserRole, UserSession, RoleEnum
from api.services.auth_service import AuthService
from api.deps import generate_token_pair


# =============================================================================
# ТЕСТЫ РЕГИСТРАЦИИ (register_user)
# =============================================================================

@pytest.mark.asyncio
async def test_register_user_success(db_session: AsyncSession, create_user_data):
    '''
    Тест: успешная регистрация нового пользователя.
    '''
    service = AuthService(db_session)
    user_data = create_user_data()
    
    # Вызываем метод регистрации
    token = await service.register_user(
        email=user_data['email'],
        name=user_data['name'],
        family_name=user_data['family_name'],
        patronymic=user_data['patronymic'],
        password1=user_data['password1'],
        password2=user_data['password2']
    )
    
    # Проверяем токен
    assert 'access_token' in token
    assert 'refresh_token' in token
    assert token['token_type'] == 'bearer'
    
    # Проверяем, что пользователь создан в БД
    result = await db_session.execute(select(User).where(User.email == user_data['email']))
    user: User = result.scalar_one_or_none()
    assert user is not None
    assert user.email == user_data['email']
    assert user.is_active is True
    
    # Проверяем, что роль USER назначена
    result = await db_session.execute(select(UserRole).where(UserRole.user_id == user.id))
    user_role: UserRole = result.scalar_one_or_none()
    assert user_role is not None
    assert user_role.role_id == RoleEnum.USER


@pytest.mark.asyncio
async def test_register_user_duplicate_email(db_session: AsyncSession, create_user_data):
    '''
    Тест: нельзя зарегистрировать двух пользователей с одним email.
    '''
    service = AuthService(db_session)
    user_data = create_user_data()
    
    # Первая регистрация
    await service.register_user(
        email=user_data['email'],
        name=user_data['name'],
        family_name=user_data['family_name'],
        patronymic=user_data['patronymic'],
        password1=user_data['password1'],
        password2=user_data['password2']
    )
    
    # Вторая регистрация с тем же email → ошибка
    with pytest.raises(HTTPException) as exc_info:
        await service.register_user(
            email=user_data['email'],
            name='Another',
            family_name='User',
            patronymic='',
            password1=user_data['password1'],
            password2=user_data['password2']
        )
    
    assert exc_info.value.status_code == status.HTTP_409_CONFLICT
    assert 'уже зарегистрирован' in exc_info.value.detail


@pytest.mark.asyncio
async def test_register_user_passwords_mismatch(db_session: AsyncSession, create_user_data):
    '''
    Тест: пароли должны совпадать.
    '''
    service = AuthService(db_session)
    user_data = create_user_data()
    user_data['password2'] = 'different_password'
    
    with pytest.raises(HTTPException) as exc_info:
        await service.register_user(
            email=user_data['email'],
            name=user_data['name'],
            family_name=user_data['family_name'],
            patronymic=user_data['patronymic'],
            password1=user_data['password1'],
            password2=user_data['password2']
        )
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'Пароли не совпадают' in exc_info.value.detail


@pytest.mark.asyncio
async def test_register_user_invalid_email(db_session: AsyncSession, create_user_data):
    '''
    Тест: некорректный email → ошибка.
    '''
    service = AuthService(db_session)
    user_data = create_user_data()
    user_data['email'] = 'invalid-email'  # Нет @
    
    with pytest.raises(HTTPException) as exc_info:
        await service.register_user(
            email=user_data['email'],
            name=user_data['name'],
            family_name=user_data['family_name'],
            patronymic=user_data['patronymic'],
            password1=user_data['password1'],
            password2=user_data['password2']
        )
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'email' in exc_info.value.detail.lower()


# =============================================================================
# ТЕСТЫ ВХОДА (login_user)
# =============================================================================

@pytest.mark.asyncio
async def test_login_user_success(db_session: AsyncSession, known_users, create_auth_form):
    '''
    Тест: успешный вход существующего пользователя.
    '''
    service = AuthService(db_session)
    
    form = create_auth_form(
        username=known_users['user1']['email'],
        password=known_users['user1']['password']
    )
    
    token = await service.login_user(form)
    
    assert 'access_token' in token
    assert 'refresh_token' in token
    assert token['token_type'] == 'bearer'


@pytest.mark.asyncio
async def test_login_user_not_registered(db_session: AsyncSession, create_auth_form):
    '''
    Тест: вход незарегистрированного пользователя → ошибка.
    '''
    service = AuthService(db_session)
    
    form = create_auth_form(
        username='nonexistent@bookreviews.com',
        password='111'
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await service.login_user(form)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'не зарегистрирован' in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_login_user_wrong_password(db_session: AsyncSession, known_users, create_auth_form):
    '''
    Тест: неверный пароль → ошибка.
    '''
    service = AuthService(db_session)
    
    form = create_auth_form(
        username=known_users['user1']['email'],
        password='wrong_password'
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await service.login_user(form)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'пароль' in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_login_blocked_user(db_session: AsyncSession, known_users, create_auth_form):
    '''
    Тест: вход заблокированного пользователя (user5) → ошибка.
    '''
    service = AuthService(db_session)
    
    form = create_auth_form(
        username=known_users['user5_blocked']['email'],
        password=known_users['user5_blocked']['password']
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await service.login_user(form)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'заблокирован' in exc_info.value.detail.lower()


# =============================================================================
# ТЕСТЫ ОБНОВЛЕНИЯ ТОКЕНА (refresh_token)
# =============================================================================

@pytest.mark.asyncio
async def test_refresh_token_success(db_session: AsyncSession, known_users):
    
    service = AuthService(db_session)
    tokens = generate_token_pair(known_users['user1']['email'])
    
    # Сохраняем сессию в БД
    user_result = await db_session.execute(
        select(User).where(User.email == known_users['user1']['email'])
    )
    user = user_result.scalar_one_or_none()
    
    token_entry = UserSession(
        user_id=user.id,
        token_jti=tokens['refresh_jti'],
        token_type='refresh',
        expires_at=tokens['refresh_expire']
    )
    db_session.add(token_entry)
    await db_session.commit()
    
    new_access_token = await service.refresh_token(tokens['refresh_token'])
    assert isinstance(new_access_token, str)


@pytest.mark.asyncio
async def test_refresh_token_expired(db_session: AsyncSession, known_users):
    '''
    Тест: просроченный refresh-токен → ошибка.
    '''
    from api.deps import generate_access_token
    from datetime import timedelta
    
    service = AuthService(db_session)
    
    # Генерируем просроченный токен
    token, *_ = generate_access_token(
        data={'sub': known_users['user1']['email']},
        exp_time=timedelta(seconds=-1),  # Уже истёк
        token_type='refresh'
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh_token(token)
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED
    assert 'истек' in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_refresh_token_wrong_type(db_session: AsyncSession, known_users):
    '''
    Тест: передан access-токен вместо refresh → ошибка.
    '''
    from api.deps import generate_access_token
    
    service = AuthService(db_session)
    
    # Генерируем access-токен (вместо refresh)
    token, *_ = generate_access_token(
        data={'sub': known_users['user1']['email']},
        token_type='access'
    )
    
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh_token(token)
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST
    assert 'refresh' in exc_info.value.detail.lower()


@pytest.mark.asyncio
async def test_refresh_token_invalid(db_session):
    '''
    Тест: невалидный токен → ошибка.
    '''
    service = AuthService(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        await service.refresh_token('invalid.token.here')
    
    assert exc_info.value.status_code == status.HTTP_401_UNAUTHORIZED


# =============================================================================
# ТЕСТЫ ВЫХОДА (logout_user)
# =============================================================================

@pytest.mark.asyncio
async def test_logout_user_success(db_session: AsyncSession, known_users):
    '''
    Тест: успешный выход (отзыв токена).
    '''
    from api.deps import generate_token_pair
    
    service = AuthService(db_session)
    
    # Генерируем токен и сохраняем сессию в БД
    tokens = generate_token_pair(known_users['user1']['email'])
    authorization = f"Bearer {tokens['refresh_token']}"
    
    # Находим пользователя для создания сессии
    result = await db_session.execute(select(User).where(User.email == known_users['user1']['email']))
    user = result.scalar_one_or_none()
    
    # Создаём сессию в БД
    session = UserSession(
        user_id=user.id,
        token_jti=tokens['refresh_jti'],
        token_type='refresh',
        expires_at=tokens['refresh_expire']
    )
    db_session.add(session)
    await db_session.commit()
    
    # Выход
    await service.logout_user(authorization)
    
    # Проверяем, что сессия отозвана
    result = await db_session.execute(
        select(UserSession).where(UserSession.token_jti == tokens['refresh_jti'])
    )
    db_session_entry = result.scalar_one_or_none()
    assert db_session_entry.is_revoked is True


@pytest.mark.asyncio
async def test_logout_user_invalid_token(db_session):
    '''
    Тест: выход с невалидным токеном → ошибка.
    '''
    service = AuthService(db_session)
    
    with pytest.raises(HTTPException) as exc_info:
        await service.logout_user('Bearer invalid.token')
    
    assert exc_info.value.status_code == status.HTTP_400_BAD_REQUEST