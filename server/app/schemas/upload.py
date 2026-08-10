from pydantic import BaseModel, HttpUrl
from typing import Optional
from datetime import datetime


class UploadFileResponse(BaseModel):
    upload_id: str
    file_name: str
    file_size: int
    status: str

    class Config:
        from_attributes = True


class UploadUrlRequest(BaseModel):
    url: HttpUrl


class UploadUrlResponse(BaseModel):
    upload_id: str
    url: str
    status: str

    class Config:
        from_attributes = True


class UploadStatusResponse(BaseModel):
    upload_id: str
    type: str
    status: str
    error_message: Optional[str] = None
    transcript: Optional[str] = None
    analysis: Optional[str] = None
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class PipelineAcceptedResponse(BaseModel):
    upload_id: str
    status: str
    image_count: int
    audio_file_name: str

    class Config:
        from_attributes = True