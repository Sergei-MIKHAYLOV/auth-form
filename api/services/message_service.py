from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from fastapi import HTTPException, status
from db.models import Message, User, UserRole, Book
from api.models import MessageResponse
from api.deps import get_object_or_404, serialize_model, check_has_role, check_is_owner_or_has_all_permission
from dataclasses import dataclass


@dataclass
class MessagesInfo:
    messages_count: int
    messages_content: MessageResponse


class MessageService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def request_one_message(self,
                                  message_id: int) -> Message:
        
        result = await self.db.execute(select(Message)
                                       .where(Message.id == message_id)
                                        .options(
                                            selectinload(Message.msg_owner)
                                            .selectinload(User.user_roles)
                                            .selectinload(UserRole.role)))
        message = result.scalar_one_or_none()
        if not message:
            raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail='Сообщение не найдено')

        return message



    async def get_messages(self, book_id: int) -> MessagesInfo:
        query = select(Message)
    
        if book_id:
            query = query.where(Message.book_id == book_id)

        query = query.options(selectinload(Message.msg_owner)
                            .selectinload(User.user_roles)
                            .selectinload(UserRole.role))
        
        result = await self.db.execute(query.order_by(
            desc(func.coalesce(Message.updated_at, Message.created_at))
        ))
        messages = result.scalars().all()
        count = len(messages)

        serialized_messages = [serialize_model(m, MessageResponse) for m in messages]

        return MessagesInfo(count, serialized_messages)



    async def get_one_message(self,
                              message_id: int) -> MessageResponse:
        

        message = await self.request_one_message(message_id)

        if message.is_active == False:
            try:
                await check_has_role(roles=['admin', 'moderator'])
            except HTTPException:
                raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                                    detail=f'Сообщение не найдено')
       
        return serialize_model(message, MessageResponse)



    async def create_new_message(self,
                                 content: str,
                                 book_id: int,
                                 current_user: User) -> MessageResponse:
            
        book = await get_object_or_404(self.db, Book, book_id, 'Книга не найдена')
        if not book.is_active:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN,
                                detail=f'Книга `{book.title}` закрыта для комментирования')

        message = Message(owner_id=current_user.id, book_id=book_id, content=content)
        
        self.db.add(message)
        await self.db.commit()
        await self.db.refresh(message)

        return serialize_model(message, MessageResponse)
            

    async def edit_message(self,
                           message_id: int,
                           content: str,
                           current_user: User) -> MessageResponse:
        
        message = await self.request_one_message(message_id)
        check_is_owner_or_has_all_permission(message, current_user, 'messages', 'update')
    
        message.content = content
        await self.db.commit()
        await self.db.refresh(message)
        
        return serialize_model(message, MessageResponse)




    async def delete_message(self,
                             message_id: int,
                             current_user: User) -> None:

        message = await self.request_one_message(message_id)
        check_is_owner_or_has_all_permission(message, current_user, 'messages', 'delete')
        
        message.is_active = False
        await self.db.commit()

        return None