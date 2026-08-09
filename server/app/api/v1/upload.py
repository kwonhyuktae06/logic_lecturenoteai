from typing import List
from fastapi import APIRouter, UploadFile, File, Depends, Form, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.upload import (
    UploadFileResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    UploadStatusResponse,
    PipelineAcceptedResponse,
)
from app.services.upload import (
    upload_file,
    upload_url,
    get_upload_status,
    process_audio_image_pipeline,
    run_pipeline_background,
)

router = APIRouter(prefix="/upload", tags=["upload"])


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


@router.get("/{upload_id}", response_model=UploadStatusResponse)
def get_status_endpoint(
    upload_id: str,
    db: Session = Depends(get_db)
):
    upload = get_upload_status(upload_id, db)
    return UploadStatusResponse(
        upload_id=upload.id,
        type=upload.type,
        status=upload.status,
        error_message=upload.error_message,
        transcript=upload.transcript,
        analysis=upload.analysis,
        created_at=upload.created_at,
        updated_at=upload.updated_at,
    )


@router.post("/pipeline", response_model=PipelineAcceptedResponse)
async def pipeline_endpoint(
    background_tasks: BackgroundTasks,
    audio: UploadFile = File(...),
    images: List[UploadFile] = File(...),
    image_count: int = Form(default=1),
    db: Session = Depends(get_db)
):
    if image_count < 1:
        raise HTTPException(status_code=400, detail="image_count는 1 이상이어야 해요.")

    if len(images) != image_count:
        raise HTTPException(status_code=400, detail="전송한 이미지 수와 image_count가 일치하지 않아요.")

    upload, audio_path, saved_images = await process_audio_image_pipeline(audio, images, db)
    background_tasks.add_task(run_pipeline_background, upload.id, audio_path, saved_images)

    return PipelineAcceptedResponse(
        upload_id=upload.id,
        status=upload.status,
        image_count=len(saved_images),
        audio_file_name=audio.filename,
    )