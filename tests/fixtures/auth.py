import pytest
from dataclasses import dataclass


@dataclass
class MockOAuth2Form:
    username: str
    password: str


@pytest.fixture
def create_auth_form():
    '''
    Фабрика для создания OAuth2PasswordRequestForm
    '''
    def _create(username: str, password: str) -> MockOAuth2Form:
        return MockOAuth2Form(username=username, password=password)
    return _create


@pytest.fixture
def auth_headers():
    '''
    Возвращает функцию для генерации заголовков с токеном
    '''

    def _get_headers(token: str) -> dict:
        return {
            'Authorization': f'Bearer {token}',
            'Content-Type': 'application/x-www-form-urlencoded',
            
        }
    return _get_headers


@pytest.fixture
def form_data_factory():
    '''
    Фабрика для создания form-data в тестах
    '''

    def _create_form(**kwargs) -> dict:
        return {k: str(v) if v is not None else '' for k, v in kwargs.items()}
    
    return _create_form


