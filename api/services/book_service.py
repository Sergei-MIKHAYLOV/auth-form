from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from fastapi import HTTPException, status, UploadFile
from db.models import Book
from api.models import BookSchema
from api.deps import get_object_or_404, serialize_model, save_file_on_disc
from dataclasses import dataclass


@dataclass
class BookInfo:
    books_count: int
    books_content: BookSchema


class BookService:
    def __init__(self, db: AsyncSession):
        self.db = db


    async def get_books(self) -> BookInfo:

        result = await self.db.execute(select(Book))
        books = result.scalars().all()

        books_count = len(books)
        books_content = [serialize_model(b, BookSchema) for b in books]
        
        return BookInfo(books_count, books_content)



    async def get_one_book(self,
                           book_id: int) -> BookSchema:
        
        book = await get_object_or_404(self.db, Book, book_id)   
        return serialize_model(book, BookSchema)
        



    async def create_new_book(self,
                              title: str,
                              author: str | None,
                              description: str,
                              year: int | None,
                              buy_link: str,
                              read_link: str,
                              cover_url: str | None,
                              cover_file: UploadFile | None) -> BookSchema:
            
        result = await self.db.execute(select(Book).where(Book.title == title))
        book = result.scalar_one_or_none() 
        if book:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST,
                                detail=f'Книга `{title}` уже добавлена на сайт')
        
        if cover_file:
            unique_filename = await save_file_on_disc(cover_file)
            cover_url = f'/books/covers/{unique_filename}'

        new_book = Book(title=title,
                        author=author,
                        description=description,
                        year=year,
                        buy_link=buy_link,
                        read_link=read_link,
                        cover_url=cover_url)
        
        self.db.add(new_book)
        await self.db.commit()
        await self.db.refresh(new_book)
        
        return serialize_model(new_book, BookSchema)
    

            

    async def edit_book(self,
                        book_id: int,
                        title: str,
                        author: str | None,
                        description: str,
                        year: int | None,
                        buy_link: str,
                        read_link: str,
                        cover_url: str | None,
                        cover_file: UploadFile | None) -> BookSchema:
        
        book = await get_object_or_404(self.db, Book, book_id)
        
        update_data = {'title': title,
                    'author': author,
                    'description': description,
                    'year': year,
                    'buy_link': buy_link,
                    'read_link': read_link,
                    'cover_url': cover_url }
        
        for field, value in update_data.items():
            if value is not None:
                setattr(book, field, value)

        if cover_file and cover_file.filename:
            book.cover_url = await save_file_on_disc(cover_file)
    
        await self.db.commit()
        await self.db.refresh(book)
        
        return serialize_model(book, BookSchema)




    async def delete_book(self,
                          book_id: int) -> None:

        book = await get_object_or_404(self.db, Book, book_id)
        book.is_active = False
        await self.db.commit()

        return None
    