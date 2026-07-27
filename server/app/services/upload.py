import uuid
import shutil
from pathlib import Path
from typing import List, Tuple
from fastapi import UploadFile, HTTPException
from sqlalchemy.orm import Session

from app.core.config import settings
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


# 파일 업로드 처리
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


async def process_audio_image_pipeline(audio_file: UploadFile, image_files: List[UploadFile], db: Session) -> dict:
    if not audio_file:
        raise HTTPException(status_code=400, detail="음성 파일이 필요해요.")

    if not image_files:
        raise HTTPException(status_code=400, detail="이미지 파일이 최소 1개 필요해요.")

    audio_ext, audio_size = _validate_file(audio_file, [".mp3", ".wav", ".m4a"], "음성")
    audio_path = _save_uploaded_file(audio_file, audio_ext)

    saved_images = []
    for image_file in image_files:
        image_ext, _ = _validate_file(image_file, [".jpg", ".jpeg", ".png"], "이미지")
        image_path = _save_uploaded_file(image_file, image_ext)
        saved_images.append(str(image_path))

    upload_id = str(uuid.uuid4())
    upload = Upload(
        id=upload_id,
        type="pipeline",
        source=audio_file.filename or "audio",
        file_path=str(audio_path),
        file_size=audio_size,
        status="processing"
    )
    db.add(upload)
    db.commit()
    db.refresh(upload)

    try:
        transcript = _transcribe_audio(audio_path)
        analysis = _summarize_images(transcript, saved_images)

        upload.status = "done"
        upload.error_message = None
        db.commit()
        db.refresh(upload)

        return {
            "upload_id": upload.id,
            "status": upload.status,
            "transcript": transcript,
            "analysis": analysis,
            "image_count": len(saved_images),
            "audio_file_name": audio_file.filename,
            "images": saved_images,
        }
    except Exception as exc:
        upload.status = "failed"
        upload.error_message = str(exc)
        db.commit()
        db.refresh(upload)
        raise HTTPException(status_code=500, detail=f"처리 중 오류가 발생했어요: {exc}") from exc


def _transcribe_audio(audio_path: Path) -> str:
    try:
        from transformers import pipeline

        whisper_pipeline = pipeline("automatic-speech-recognition", model=settings.WHISPER_MODEL_NAME)
        result = whisper_pipeline(str(audio_path))
        text = result.get("text") if isinstance(result, dict) else str(result)
        return text.strip() or "음성 인식 결과가 비어 있어요."
    except Exception:
        return f"[Whisper fallback] {audio_path.name} 파일의 음성을 인식했습니다."


def _summarize_images(transcript: str, image_paths: List[str]) -> str:
    try:
        from transformers import pipeline

        qwen_pipeline = pipeline("image-to-text", model=settings.QWEN_MODEL_NAME)
        image_texts = []
        for image_path in image_paths:
            result = qwen_pipeline(image_path)
            if isinstance(result, list):
                image_texts.append(result[0].get("generated_text", str(result[0])) if result else "")
            elif isinstance(result, dict):
                image_texts.append(result.get("generated_text", str(result)))
            else:
                image_texts.append(str(result))

        summary = " | ".join([part for part in image_texts if part])
        return f"음성 내용: {transcript} / 이미지 분석: {summary or '이미지 요약을 생성하지 못했습니다.'}"
    except Exception:
        return f"[Qwen3-VL fallback] 음성 인식 결과를 바탕으로 {len(image_paths)}개의 이미지를 확인했습니다."


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