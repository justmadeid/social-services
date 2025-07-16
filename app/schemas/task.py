from pydantic import BaseModel
from typing import Optional, Any, Dict
from datetime import datetime
from enum import Enum


class TaskStatus(str, Enum):
    PENDING = "PENDING"
    PROCESSING = "PROCESSING"
    SUCCESS = "SUCCESS"
    FAILURE = "FAILURE"
    RETRY = "RETRY"
    REVOKED = "REVOKED"


class TaskResponse(BaseModel):
    task_id: str
    status: str
    status_url: Optional[str] = None
    parameters: Optional[Dict[str, Any]] = None


class TaskStatusResponse(BaseModel):
    task_id: str
    status: str
    message: Optional[str] = None
    result: Optional[Any] = None
    error: Optional[str] = None
    progress: Optional[int] = None
    execution_time: Optional[float] = None
    created_at: Optional[datetime] = None
    started_at: Optional[datetime] = None
    completed_at: Optional[datetime] = None
    failed_at: Optional[datetime] = None
    estimated_completion: Optional[datetime] = None
    retry_count: Optional[int] = None


class TaskMetadata(BaseModel):
    execution_time: Optional[float] = None
    cached: bool = False
    query: Optional[str] = None
    username: Optional[str] = None
    result_count: Optional[int] = None
    total_tweets: Optional[int] = None
    analysis_period: Optional[datetime] = None
    result_count: Optional[int] = None
