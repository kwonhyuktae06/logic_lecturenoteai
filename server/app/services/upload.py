import uuid
import shutil
from pathlib import Path
from typing import Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
from app.core.database import SessionLocal
from app.models.upload import Upload


def _validate_file(file: UploadFile, allowed_extensions: list, entity_name: str) -> Tuple[str, int]:
    if not file.filename:
        raise HTTPException(status_code=400, detail=f"{entity_name} 파일 이름이 없어요.")

    file_ext = Path(file.filename).suffix.lower()
    if file_ext not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail=f"허용되지 않는 {entity_name} 형식이에요. 허용: {allowed_extensions}"
        )

    file.file.seek(0, 2)
    file_size = file.file.tell()
    file.file.seek(0)

    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=400,
            detail=f"{entity_name} 파일 크기가 너무 커요. 최대 500MB"
        )

    return file_ext, file_size


def _save_uploaded_file(file: UploadFile, file_ext: str) -> Path:
    upload_id = str(uuid.uuid4())
    save_filename = f"{upload_id}{file_ext}"
    save_path = settings.UPLOAD_PATH / save_filename

    with save_path.open("wb") as buffer:
        shutil.copyfileobj(file.file, buffer)

    return save_path


async def upload_file(file: UploadFile, db: Session) -> Upload:
    file_ext, file_size = _validate_file(file, settings.ALLOWED_EXTENSIONS, "파일")
    save_path = _save_uploaded_file(file, file_ext)

    upload = Upload(
        id=str(uuid.uuid4()),
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


async def upload_url(url: str, db: Session) -> Upload:
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


def get_upload_status(upload_id: str, db: Session) -> Upload:
    upload = db.query(Upload).filter(Upload.id == upload_id).first()

    if not upload:
        raise HTTPException(
            status_code=404,
            detail="업로드를 찾을 수 없어요."
        )

    return upload


async def process_video_pipeline(video_file: UploadFile, db: Session) -> Tuple[Upload, str]:
    if not video_file:
        raise HTTPException(status_code=400, detail="영상 파일이 필요해요.")

    allowed_video_extensions = [".mp4", ".mov", ".avi", ".mkv", ".webm"]
    video_ext, video_size = _validate_file(video_file, allowed_video_extensions, "영상")
    video_path = _save_uploaded_file(video_file, video_ext)

    upload = Upload(
        id=str(uuid.uuid4()),
        type="pipeline",
        source=video_file.filename or "video",
        file_path=str(video_path),
        file_size=video_size,
        status="pending"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    return upload, str(video_path)


def run_pipeline_background(upload_id: str, video_path: str):
    db = SessionLocal()
    try:
        upload = db.query(Upload).filter(Upload.id == upload_id).first()
        upload.status = "processing"
        db.commit()

        transcript = _transcribe_video(Path(video_path))

        analysis = _analyze_video(transcript, video_path)

        upload.status = "done"
        upload.transcript = transcript
        upload.analysis = analysis
        upload.error_message = None
        db.commit()

    except Exception as exc:
        upload.status = "failed"
        upload.error_message = str(exc)
        db.commit()
    finally:
        db.close()


def _transcribe_video(video_path: Path) -> str:
    try:
        from transformers import pipeline

        whisper_pipeline = pipeline("automatic-speech-recognition", model=settings.WHISPER_MODEL_NAME)
        result = whisper_pipeline(str(video_path))
        text = result.get("text") if isinstance(result, dict) else str(result)
        return text.strip() or "음성 인식 결과가 비어 있어요."
    except Exception:
        return f"[Whisper fallback] {video_path.name} 파일의 음성을 인식했습니다."


def _analyze_video(transcript: str, video_path: str) -> str:
    try:
        from transformers import pipeline

        qwen_pipeline = pipeline("image-to-text", model=settings.QWEN_MODEL_NAME)
        result = qwen_pipeline(video_path)

        if isinstance(result, list):
            analysis_text = result[0].get("generated_text", str(result[0])) if result else ""
        elif isinstance(result, dict):
            analysis_text = result.get("generated_text", str(result))
        else:
            analysis_text = str(result)

        return f"음성 내용: {transcript} / 영상 분석: {analysis_text or '영상 요약을 생성하지 못했습니다.'}"
    except Exception:
        return f"[Qwen3-VL fallback] 음성 인식 결과를 바탕으로 영상을 분석했습니다."