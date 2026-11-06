"""FastAPI entry: CORS, routers, SQLite bootstrap, local storage mount."""

from contextlib import asynccontextmanager

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException

from app.api import annotation, auth, dashboard, datasets, devices, review, sessions, system, tasks
from app.core.config import RAW_DIR, STORAGE_DIR, settings
from app.db import models  # noqa: F401
from app.db.database import Base, SessionLocal, engine
from app.services.bootstrap import seed_if_empty


@asynccontextmanager
async def lifespan(_app: FastAPI):
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    (STORAGE_DIR / "export").mkdir(parents=True, exist_ok=True)
    Base.metadata.create_all(bind=engine)
    db = SessionLocal()
    try:
        seed_if_empty(db)
    finally:
        db.close()
    yield


app = FastAPI(
    title="OpenDF 具身智能采标平台",
    description="多源异构数据采集、多模态时间轴标注与 LeRobot 导出。",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.exception_handler(StarletteHTTPException)
async def http_exception_handler(_request: Request, exc: StarletteHTTPException):
    detail = exc.detail
    message = detail if isinstance(detail, str) else "请求失败"
    return JSONResponse(status_code=exc.status_code, content={"code": exc.status_code, "message": message, "data": None})


@app.exception_handler(RequestValidationError)
async def validation_exception_handler(_request: Request, exc: RequestValidationError):
    return JSONResponse(
        status_code=422,
        content={"code": 422, "message": "参数校验失败", "data": exc.errors()},
    )


prefix = settings.api_prefix
app.include_router(auth.router, prefix=prefix)
app.include_router(dashboard.router, prefix=prefix)
app.include_router(devices.router, prefix=prefix)
app.include_router(tasks.router, prefix=prefix)
app.include_router(sessions.router, prefix=prefix)
app.include_router(annotation.router, prefix=prefix)
app.include_router(review.router, prefix=prefix)
app.include_router(datasets.router, prefix=prefix)
app.include_router(system.router, prefix=prefix)

app.mount("/storage", StaticFiles(directory=str(STORAGE_DIR)), name="storage")


@app.get("/")
def root():
    return {
        "name": settings.app_name,
        "docs": "/docs",
        "api": prefix,
    }
