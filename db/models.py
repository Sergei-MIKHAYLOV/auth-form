from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship
from sqlalchemy import (String, DateTime, func, CheckConstraint, Boolean,
                        ForeignKey, Index, Integer, Identity, Text)
from typing import TypeVar
from enum import Enum


SqlModel = TypeVar('SqlModel', bound=DeclarativeBase)

class RoleEnum(int, Enum):
    '''Перечисление базовых ролей в системе'''
    ADMIN = 1
    MODERATOR = 2
    USER = 3
    GUEST = 4


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(),
                                                 nullable=False)
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                 onupdate=func.now(),
                                                 nullable=True)
    

class ActiveMixin:
    is_active: Mapped[bool] = mapped_column(default=True, nullable=False)



class User(Base, TimestampMixin, ActiveMixin):
    '''Модель пользователей'''
    __tablename__ = 'users'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    family_name: Mapped[str] = mapped_column(String(255), nullable=True)
    name: Mapped[str] = mapped_column(String(255), nullable=False)
    patronymic: Mapped[str] = mapped_column(String(255), nullable=True)

    password: Mapped[str] = mapped_column(String(255), nullable=False)

    user_roles: Mapped[list['UserRole']] = relationship(back_populates='user',
                                              cascade='all, delete-orphan',
                                              lazy='selectin')
    
    sessions: Mapped[list['UserSession']] = relationship(back_populates='user',
                                                         cascade='all, delete-orphan')

    messages: Mapped[list['Message']] = relationship(back_populates='msg_owner',
                                                     cascade='all, delete-orphan',
                                                     lazy='selectin')

    __table_args__ = (
        CheckConstraint('CHAR_LENGTH(password) >= 3', name='chk_password_length'),
        CheckConstraint("email LIKE '%%@%%.%%'", name='chk_is_correct_email'),
        Index('idx_users_email', 'email'),
        Index('idx_users_is_active', 'is_active'),
    )


class Role(Base, TimestampMixin, ActiveMixin):
    '''Модель с перечнем ролей в системе'''
    __tablename__ = 'roles'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(50), unique=True, nullable=False)
    description: Mapped[str] = mapped_column(String(255), unique=True, nullable=False)

    user_roles: Mapped[list['UserRole']] = relationship(back_populates='role',
                                                        cascade='all, delete-orphan',
                                                        lazy='selectin')
    access_rules: Mapped[list['AccessRule']] = relationship(back_populates='role',
                                                            cascade='all, delete-orphan',
                                                            lazy='selectin')
    
    __table_args__ = (
        Index('idx_roles_name', 'name'),
    )


class UserRole(Base, TimestampMixin):
    '''Связующая таблица: пользователь-роль'''
    __tablename__ = 'user_roles'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'), 
                                         nullable=False)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'),
                                         nullable=False)
    
    # Связи
    user: Mapped['User'] = relationship(back_populates='user_roles',
                                        lazy='selectin')
    role: Mapped['Role'] = relationship(back_populates='user_roles',
                                        lazy='selectin')
    
    __table_args__ = (
        Index('idx_user_roles_user_id', 'user_id'),
        Index('idx_user_roles_role_id', 'role_id'),
        Index('idx_user_roles_unique', 'user_id', 'role_id', unique=True),
    )


class AccessRule(Base, TimestampMixin, ActiveMixin):
    '''Модель прав доступа ролей к ресурсам в системе'''
    __tablename__ = 'access_rules'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    role_id: Mapped[int] = mapped_column(ForeignKey('roles.id', ondelete='CASCADE'),
                                         nullable=False)
    resource_id: Mapped[int] = mapped_column(ForeignKey('resources.id', ondelete='CASCADE'),
                                             nullable=False)
    
    create_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    read_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    read_all_permission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    update_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    update_all_permission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    delete_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    delete_all_permission: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    change_user_role_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)
    user_ban_permission: Mapped[bool] = mapped_column(Boolean, default=True, nullable=False)

    role: Mapped['Role'] = relationship(back_populates='access_rules',
                                        lazy='selectin')
    resource: Mapped['Resource'] = relationship(back_populates='access_rules',
                                                lazy='selectin')

    __table_args__ = (
        Index('idx_access_rules_role_id', 'role_id'),
        Index('idx_access_rules_resource_id', 'resource_id'),
        Index('idx_access_rules_unique', 'role_id', 'resource_id', unique=True),
    )


class Resource(Base, TimestampMixin, ActiveMixin):
    '''Модель доступных ресурсов в системе'''
    __tablename__ = 'resources'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    name: Mapped[str] = mapped_column(String(255))

    access_rules: Mapped[list['AccessRule']] = relationship(back_populates='resource',
                                                      cascade='all, delete-orphan')
    
    __table_args__ = (
        Index('idx_resources_name', 'name'),
        )
    


class UserSession(Base):
    '''Модель для сессий пользователей'''
    __tablename__ = 'sessions'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'))
    token_jti: Mapped[str] = mapped_column(String(255))
    token_type: Mapped[str] = mapped_column(String(20))

    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),
                                                 server_default=func.now(),
                                                 nullable=False)
    expires_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True),                                                 
                                                 nullable=False)
    is_revoked: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)

    user: Mapped['User'] = relationship(back_populates='sessions')

    __table_args__ = (
        Index('idx_sessions_user_id', 'user_id'),
        Index('idx_sessions_token_jti', 'token_jti'),
        Index('idx_sessions_expires_at', 'expires_at'),
        Index('idx_sessions_is_revoked', 'is_revoked'),
    )



class Message(Base, TimestampMixin, ActiveMixin):
    '''Модель сообщений пользователей'''
    __tablename__ = 'messages'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    owner_id: Mapped[int] = mapped_column(ForeignKey('users.id', ondelete='CASCADE'),
                                          nullable=False)
    book_id: Mapped[int] = mapped_column(ForeignKey('books.id', ondelete='CASCADE'))
    content: Mapped[str] = mapped_column(Text, nullable=False)

    msg_owner: Mapped['User'] = relationship(back_populates='messages',
                                         foreign_keys=[owner_id])
    book: Mapped['Book'] = relationship(back_populates='messages',
                                         foreign_keys=[book_id])


    __table_args__ = (
        CheckConstraint('CHAR_LENGTH(content) > 0', name='chk_message_length'),
        Index('idx_message_book_id', 'book_id'),
        Index('idx_message_owner_id', 'owner_id'),
    )



class Book(Base, TimestampMixin, ActiveMixin):
    '''Модель книг на представленных на сайте'''
    __tablename__ = 'books'

    id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
    author: Mapped[str] = mapped_column(String(255), nullable=True)
    title: Mapped[str] = mapped_column(String(1000), nullable=False)
    description: Mapped[str] = mapped_column(Text, nullable=False)
    year: Mapped[int] = mapped_column(nullable=True)

    buy_link: Mapped[str] = mapped_column(Text, nullable=False)
    read_link: Mapped[str] = mapped_column(Text, nullable=False)
    cover_url: Mapped[str] = mapped_column(String(500), nullable=True)
    

    messages: Mapped[list['Message']] = relationship(back_populates='book',
                                                     cascade='all, delete-orphan')
    
    __table_args__ = (
        CheckConstraint('CHAR_LENGTH(description) > 0', name='chk_book_description_length'),
    )


# class BookAuthors(Base):
#     '''Модель авторов книг на представленных на сайте'''
#     __tablename__ = 'authors'

#     id: Mapped[int] = mapped_column(Integer, Identity(), primary_key=True)
#     author: Mapped[list[str]] = mapped_column(String(255), nullable=False)


#     book: Mapped['Book'] = relationship(back_populates='authors',
#                                         cascade='all, delete-orphan')


#     __table_args__ = (
#         Index('idx_book_author', 'author'),
#     )