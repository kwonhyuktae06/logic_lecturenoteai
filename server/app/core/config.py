from pydantic_settings import BaseSettings
from pathlib import Path

class Settings(BaseSettings):
    APP_NAME: str = "LectureNoteAI"
    DEBUG: bool = False

    DB_HOST: str = "localhost"
    DB_PORT: int = 3306
    DB_USER: str = "root"
    DB_PASSWORD: str = ""
    DB_NAME: str = "lecture_pipeline_db"

    @property
    def DATABASE_URL(self) -> str:
        return (
            f"mysql+pymysql://{self.DB_USER}:{self.DB_PASSWORD}"
            f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
        )

    UPLOAD_DIR: str = "uploads"

    @property
    def UPLOAD_PATH(self) -> Path:
        path = Path(self.UPLOAD_DIR)
        path.mkdir(parents=True, exist_ok=True)
        return path

    MAX_FILE_SIZE: int = 500 * 1024 * 1024
    ALLOWED_EXTENSIONS: list = [".mp4", ".mp3", ".wav", ".pdf", ".pptx", ".txt", ".jpg", ".jpeg", ".png"]

    WHISPER_MODEL_NAME: str = "openai/whisper-base"
    QWEN_MODEL_NAME: str = "Qwen/Qwen2.5-VL-3B-Instruct"

    class Config:
        env_file = ".env"

settings = Settings()