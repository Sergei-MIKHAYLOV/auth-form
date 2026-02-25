from db.models import Base, User, UserRole, AccessRule, Role, Book, Message, Resource
import logging
from pathlib import Path
import csv
from sqlalchemy.orm import Session, sessionmaker
from sqlalchemy import create_engine, text
from typing import Any
from config.config import load_config


config = load_config()
logger = logging.getLogger(__name__)

engine = create_engine(url=config.db.sync_url,
                       pool_pre_ping=True,
                       echo=True
                       )

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

table_data = {        
              'roles.csv': Role,
              'resources.csv': Resource,
              'users.csv': User,
              'user_roles.csv': UserRole,              
              'access_rules.csv': AccessRule,
              'books.csv': Book,
              'messages.csv': Message,
              }

def convert_csv_value(value: str, field_name: str) -> Any:
    '''Конвертирует строковые значения из csv-файлов
    в требуемые для БД типы данных'''

    # Целые числа
    int_vals = ['id', 'user_id', 'role_id', 'resource_id']
    bool_vals = ['is_active', 'create_permission', 'read_permission', 'read_all_permission', 
                 'update_permission', 'update_all_permission', 'delete_permission', 'delete_all_permission',
                 'change_user_role_permission', 'user_ban_permission']

    if not value:
        return None
    if field_name in bool_vals:
        return value.lower() == 'true'
    if field_name in int_vals:
        return int(value)
    return value



def load_csv_data(db: Session, data_dir: str = 'mock-data'):
    '''Загружает мок-данные из csv-файлов'''
    
    data_path = Path(data_dir)
    for csv_file, table_model in table_data.items():
        file_path = data_path / csv_file
        logger.info(f'Загрузка данных из файла {csv_file}')
        
        with open(file_path, encoding='utf-8-sig') as f:
            reader = csv.reader(f)

            headers = next(reader)

            for row in reader:
                row_dict = {
                    header: convert_csv_value(value, header)
                    for header, value in zip(headers, row)
                }
                record = table_model(**row_dict)
                db.add(record)

        db.commit()
        logger.info(f'Таблица {csv_file.split('.')[0]} успешно создана')


def sync_sequences(db: Session, tables_list: dict) -> None:
    '''Синхронизирует id в таблицах со вставленными вручную из мок-данных'''

    tables = (name.split('.')[0] for name in tables_list.keys())
    for table in tables:
        db.execute(
            text(f'''SELECT setval(pg_get_serial_sequence('{table}', 'id'),
                COALESCE(MAX(id), 0) + 1) FROM "{table}";'''))
    db.commit()



def init_database_from_csv():
    '''Инициализирует БД и загружает в неё мок-данные'''

    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        db.execute(
            text('''TRUNCATE users, roles, user_roles, resources,
            access_rules, books, messages
            RESTART IDENTITY CASCADE'''))
        db.commit()
        load_csv_data(db)
        sync_sequences(db, table_data)
    finally:
        db.close()



if __name__ == '__main__':
    init_database_from_csv()
