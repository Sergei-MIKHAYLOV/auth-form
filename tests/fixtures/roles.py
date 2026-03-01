import pytest


@pytest.fixture
def known_roles():
    '''
    Данные ролей из `roles.csv`
    '''
    return {
        'admin': {'id': 1, 'name': 'admin'},
        'moderator': {'id': 2, 'name': 'moderator'},
        'user': {'id': 3, 'name': 'user'},
        'guest': {'id': 4, 'name': 'guest'},
    }
