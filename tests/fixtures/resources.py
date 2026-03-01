import pytest


@pytest.fixture
def known_resources():
    '''
    Данные ресурсов из `resources.csv`
    '''
    return {'users': {'id': 1, 'name': 'users'},
            'roles': {'id': 2, 'name': 'roles'},
            'access_rules': {'id': 3, 'name': 'access_rules'},
            'books': {'id': 4, 'name': 'books'},
            'messages': {'id': 5, 'name': 'messages'}}
