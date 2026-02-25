# Auth-form: Система аутентификации и разграничения прав доступа

Реализация backend-приложения с собственной системой аутентификации, авторизации и гибким управлением правами доступа к ресурсам. Проект демонстрирует работу с JWT-токенами, сессиями и RBAC-моделью.

## Техническое задание

Реализовать backend-приложение - собственную систему аутентификации и авторизации, не полагаясь полностью на готовые решения фреймворка.

**1. Взаимодействие с пользователем**  
- Регистрация: ФИО, email, пароль, подтверждение пароля
- Login: вход по email/паролю
- Logout: выход из системы
- Профиль: редактирование личных данных
- Удаление аккаунта: «мягкое» (`is_active=False`), с запретом на вход
- Идентификация: при последующих запросах система должна «узнавать» пользователя

**2. Система разграничения прав доступа**  
- Спроектировать схему БД: роли, ресурсы, правила доступа
- Описать логику в README.md
- Заполнить тестовыми данными для демонстрации
- Возвращать:
  - `401 Unauthorized` - если пользователь не аутентифицирован;  
  - `403 Forbidden` - если пользователь аутентифицирован, но не имеет прав на ресурс.
- API для администратора: CRUD для ролей, ресурсов и правил доступа.

**3. Mock-объекты бизнес-приложения**  
- Не обязательно создавать реальные таблицы, достаточно Mock-View, которые возвращают тестовые данные или ошибки

**Комментарии от авторов ТЗ:**   

Аутентификация:
- bcrypt для хеширования паролей
- jwt для генерации токенов
- Варианты: Bearer-токен в заголовке или сессии + Cookie
- Middleware для присвоения request.user

Авторизация:
- Таблицы: `roles`, `business_elements`, `access_roles_rules`
- Поля прав: `read_permission`, `read_all_permission`, `create_permission`, и т.д.
- `_all` - доступ ко всем объектам, без суффикса - только к своим (`owner_id`)
---

## Реализация

**1. Взаимодействие с пользователем**  


| Требование | Реализация | Файл / Эндпоинт |
|------------|------------|-----------------|
| Регистрация | `POST /register` - валидация через Pydantic, SHA256+bcrypt | `api/deps.py::hash_password` |
| Login | `POST /login` - выдача пары access/refresh JWT | `api/deps.py::generate_token_pair` |
| Logout | Отзыв токена через `jti` в таблице `sessions` | `db/models.py::UserSession` |
| Профиль | `GET/PUT /me` - получение и обновление данных | `api/routers/access_control.py` |
| Удаление | `PATCH /me/deactivate` - `is_active=False` + logout | `db/models.py::ActiveMixin` |
| Идентификация | Middleware + `get_current_user()` подтягивает пользователя по JWT | `api/deps.py`, `api/protect_docs.py` |

---

Пример проверки токена и подгрузки прав доступа:
```python
# api/deps.py
async def get_current_user(token: str = Depends(oauth2_scheme),
                           db: AsyncSession = Depends(get_db)) -> User:

    payload = jwt.decode(token, SECRET_KEY, algorithms=[ALGORITHM])

    # ... загрузка пользователя с roles -> access_rules -> resources
    # через selectinload, чтобы избежать N+1
```


**2. Система разграничения прав доступа (RBAC)**   
Система построена на реляционной модели с поддержкой many-to-many связей и гранулярных прав.

![Даталогическая схема БД](auth_db_schema_cut.png)



- Гранулярные права: `read` vs `read_all`, `update` vs `update_all` - доступ к «своим» или ко «всем» объектам
- Наследование прав: если у пользователя несколько ролей - достаточно права в одной из них
- Защита служебных аккаунтов: `is_staff_account()` не даёт заблокировать `admin`/`moderator`
- Защита от `self-actions`: `check_not_self()` - админ не может удалить/заблокировать себя
- Middleware для `/docs`: документация видна только admin | `api/protect_docs.py`


Пример проверки прав в эндпоинте:
```python
# api/routers/access_control.py
@access_control_router.patch('/users/{user_id}/status', summary='Заблокировать/разблокировать пользователя')
async def change_user_status(user_id: int,
                             is_active: bool = Form(...),
                             current_user: User = Depends(check_permission('users', 'user_ban')),
                             db: AsyncSession = Depends(get_db)):

# Если у пользователя нет права 'user_ban' на ресурс 'users' - возбуждение исключения 403_FORBIDDEN
```

При старте загружаются тестовые данные (см. папку mock-data):
```
users: admin@, moderator1@, user1@... (везде одинаковый пароль: '111')
roles: admin, moderator, user, guest
resources: users, messages, books, roles, access_rules
rules: например, `user` может `read` свои `messages`, но не `read_all`
```

Пользователь с ролью `admin` может назначать роли пользователям:
```python
# api/routers/access_control.py
@access_control_router.patch('/users/{user_id}/role', summary='Добавить роль пользователю')
async def add_user_role(user_id: int,
                        role_id: int = Form(...),
                        current_user: User = Depends(check_has_role(roles='admin')),
                        db: AsyncSession = Depends(get_db)):

# Если у пользователь не является 'admin' - возбуждение исключения 403_FORBIDDEN
```


**3. Mock-объекты бизнес-приложения**  

| Ресурс | Описание | Эндпоинт |
|------------|------------|-----------------|
| messages | Отзывы пользователей к книгам | CRUD с проверкой `owner_id` |
| books | Мок-каталог книг | CRUD с проверкой `check_permission('<ресурс>', '<действие>')` |
| users | Управление пользователями | Полный контроль для `admin`, для `moderator` - только бан/разбан |


Пример с проверкой права редактирования отзыва к книге (проверка «свой или есть `_all_permission`»):
```python
# api/deps.py
def check_is_owner_or_has_all_permission(model: SqlModel, 
                                               user: User, 
                                               resource: str, 
                                               action: str) -> User:

    if is_owner(model, user) or has_all_permission(user, resource, action):
        return user
    
    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                        detail=f'Недостаточно прав для действия `{action}` c {resource}')
```


---
# Что сделано сверх ТЗ:

Фича | Что делает | Где находится
--- | --- | ---
Refresh-токены | Безопасное обновление сессии без повторного логина | `api/deps.py::generate_token_pair`
Фабрика роутеров | DRY: один код для CRUD ролей/ресурсов | `api/utils.py::create_crud_router`
Асинхронность везде | Производительность, non-blocking I/O | `SQLAlchemy 2.0 async, FastAPI`
Валидация email | Ранний отсев некорректных данных | `api/utils.py::is_correct_email`
Логирование | Отладка и аудит действий | `logger.debug()` в `api/deps.py`, `api/protect_docs.py`
Health-check | Мониторинг состояния сервиса | `GET /health` в `main.py`
Pre-hash SHA256 + bcrypt | Дополнительный слой защиты паролей | `api/deps.py::hash_password`
Защита `/docs` | Swagger/ReDoc видны только admin | `api/protect_docs.py::AuthDocsMiddleware`
Frontend-заглушка на HTML/JS | для быстрой проверки flow без Postman | `frontend/index.html`


#### Возможности сервиса
- Регистрация, логин, редактирование профиля пользователя, блокировка аккаунта, логаут.
- Подержка входа без логина (на основе jwt-токена)
- CRUD для книг/отзывов (Mock-объекты бизнес-приложения)
- Управление ролями и ресурсами для админа

#### Технологический стек
- Backend: Python 3.13, FastAPI 0.128
- ORM: SQLAlchemy 2.0+ (асинхронный режим)
- База данных: PostgreSQL 17
- Контейнеризация: Docker, Docker Compose
- Документация: Swagger UI (OpenAPI)


#### Запуск проекта

1. Клонировать репозиторий:
   ```bash
   git clone https://github.com/Sergei-MIKHAYLOV/auth-form.git
   cd auth-form
   ```

2. Собрать и запустить сервисы:
   ```bash
   docker-compose up --build
   ```

3. Доступные интерфейсы:
   - API Documentation: http://localhost:8000/docs (для админа)
   - pgAdmin (управление БД): http://localhost:5050

#### Настройка pgAdmin

Для подключения к базе данных выполнить следующие действия:
1. Войти в pgAdmin, используя учётные данные:  
   - e-mail: `admin@bookreviews.com`  
   - Пароль: `1111`
2. Нажать Add New Server.
3. Во вкладке General указать имя сервера: `auth-form`.
4. Во вкладке Connection задать параметры подключения:  
     - Host: `postgresDB`  
     - Port: `5432`  
     - Maintenance database: `bookreviews`  
     - Username: `admin`  
     - Password: `1111`
5. Нажать Save.