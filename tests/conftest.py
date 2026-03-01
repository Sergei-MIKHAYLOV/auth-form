import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession, async_sessionmaker
from config.config import load_config
from db.models import Base
from db.db_init import get_db
from main import app
from tests.fixtures.users import known_users, create_user_data
from tests.fixtures.roles import known_roles
from tests.fixtures.resources import known_resources
from tests.fixtures.auth import auth_headers, form_data_factory, create_auth_form
from tests.fixtures.csv_data import load_mock_data_to_test_db


config = load_config(test_mode=True)

@pytest_asyncio.fixture(scope='function')
async def test_engine():
    '''
    Движок для тестовой БД
    '''

    engine = create_async_engine(config.db.async_url, 
                                 echo=False,
                                 pool_pre_ping=True)
    
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
    
    yield engine   
    await engine.dispose()



@pytest_asyncio.fixture
async def db_session(test_engine):
    '''
    Сессия БД с автоматическим откатом после каждого теста
    '''

    async_session = async_sessionmaker(test_engine,
                                       class_=AsyncSession,
                                       expire_on_commit=False)
    
    async with async_session() as session:
        yield session
        await session.rollback()



@pytest_asyncio.fixture
async def test_client(db_session):
    '''
    HTTP-клиент с подменой зависимости get_db
    '''

    async def override_get_db():
        yield db_session
    
    app.dependency_overrides[get_db] = override_get_db
    
    async with AsyncClient(transport=ASGITransport(app=app), 
                           base_url='http://test') as client:
        yield client
    
    app.dependency_overrides.clear()

