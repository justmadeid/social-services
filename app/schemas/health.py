from pydantic import BaseModel
from typing import Dict, Any, Optional, List
from datetime import datetime
from enum import Enum


class HealthStatus(str, Enum):
    """Health status enum"""
    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


class ServiceHealthCheck(BaseModel):
    """Individual service health check result"""
    service_name: str
    status: HealthStatus
    message: Optional[str] = None
    response_time_ms: Optional[float] = None
    last_check: datetime
    details: Optional[Dict[str, Any]] = None


class CeleryWorkerInfo(BaseModel):
    """Celery worker information"""
    worker_name: str
    status: str
    active_tasks: int
    processed_tasks: int
    pool_size: int
    pool_processes: List[int]  # Changed from List[str] to List[int]


class CeleryHealthDetails(BaseModel):
    """Celery health check details"""
    broker_connected: bool
    result_backend_connected: bool
    active_workers: List[CeleryWorkerInfo]
    total_workers: int
    pending_tasks: int
    active_tasks: int
    processed_tasks: int
    failed_tasks: int


class DatabaseHealthDetails(BaseModel):
    """Database health check details"""
    connected: bool
    connection_pool_size: int
    active_connections: int
    database_name: str
    version: Optional[str] = None


class RedisHealthDetails(BaseModel):
    """Redis health check details"""
    connected: bool
    ping_time_ms: float
    memory_usage_mb: float
    connected_clients: int
    total_commands_processed: int
    keyspace_hits: int
    keyspace_misses: int
    cache_hit_ratio: float


class TwitterScraperHealthDetails(BaseModel):
    """Twitter scraper health check details"""
    state_file_exists: bool
    state_file_path: str
    state_file_size: int
    cookies_count: int
    login_required: bool
    has_credentials: bool
    last_login_check: Optional[datetime] = None
    error: Optional[str] = None


class SystemHealthDetails(BaseModel):
    """System health check details"""
    uptime_seconds: float
    memory_usage_mb: float
    cpu_usage_percent: float
    disk_usage_percent: float
    python_version: str
    application_version: str


class HealthCheckResponse(BaseModel):
    """Comprehensive health check response"""
    status: HealthStatus
    timestamp: datetime
    overall_health: str
    services: List[ServiceHealthCheck]
    system: SystemHealthDetails
    details: Dict[str, Any]
    response_time_ms: float
