from pydantic import BaseModel
from typing import Any, Dict, List, Optional, Generic, TypeVar
from datetime import datetime

T = TypeVar('T')


class BaseResponse(BaseModel):
    status: str
    message: Optional[str] = None


class ErrorResponse(BaseResponse):
    status: str = "error"
    code: Optional[str] = None
    errors: Optional[List[Dict[str, Any]]] = None


class SuccessResponse(BaseResponse):
    status: str = "success"
    data: Optional[Any] = None


class StandardResponse(BaseModel, Generic[T]):
    status: str
    message: Optional[str] = None
    data: Optional[T] = None


class ValidationError(BaseModel):
    field: str
    message: str


class AcceptedResponse(BaseResponse):
    status: str = "accepted"
    task_id: str
    status_url: str
    parameters: Optional[Dict[str, Any]] = None


class MetadataResponse(BaseModel):
    execution_time: Optional[float] = None
    cached: bool = False
    result_count: Optional[int] = None
