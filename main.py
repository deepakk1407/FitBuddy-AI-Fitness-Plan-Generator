from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from config import settings
from database import init_db
from routes import api_router, router

@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


app = FastAPI(title=settings.app_name, description="AI-powered personalized fitness planning platform", version="1.0.0", lifespan=lifespan)
app.mount("/static", StaticFiles(directory="static"), name="static")
app.include_router(router)
app.include_router(api_router)


@app.get("/favicon.ico", include_in_schema=False)
def favicon():
    return ""
