from fastapi import HTTPException, status
from typing import Any, Dict, List, Optional


class APIException(HTTPException):
    """Base API exception class."""
    
    def __init__(
        self,
        status_code: int,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        self.message = message
        self.code = code
        self.details = details or {}
        super().__init__(status_code=status_code, detail=message)


class ValidationException(Exception):
    """Exception for validation errors."""
    
    def __init__(self, errors: List[Dict[str, str]]):
        self.errors = errors
        super().__init__("Validation failed")


class AuthenticationException(APIException):
    """Exception for authentication errors."""
    
    def __init__(self, message: str = "Authentication failed"):
        super().__init__(
            status_code=401,
            message=message,
            code="AUTHENTICATION_ERROR"
        )


class NotFoundException(APIException):
    """Exception for not found errors."""
    
    def __init__(self, resource: str, identifier: str):
        super().__init__(
            status_code=404,
            message=f"{resource} '{identifier}' not found",
            code="NOT_FOUND"
        )


class ConflictException(APIException):
    """Exception for conflict errors."""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=409,
            message=message,
            code="CONFLICT"
        )


class ScrapingException(APIException):
    """Exception for scraping-related errors."""
    
    def __init__(self, message: str):
        super().__init__(
            status_code=500,
            message=f"Scraping failed: {message}",
            code="SCRAPING_ERROR"
        )


class UnauthorizedError(APIException):
    """Exception for unauthorized access."""
    
    def __init__(self, detail: str = "Invalid or missing API key"):
        super().__init__(
            status_code=status.HTTP_401_UNAUTHORIZED,
            message=detail,
            code="UNAUTHORIZED"
        )


class RateLimitError(APIException):
    """Exception for rate limit errors."""
    
    def __init__(self, detail: str = "Rate limit exceeded", retry_after: int = 60):
        super().__init__(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            message=detail,
            code="RATE_LIMIT_EXCEEDED"
        )
        self.retry_after = retry_after


class InternalServerError(APIException):
    """Exception for internal server errors."""
    
    def __init__(self, detail: str = "Internal server error", request_id: str = None):
        super().__init__(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            message=detail,
            code="INTERNAL_ERROR"
        )
        self.request_id = request_id


class TaskNotFoundError(NotFoundException):
    """Exception for task not found errors."""
    
    def __init__(self, task_id: str):
        super().__init__(resource="Task", identifier=task_id)


class CredentialNotFoundError(NotFoundException):
    """Exception for credential not found errors."""
    
    def __init__(self, credential_name: str):
        super().__init__(resource="Credential", identifier=credential_name)


# Backward compatibility aliases
ScraperAPIException = APIException
ValidationError = ValidationException
NotFoundError = NotFoundException
