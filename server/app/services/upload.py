import uuid
import shutil
from pathlib import Path
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models.upload import Upload


# 파일 업로드 처리
async def upload_file(file: UploadFile, db: Session) -> Upload:

    # 확장자 체크
    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in settings.ALLOWED_EXTENSIONS:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 파일 형식이에요. 허용: {settings.ALLOWED_EXTENSIONS}"
        )

    # 파일 크기 체크
    file.file.seek(0, 2)          # 파일 끝으로 이동
    file_size = file.file.tell()  # 현재 위치 = 파일 크기
    file.file.seek(0)             # 다시 처음으로

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"파일 크기가 너무 커요. 최대 500MB"
        )

    # 저장할 파일명 (uuid로 중복 방지)
    upload_id = str(uuid.uuid4())
    save_filename = f"{upload_id}{file_ext}"
    save_path = settings.UPLOAD_PATH / save_filename

    # 파일 저장
    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    # DB 저장
    upload = Upload(
        id=upload_id,
        type="file",
        source=file.filename,
        file_path=str(save_path),
        file_size=file_size,
        status="pending"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return upload


# 1. 확장자 체크 → 2. 파일 크기 체크 → 3. 저장 → 4. DB 기록
async def upload_url(url: str, db: Session) -> Upload:

    # DB 저장
    upload_id = str(uuid.uuid4())
    upload = Upload(
        id=upload_id,
        type="url",
        source=url,
        status="pending"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return upload


# 업로드 상태 조회
def get_upload_status(upload_id: str, db: Session) -> Upload:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()

    if not upload:
        raise HTTPException(
            status_code=404,
            detail="업로드를 찾을 수 없어요."
        )

    return upload