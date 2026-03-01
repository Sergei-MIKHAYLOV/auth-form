import pytest
from faker import Faker


fake = Faker('ru_RU')


@pytest.fixture
def known_users() -> dict:
    '''
    Выборка пользователей с разными ролями из `users.csv`.
    Пароль для всех: '111'
    '''
    return {
        'admin': {
            'id': 1,
            'email': 'admin@bookreviews.com',
            'password': '111',
            'is_active': True,
        },
        'moderator1': {
            'id': 2,
            'email': 'moderator1@bookreviews.com',
            'password': '111',
            'is_active': True,
        },
        'user1': {
            'id': 4,
            'email': 'user1@bookreviews.com',
            'password': '111',
            'is_active': True,
        },
        'user5_blocked': {
            'id': 8,
            'email': 'user5@bookreviews.com',
            'password': '111',
            'is_active': False,  # Заблокирован
        },
    }



@pytest.fixture
def create_user_data():
    '''
    Фабрика для генерации данных нового пользователя
    '''

    def _create(**overrides) -> dict:
       
        base = {'email': fake.email(),
                'name': fake.first_name(),
                'family_name': fake.last_name(),
                'patronymic': fake.middle_name(),
                'password1': 'TestPass123!',
                'password2': 'TestPass123!'}

        base.update(overrides)
        return base
    
    return _create