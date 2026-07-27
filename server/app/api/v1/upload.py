from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.upload import (
    UploadFileResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    UploadStatusResponse,
    PipelineResponse,
)
from app.services.upload import upload_file, upload_url, get_upload_status, process_audio_image_pipeline

router = APIRouter(prefix="/upload", tags=["upload"])


# 프론트에서 multipart/form-data 형식으로 파일 전송
# 응답: upload_id, file_name, file_size, status
@router.post("/file", response_model=UploadFileResponse)
async def upload_file_endpoint(
    file: UploadFile = File(...),
    db: Session = Depends(get_db)
):
    upload = await upload_file(file, db)
    return UploadFileResponse(
        upload_id=upload.id,
        file_name=upload.source,
        file_size=upload.file_size,
        status=upload.status
    )


# URL 업로드
@router.post("/url", response_model=UploadUrlResponse)
async def upload_url_endpoint(
    request: UploadUrlRequest,
    db: Session = Depends(get_db)
):
    upload = await upload_url(str(request.url), db)
    return UploadUrlResponse(
        upload_id=upload.id,
        url=upload.source,
        status=upload.status
    )


# 업로드 상태 조회
@router.get("/{upload_id}", response_model=UploadStatusResponse)
def get_status_endpoint(
    upload_id: str,
    db: Session = Depends(get_db)
):
    return get_upload_status(upload_id, db)


# 음성 + 이미지 파이프라인 처리
@router.post("/pipeline", response_model=PipelineResponse)
async def pipeline_endpoint(
    audio: UploadFile = File(...),
    images: List[UploadFile] = File(...),
    image_count: int = Form(default=1),
    db: Session = Depends(get_db)
):
    if image_count < 1:
        raise HTTPException(status_code=400, detail="image_count는 1 이상이어야 해요.")

    if len(images) != image_count:
        raise HTTPException(status_code=400, detail="전송한 이미지 수와 image_count가 일치하지 않아요.")

    result = await process_audio_image_pipeline(audio, images, db)
    return PipelineResponse(**result)