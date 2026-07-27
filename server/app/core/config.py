from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    # 앱 기본 설정
    APP_NAME: str = "LectureNoteAI"
    DEBUG: bool = False

    # DB 설정
    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "lecturenoteai"

    @property
    def DATABASE_URL(self) -> str:
        return "sqlite:///./lecturenoteai.db"

    # 파일 저장 경로 (나중에 S3로 교체할 부분)
    UPLOAD_DIR: str = "uploads"

    @property
    def UPLOAD_PATH(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)  # 폴더 없으면 자동 생성
        return path

    # 파일 제한 # 500MB
    MAX_FILE_SIZE: int = 500 * 1024 * 1024
    ALLOWED_EXTENSIONS: list = [".mp4", ".mp3", ".wav", ".pdf", ".pptx", ".txt", ".jpg", ".jpeg", ".png"]

    # AI 모델 설정
    WHISPER_MODEL_NAME: str = "openai/whisper-base"
    QWEN_MODEL_NAME: str = "Qwen/Qwen2.5-VL-3B-Instruct"

    class Config:
        env_file = ".env"

settings = Settings()