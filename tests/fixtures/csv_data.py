import pytest
from sqlalchemy.orm import Session
from sqlalchemy import create_engine, text
from config.config import load_config
from utils.csv_loader import init_database_from_csv
from db.models import Base
import logging


logger = logging.getLogger(__name__)



@pytest.fixture(scope='session', autouse=True)
def load_mock_data_to_test_db():
    '''
    Перед началом тестов создает тестовую БД и загружает мок-данные из csv-файлов.
    '''

    config = load_config(test_mode=True)
    
    admin_url = config.db.sync_url.replace(config.db._current_db_name, 'postgres')
    test_db_name = config.db._current_db_name
    test_url = config.db.sync_url
    
    admin_engine = create_engine(admin_url, echo=False, isolation_level='AUTOCOMMIT')
    with admin_engine.connect() as conn:
        result = conn.execute(
            text("SELECT 1 FROM pg_database WHERE datname = :name"),
            {"name": test_db_name}
        )
        if not result.scalar():
            conn.execute(text(f'CREATE DATABASE "{test_db_name}"'))
            logger.info(f'База данных `{test_db_name}` создана')
        else:
            logger.info(f'База данных `{test_db_name}` уже существует')
    admin_engine.dispose()
    
    test_engine = create_engine(test_url, echo=False)
    Base.metadata.create_all(bind=test_engine)
    
    with Session(test_engine) as session:
        init_database_from_csv(db=session)
        logger.info(f'Мок-данные загружены в тестовую БД `{config.db._current_db_name}`')
    
    yield