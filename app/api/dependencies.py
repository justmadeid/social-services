from fastapi import HTTPException, Security, status
from fastapi.security import APIKeyHeader
from app.core.config import settings

# API Key authentication (DISABLED)
# api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)


async def get_api_key():
    """API key validation disabled - open access for now."""
    # API key authentication is disabled
    # Enable this function when authentication is needed
    return "no-auth"


# Rate limiting would be implemented here in production
# For now, we'll create a placeholder dependency
async def rate_limit():
    """Rate limiting dependency (placeholder for production implementation)."""
    # In production, implement actual rate limiting using Redis
    # with sliding window or token bucket algorithm
    pass
