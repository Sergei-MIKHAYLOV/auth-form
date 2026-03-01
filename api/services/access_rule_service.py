
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from db.models import AccessRule, Role, Resource
from api.models import AccessRuleResponse, AccessRuleCreateRequest
from api.deps import get_object_or_404
from dataclasses import dataclass


@dataclass
class RulesInfo:
    role: Role
    resource: Resource


@dataclass
class ResourceInfo:
    resource_name: str
    rule_id: int


class AccessRuleService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def request_rule_change(self,
                                  role_id: int,
                                  resource_id: int) -> AccessRule:
        
        role = await get_object_or_404(self.db, Role, role_id, 'Роль не найдена')
        resource = await get_object_or_404(self.db, Resource, resource_id, 'Ресурс не найден')
        
        # Проверка дубликатов правила
        result = await self.db.execute(select(AccessRule)
                                       .where(AccessRule.role_id == role_id,
                                        AccessRule.resource_id == resource_id))
        if result.scalar_one_or_none():
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f'Правило уже существует для роли `{role.name}` и ресурса `{resource.name}`')

        return RulesInfo(role, resource)


    async def get_access_rules(self) -> list:
        result = await self.db.execute(select(AccessRule)
                                       .options(selectinload(AccessRule.role),
                                       selectinload(AccessRule.resource)))
        
        rules = result.scalars().all()   
        rules_list = [AccessRuleResponse.model_validate(r) for r in rules]

        return rules_list


    async def create_access_rule(self,
                                 request: AccessRuleCreateRequest) -> ResourceInfo:
        
        can_create = await self.request_rule_change(request.role_id, request.resource_id)

        if can_create:
            rule = AccessRule(**request.model_dump())
            self.db.add(rule)
            await self.db.commit()
            await self.db.refresh(rule)        

        return ResourceInfo(can_create.resource.name, rule.id)



    async def update_access_rule(self,
                                 rule_id: int,
                                 request: AccessRuleCreateRequest) -> None:
        
        rule = await get_object_or_404(self.db, AccessRule, rule_id)
    
        update_data = request.model_dump(exclude_unset=True)
        for field, value in update_data.items():
            setattr(rule, field, value)
        
        await self.db.commit()
        await self.db.refresh(rule)

        return None



    async def delete_access_rule(self, rule_id: int) -> None:

        rule = await get_object_or_404(self.db, AccessRule, rule_id)
        
        await self.db.delete(rule)
        await self.db.commit()

        return None