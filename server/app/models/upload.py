from sqlalchemy import Column, String, DateTime, Text, BigInteger
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.dialects.mysql import CHAR
from datetime import datetime
import uuid

Base = declarative_base()


class Upload(Base):
    __tablename__ = "uploads"

    id = Column(CHAR(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    type = Column(String(10), nullable=False)
    source = Column(Text, nullable=False)
    file_path = Column(Text, nullable=True)
    file_size = Column(BigInteger, nullable=True)
    status = Column(String(20), nullable=False, default="pending")
    error_message = Column(Text, nullable=True)
    transcript = Column(Text, nullable=True)
    analysis = Column(Text, nullable=True)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    def __repr__(self):
        return f"<Upload id={self.id} type={self.type} status={self.status}>"