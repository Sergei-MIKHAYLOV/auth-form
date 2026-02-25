from pydantic import ValidationError
from api.models import EmailCheck
from fastapi import APIRouter, Depends, HTTPException, Form, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from typing import Type
from db.models import SqlModel
from db.db_init import get_db
from api.deps import get_object_or_404



def is_correct_email(email: str) -> dict:
    try:
        email = EmailCheck(email=email).email        
    except ValidationError:
        raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail='Некорректный формат email')
    
    return {'valid': True}



def create_crud_router(model: Type[SqlModel],
                       resource_name: str,
                       dependencies: list = None) -> APIRouter:
    '''
    Фабрика для создания CRUD роутеров.
    
    Аргументы:
        `model` - модель sqlalchemy.orm 
        `resource_name` - имя ресурса ('users', 'messages', 'roles', 'access_rules')
        `dependencies` - список зависимостей FastAPI
    
    Возвращает:
        APIRouter с endpoint'ами: `GET /`, `GET /{id}`, `POST /`, `PATCH /{id}`, `DELETE /{id}`
    '''
   
    router = APIRouter(prefix=f'/{resource_name}', 
                       dependencies=dependencies or [])
    
    @router.get('/')
    async def get_all(db: AsyncSession = Depends(get_db)):
        result = await db.execute(select(model)) 
        objects = result.scalars().all()

        def serialize_obj(o):
            data = {'id': o.id, 'name': o.name}
            if hasattr(o, 'description'):
                data['description'] = o.description
            return data

        return {'count': len(objects),
                resource_name: [serialize_obj(o) for o in objects]}
    
    @router.get('/{id}')
    async def get_one(id: int, db: AsyncSession = Depends(get_db)):
        obj = await get_object_or_404(db, model, id)
        return {'id': obj.id, 'name': obj.name}
    
    @router.post('/')
    async def create(name: str = Form(...),
                     description: str = Form(''), 
                     db: AsyncSession = Depends(get_db)):
        obj = model(name=name)
        if description:
            obj.description = description
        db.add(obj)
        await db.commit()
        await db.refresh(obj)
        return {'message': f'Создан новый ресурс {resource_name}', 'id': obj.id}
    
    @router.patch('/{id}')
    async def update(id: int, name: str = Form(...), description: str = Form(''), db: AsyncSession = Depends(get_db)):
        obj = await get_object_or_404(db, model, id)
        obj.name = name
        if description:
            obj.description = description
        await db.commit()
        return {'message': f'Обновлен ресурс {resource_name}', 'id': obj.id}
    
    @router.delete('/{id}')
    async def delete(id: int, db: AsyncSession = Depends(get_db)):
        obj = await get_object_or_404(db, model, id)
        await db.delete(obj)
        await db.commit()
        return {'message': f'Ресурс {resource_name} удалён'}
    
    return router