from pydantic import BaseModel, ConfigDict, EmailStr, computed_field, Field
from fastapi import Form
from typing import TypeVar, Any, Optional
from datetime import datetime


PydanticModel = TypeVar('PydanticModel', bound=BaseModel)


PERMISSION_FIELDS = [
    'read', 'create', 'update', 'delete',
    'read_all', 'update_all', 'delete_all',
    'change_user_role', 'user_ban'
]

class UserSchema(BaseModel):
    '''Pydantic модель для валидации и ответов'''

    model_config = ConfigDict(from_attributes=True)

    id: int
    name: str
    family_name: str | None = None
    patronymic: str | None = None

    email: EmailStr
    is_active: bool = True

    user_roles: list[Any] | None = Field(exclude=True)

    @computed_field
    @property
    def roles(self) -> list[str]:
        return [ur.role.name for ur in self.user_roles] if self.user_roles else []
    
    @computed_field
    @property
    def permissions(self) -> dict[str, dict[str, bool]]:
        result = {}
        
        for user_role in self.user_roles or []:
            if not user_role.role.is_active:
                continue
            
            for rule in user_role.role.access_rules or []:
                if not rule.is_active or not rule.resource:
                    continue
                
                resource = rule.resource.name
                result[resource] = {perm: getattr(rule, f'{perm}_permission', False)
                                    for perm in PERMISSION_FIELDS}
        
        return result



class TokenPair(BaseModel):
    access_token: str
    refresh_token: str


class EmailCheck(BaseModel):
    email: EmailStr


class AccessRuleCreateRequest(BaseModel):
    role_id: int
    resource_id: int
    read_permission: bool = True
    read_all_permission: bool = False
    create_permission: bool = True
    update_permission: bool = True
    update_all_permission: bool = False
    delete_permission: bool = True
    delete_all_permission: bool = False
    change_user_role_permission: bool = False
    user_ban_permission: bool = False


class AccessRuleUpdateRequest(BaseModel):
    read_permission: bool | None = None
    read_all_permission: bool | None = None
    create_permission: bool | None = None
    update_permission: bool | None = None
    update_all_permission: bool | None = None
    delete_permission: bool | None = None
    delete_all_permission: bool | None = None
    change_user_role_permission: bool | None = None
    user_ban_permission: bool | None = None
 

class AccessRuleResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    
    id: int
    role_id: int
    resource_id: int
    read_permission: bool
    read_all_permission: bool
    create_permission: bool
    update_permission: bool
    update_all_permission: bool
    delete_permission: bool
    delete_all_permission: bool
    change_user_role_permission: bool
    user_ban_permission: bool
    is_active: bool

    role: Any | None = Field(default=None, exclude=True)
    resource: Any | None = Field(default=None, exclude=True)
    
    @computed_field
    @property
    def role_name(self) -> str:
        return self.role.name if self.role else ''
    
    @computed_field
    @property
    def resource_name(self) -> str:
        return self.resource.name if self.resource else ''
    


class MessageResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: int
    owner_id: int
    book_id: int
    content: str
    created_at: datetime | None
    updated_at: datetime | None
    is_active: bool

    msg_owner: Optional[UserSchema] = None

    @computed_field
    @property
    def display_date(self) -> datetime:
        return self.updated_at or self.created_at



class BookSchema(BaseModel):

    model_config = ConfigDict(from_attributes=True)

    id: int

    title: str
    author: str | None = None
    description: str
    year: int | None = None
    buy_link: str
    read_link: str
    cover_url: str | None = None
