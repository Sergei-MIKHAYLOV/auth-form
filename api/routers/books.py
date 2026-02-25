from fastapi import APIRouter, Depends, Query, Form, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, desc
from sqlalchemy.orm import selectinload
from db.db_init import get_db
from db.models import Book
from api.models import BookSchema
from api.deps import check_permission, get_object_or_404, save_file_on_disc, serialize_model
from pathlib import Path



books_router = APIRouter(prefix='/books')


@books_router.get('/', summary='Получить список всех книг')
async def get_books(db: AsyncSession = Depends(get_db)):
       
    result = await db.execute(select(Book))
    books = result.scalars().all()
    
    return {'count': len(books),
            'books': [serialize_model(b, BookSchema) for b in books]}




@books_router.get('/{book_id}', summary='Получить одну книгу',
                     dependencies=[Depends(check_permission('books', 'read'))])
async def get_book(book_id: int,
                   db: AsyncSession = Depends(get_db)):
    
    message = await get_object_or_404(db, Book, book_id)   
    return serialize_model(message, BookSchema)



@books_router.get('/covers/{filename}', summary='Просмотреть обложку для книги')
async def get_cover(filename: str):

    file_path = Path('app/uploads/covers') / filename
    
    if not file_path.exists():
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND,
                            detail=f'Файл обложки не найден')
    
    return FileResponse(file_path, media_type='image/jpeg')




@books_router.post('/', summary='Добавить новую книгу',
                   dependencies=[Depends(check_permission('books', 'create'))])
async def create_book(title: str = Form(..., min_length=1, max_length=1000),
                      author: str | None = Form(None, max_length=255),
                      description: str = Form(..., min_length=1),
                      year: int | None = Form(None, ge=1000, le=2100),
                      buy_link: str = Form(..., min_length=1),
                      read_link: str = Form(..., min_length=1),
                      cover_url: str | None = Form(None),
                      cover_file: UploadFile | None = File(None),
                      db: AsyncSession = Depends(get_db)):
    
    result = await db.execute(select(Book).where(Book.title == title))
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
    
    db.add(new_book)
    await db.commit()
    await db.refresh(new_book)
    
    return {'book': 'Книга добавлена на сайт',
            'data': serialize_model(new_book, BookSchema)}



@books_router.patch('/{book_id}', summary='Редактировать книгу',
                   dependencies=[Depends(check_permission('books', 'update'))])
async def update_book(book_id: int,
                      title: str = Form(..., min_length=1, max_length=1000),
                      author: str | None = Form(None, max_length=255),
                      description: str = Form(..., min_length=1),
                      year: int | None = Form(None, ge=1000, le=2100),
                      buy_link: str = Form(..., min_length=1),
                      read_link: str = Form(..., min_length=1),
                      cover_url: str | None = Form(None),
                      cover_file: UploadFile | None = File(None),
                      db: AsyncSession = Depends(get_db)):
    
    book = await get_object_or_404(db, Book, book_id)
    
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
   
    await db.commit()
    await db.refresh(book)
    
    return {'book': 'Данные книги обновлены', 
            'data': serialize_model(book, BookSchema)}



@books_router.delete('/{book_id}', summary='Удалить книгу (скрыть от пользоателей)',
                   dependencies=[Depends(check_permission('books', 'delete'))])
async def delete_book(book_id: int,
                      db: AsyncSession = Depends(get_db)):
    
    book = await get_object_or_404(db, Book, book_id)
    book.is_active = False
    await db.commit()
    
    return {'book': 'Книга скрыта'}
