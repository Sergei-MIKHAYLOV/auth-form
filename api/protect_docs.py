from fastapi import Depends, Request, status
from fastapi.responses import FileResponse
from sqlalchemy.ext.asyncio import AsyncSession
from starlette.middleware.base import BaseHTTPMiddleware
from db.db_init import get_db
from api.deps import get_current_user
import logging


logger = logging.getLogger(__name__)

DOCS_PATHS = ['/docs', '/redoc', '/openapi.json']
NOT_FOUND_HTML = './frontend/404.html'


class AuthDocsMiddleware(BaseHTTPMiddleware):
    '''
    Middleware для защиты Swagger/ReDoc документации.
    '''
    
    async def dispatch(self,
                       request: Request,
                       call_next,
                       db: AsyncSession = Depends(get_db),):

        if not any(request.url.path.startswith(path) for path in DOCS_PATHS):
            return await call_next(request)
        
        not_found_response = FileResponse(status_code=status.HTTP_404_NOT_FOUND,
                                          path=NOT_FOUND_HTML)
        
        
        auth_header = request.headers.get('Authorization', '')
        if not auth_header.startswith('Bearer '):
            return not_found_response
        
        token = auth_header.replace('Bearer ', '')

        current_user = await get_current_user(token, db)
        try:
            user_roles = [ur.role.name for ur in current_user.user_roles]
            if 'admin' not in user_roles:
                return not_found_response
                
            return await call_next(request)
        except Exception as e:
            logger.debug(f'Docs auth failed: {e}')
            return not_found_response