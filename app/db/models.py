from sqlalchemy import (
    Column, Integer, String, Text, Boolean, 
    TIMESTAMP, DECIMAL, JSON, Enum as SQLEnum,
    Index, func
)
from sqlalchemy.sql import func
from enum import Enum
from app.db.base import Base


class OperationType(str, Enum):
    SEARCH_USER = "search_user"
    FOLLOWING = "following"
    FOLLOWERS = "followers"
    TIMELINE = "timeline"


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"


class TwitterCredentials(Base):
    __tablename__ = "twitter_credentials"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    credential_name = Column(String(100), nullable=False, unique=True)
    username = Column(String(255), nullable=False)
    encrypted_password = Column(Text, nullable=False)
    salt = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True, nullable=False)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    updated_at = Column(
        TIMESTAMP, 
        default=func.now(), 
        onupdate=func.now(), 
        nullable=False
    )
    last_login_attempt = Column(TIMESTAMP, nullable=True)
    login_success_count = Column(Integer, default=0, nullable=False)
    login_failure_count = Column(Integer, default=0, nullable=False)
    
    __table_args__ = (
        Index('idx_credential_name', 'credential_name'),
        Index('idx_is_active', 'is_active'),
    )


class ScrapingLogs(Base):
    __tablename__ = "scraping_logs"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(255), nullable=False, unique=True)
    operation_type = Column(
        SQLEnum(OperationType), 
        nullable=False
    )
    parameters = Column(JSON, nullable=False)
    status = Column(
        SQLEnum(TaskStatus), 
        default=TaskStatus.PENDING, 
        nullable=False
    )
    result_size = Column(Integer, nullable=True)
    execution_time_seconds = Column(DECIMAL(10, 3), nullable=True)
    error_message = Column(Text, nullable=True)
    created_at = Column(TIMESTAMP, default=func.now(), nullable=False)
    completed_at = Column(TIMESTAMP, nullable=True)
    
    __table_args__ = (
        Index('idx_task_id', 'task_id'),
        Index('idx_operation_type', 'operation_type'),
        Index('idx_status', 'status'),
        Index('idx_created_at', 'created_at'),
    )
