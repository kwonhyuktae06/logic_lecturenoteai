from fastapi import APIRouter, UploadFile, File, Depends
from sqlalchemy.orm import Session

from app.core.database import get_db
from app.schemas.upload import (
    UploadFileResponse,
    UploadUrlRequest,
    UploadUrlResponse,
    UploadStatusResponse
)
from app.services.upload import upload_file, upload_url, get_upload_status

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