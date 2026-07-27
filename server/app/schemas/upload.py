from pydantic import BaseModel, HttpUrl
from typing import Optional, List
from datetime import datetime


# 파일 업로드 응답
class UploadFileResponse(BaseModel):
    upload_id: str
    file_name: str
    file_size: int
    status: str

    class Config:
        from_attributes = True


# URL 업로드 요청
class UploadUrlRequest(BaseModel):
    url: HttpUrl


# URL 업로드 응답
class UploadUrlResponse(BaseModel):
    upload_id: str
    url: str
    status: str

    class Config:
        from_attributes = True


# 업로드 상태 조회 응답
class UploadStatusResponse(BaseModel):
    upload_id: str
    type: str
    status: str
    error_message: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


# 음성/이미지 처리 응답
class PipelineResponse(BaseModel):
    upload_id: str
    status: str
    transcript: str
    analysis: str
    image_count: int
    audio_file_name: str
    images: List[str]

    class Config:
        from_attributes = True