from pathlib import Path
from fastapi import APIRouter, UploadFile, File, Depends, HTTPException, BackgroundTasks
from sqlalchemy.orm import Session

from app.core.config import settings
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
    process_video_pipeline,
    run_pipeline_background,
)

router = APIRouter(prefix="/upload", tags=["upload"])


# 파일 업로드 엔드포인트
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


# URL 업로드 엔드포인트
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


# 업로드 상태 조회 엔드포인트
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
    video: UploadFile = File(...), 
    db: Session = Depends(get_db)
):
    allowed_video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    file_ext = Path(video.filename).suffix.lower()
    if file_ext not in allowed_video_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 영상 형식이에요. 허용: {allowed_video_extensions}"
        )

    video.file.seek(0, 2)
    file_size = video.file.tell()
    video.file.seek(0)
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail="파일 크기가 너무 커요. 최대 500MB"
        )

    upload, video_path = await process_video_pipeline(video, db)
    background_tasks.add_task(run_pipeline_background, upload.id, video_path)

    return PipelineAcceptedResponse(
        upload_id=upload.id,
        status=upload.status,
        video_file_name=video.filename,
    )