from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api import admin, assistant, auth, llm_jobs, recruiter, resume, runs, tasks, vibe
from app.core.config import settings
from app.db import Base, engine
import app.services.llm_handlers  # noqa: F401 — регистрация обработчиков job'ов
from app.services.llm_queue import start_workers, stop_workers


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Для dev/тестов (sqlite) таблицы создаются здесь;
    # в production схема применяется через alembic в entrypoint.sh.
    Base.metadata.create_all(bind=engine)
    start_workers()
    yield
    stop_workers()


app = FastAPI(title=settings.app_name, lifespan=lifespan)

if settings.cors_origin_list:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.cors_origin_list,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

app.include_router(auth.router)
app.include_router(tasks.router)
app.include_router(runs.router)
app.include_router(assistant.router)
app.include_router(resume.router)
app.include_router(recruiter.router)
app.include_router(vibe.router)
app.include_router(admin.router)
app.include_router(llm_jobs.router)


@app.get("/api/health")
def health():
    return {"status": "ok", "app": settings.app_name}
