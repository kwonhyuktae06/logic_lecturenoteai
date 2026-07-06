from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import settings
from app.core.database import engine
from app.models.upload import Base
from app.api.v1 import upload

# DB 테이블 자동 생성
Base.metadata.create_all(bind=engine)

app = FastAPI(
    title=settings.APP_NAME,
    debug=settings.DEBUG
)

# CORS 설정 (프론트엔드 연결용)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # 나중에 프론트 URL로 교체
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 라우터 등록
app.include_router(upload.router, prefix="/api/v1")


@app.get("/")
def health_check():
    return {"status": "ok", "app": settings.APP_NAME}