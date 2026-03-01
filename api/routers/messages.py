from fastapi import APIRouter, Depends, Query, Form
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from db.models import User
from api.services.message_service import MessageService
from api.deps import get_current_user, check_permission


messages_router = APIRouter(prefix='/messages')

@messages_router.get('/', summary='Получить список всех сообщений')
async def get_messages(book_id: int | None = Query(None),
                       db: AsyncSession = Depends(get_db)):
    
    service = MessageService(db)
    messages = await service.get_messages(book_id)
    
    return {'count': messages.messages_count,
            'messages': messages.messages_content}



@messages_router.get('/{message_id}', summary='Получить одно сообщение',
                     dependencies=[Depends(check_permission('messages', 'read'))])
async def get_message(message_id: int,
                      db: AsyncSession = Depends(get_db)):
    
    service = MessageService(db)
    message = await service.get_one_message(message_id)
       
    return message



@messages_router.post('/', summary='Создать новое сообщение')
async def create_message(content: str = Form(...),
                         book_id: int = Form(...),
                         current_user: User = Depends(check_permission('messages', 'create')),
                         db: AsyncSession = Depends(get_db)):
    
    service = MessageService(db)
    message = await service.create_new_message(content, book_id, current_user)
    
    return {'message': 'Сообщение создано',
            'content': message}



@messages_router.patch('/{message_id}', summary='Редактировать сообщение')
async def update_message(message_id: int,
                         content: str = Form(...),
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    
    service = MessageService(db)
    message = await service.edit_message(message_id, content, current_user)
    
    return {'message': 'Сообщение обновлено',
            'content': message}



@messages_router.delete('/{message_id}', summary='Удалить сообщение (мягкое)')
async def delete_message(message_id: int,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    
    service = MessageService(db)
    await service.delete_message(message_id, current_user)
    
    return {'message': 'Сообщение удалено'}

