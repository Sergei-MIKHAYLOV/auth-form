from fastapi import APIRouter, Depends, Form, HTTPException, status, UploadFile, File
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from db.db_init import get_db
from api.deps import check_permission
from pathlib import Path
from api.services.book_service import BookService



books_router = APIRouter(prefix='/books')


@books_router.get('/', summary='Получить список всех книг')
async def get_books(db: AsyncSession = Depends(get_db)):
           
    service = BookService(db)
    books = await service.get_books()
    
    return {'count': books.books_count,
            'books': books.books_content}




@books_router.get('/{book_id}', summary='Получить одну книгу',
                     dependencies=[Depends(check_permission('books', 'read'))])
async def get_book(book_id: int,
                   db: AsyncSession = Depends(get_db)):
    
    service = BookService(db)
    book = await service.get_one_book(book_id)
    
    return book



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
    
    service = BookService(db)
    book = await service.create_new_book(title, author, description, year, buy_link, read_link, cover_url, cover_file)
    
    return {'book': 'Книга добавлена на сайт',
            'data': book}



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
    
    service = BookService(db)
    book = await service.edit_book(book_id, title, author, description, year, buy_link, read_link, cover_url, cover_file)
    
    return {'book': 'Данные книги обновлены', 
            'data': book}



@books_router.delete('/{book_id}', summary='Удалить книгу (скрыть от пользоателей)',
                   dependencies=[Depends(check_permission('books', 'delete'))])
async def delete_book(book_id: int,
                      db: AsyncSession = Depends(get_db)):
    
    service = BookService(db)
    await service.delete_book(book_id)
    
    return {'book': 'Книга скрыта'}
