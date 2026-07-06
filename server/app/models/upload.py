from sqlalchemy import Column, String, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime
import uuid

Base = declarative_base()


class Upload(Base):
    __tablename__ = "uploads"

    # 고유 ID (UUID)
    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))

    # 업로드 타입 ("file" or "url")
    type = Column(String(10), nullable=False)

    # 파일명 or URL
    source = Column(Text, nullable=False)

    # 파일 업로드일 때만 값이 있음, URL 업로드는 None
    file_path = Column(Text, nullable=True)

    # 파일 크기 (bytes)
    file_size = Column(BigInteger, nullable=True)

    # 처리 상태: pending(대기) → processing(처리중) → done(완료) | failed(실패)
    status = Column(String(20), nullable=False, default="pending")

    # 실패 시 에러 메시지
    error_message = Column(Text, nullable=True)

    # 시간
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Upload id={self.id} type={self.type} status={self.status}>"