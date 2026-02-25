from fastapi import APIRouter, Depends, Query, Form, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from db.db_init import get_db
from db.models import Message, User, Book, UserRole
from api.models import MessageResponse
from api.deps import (get_current_user, check_permission, get_object_or_404, check_has_role, 
                      check_is_owner_or_has_all_permission, serialize_model)


messages_router = APIRouter(prefix='/messages')



@messages_router.get('/', summary='Получить список всех сообщений')
async def get_messages(book_id: int | None = Query(None),
                       db: AsyncSession = Depends(get_db)):
    
    query = select(Message)
    
    if book_id:
        query = query.where(Message.book_id == book_id)

    query = query.options(selectinload(Message.msg_owner)
                          .selectinload(User.user_roles)
                          .selectinload(UserRole.role))
    
    result = await db.execute(query.order_by(
        desc(func.coalesce(Message.updated_at, Message.created_at))
    ))
    messages = result.scalars().all()
    
    return {
        'count': len(messages),
        'messages': [serialize_model(m, MessageResponse) for m in messages]
    }




@messages_router.get('/{message_id}', summary='Получить одно сообщение',
                     dependencies=[Depends(check_permission('messages', 'read'))])
async def get_message(message_id: int,
                      db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(Message)
                              .where(Message.id == message_id)
                              .options(
                                  selectinload(Message.msg_owner)
                                  .selectinload(User.user_roles)
                                  .selectinload(UserRole.role)))
    message = result.scalar_one_or_none()
    
    if message.is_active == False:
        try:
            await check_has_role(roles=['admin', 'moderator'])
        except HTTPException:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                detail=f'Сообщение не найдено')
       
    return serialize_model(message, MessageResponse)




@messages_router.post('/', summary='Создать новое сообщение')
async def create_message(content: str = Form(...),
                         book_id: int = Form(...),
                         current_user: User = Depends(check_permission('messages', 'create')),
                         db: AsyncSession = Depends(get_db)):
    
    book = await get_object_or_404(db, Book, book_id, 'Книга не найдена')
    if not book.is_active:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                            detail=f'Книга `{book.title}` закрыта для комментирования')

    message = Message(owner_id=current_user.id, book_id=book_id, content=content)
    
    db.add(message)
    await db.commit()
    await db.refresh(message)
    
    return {'message': 'Сообщение создано',
            'data': serialize_model(message, MessageResponse)}



@messages_router.patch('/{message_id}', summary='Редактировать сообщение')
async def update_message(message_id: int,
                         content: str = Form(...),
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(Message)
                            .where(Message.id == message_id)
                            .options(
                                selectinload(Message.msg_owner)
                                .selectinload(User.user_roles)
                                .selectinload(UserRole.role)))
    message = result.scalar_one_or_none()
    check_is_owner_or_has_all_permission(message, current_user, 'messages', 'update')
    
    message.content = content
    await db.commit()
    await db.refresh(message)
    
    return {'message': 'Сообщение обновлено', 
            'data': serialize_model(message, MessageResponse)}



@messages_router.delete('/{message_id}', summary='Удалить сообщение (мягкое)')
async def delete_message(message_id: int,
                         current_user: User = Depends(get_current_user),
                         db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(Message)
                            .where(Message.id == message_id)
                            .options(
                                selectinload(Message.msg_owner)
                                .selectinload(User.user_roles)
                                .selectinload(UserRole.role)))
    message = result.scalar_one_or_none()
    check_is_owner_or_has_all_permission(message, current_user, 'messages', 'delete')

    message.is_active = False
    await db.commit()
    
    return {'message': 'Сообщение удалено'}

