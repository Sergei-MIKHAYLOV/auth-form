from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from api.protect_docs import AuthDocsMiddleware
from api.routers.auth import auth_router
from api.routers.users import users_router
from api.routers.messages import messages_router
from api.routers.books import books_router
from api.routers.access_control import access_control_router


app = FastAPI(title='BookStore API',
              description='API для магазина книг',
              docs_url=None,
              redoc_url=None,
              openapi_url=None)


app.add_route('/docs', app.swagger_ui_oauth2_redirect_url)
app.add_route('/redoc', app.redoc_url)
app.add_route('/openapi.json', app.openapi)

app.add_middleware(AuthDocsMiddleware)

app.include_router(auth_router)
app.include_router(users_router)
app.include_router(messages_router)
app.include_router(books_router)
app.include_router(access_control_router)

@app.get("/health")
def health():
    return {"status": "ok"}


app.mount("/", StaticFiles(directory="frontend", html=True), name="static")


