from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from celery import Celery
from celery.result import AsyncResult
import time
import json
import os
import sys
import psutil
import asyncio
from datetime import datetime
from typing import Dict, Any, List

from app.api.dependencies import rate_limit
from app.db.session import get_async_session, engine
from app.schemas.health import (
    HealthCheckResponse, 
    ServiceHealthCheck, 
    HealthStatus,
    CeleryHealthDetails,
    CeleryWorkerInfo,
    DatabaseHealthDetails,
    RedisHealthDetails,
    TwitterScraperHealthDetails,
    SystemHealthDetails
)
from app.schemas.common import StandardResponse
from app.core.config import settings
from app.scraper.cache_manager import cache_manager
from app.scraper.twitter_scraper import twitter_scraper
from app.worker.celery_app import celery_app

router = APIRouter()


async def check_database_health() -> ServiceHealthCheck:
    """Check database connectivity and health"""
    start_time = time.time()
    
    try:
        async with AsyncSession(engine) as session:
            # Test basic connectivity
            result = await session.execute(text("SELECT 1"))
            result.scalar()
            
            # Get database info
            db_info = await session.execute(text("SELECT VERSION()"))
            db_version = db_info.scalar()
            
            # Get connection pool info
            pool_size = engine.pool.size()
            checked_out = engine.pool.checkedout()
            
            details = DatabaseHealthDetails(
                connected=True,
                connection_pool_size=pool_size,
                active_connections=checked_out,
                database_name=settings.database_url.split('/')[-1],
                version=db_version
            )
            
            response_time = (time.time() - start_time) * 1000
            
            return ServiceHealthCheck(
                service_name="database",
                status=HealthStatus.HEALTHY,
                message="Database is accessible and responding",
                response_time_ms=response_time,
                last_check=datetime.now(),
                details=details.dict()
            )
            
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealthCheck(
            service_name="database",
            status=HealthStatus.UNHEALTHY,
            message=f"Database check failed: {str(e)}",
            response_time_ms=response_time,
            last_check=datetime.now(),
            details={"error": str(e)}
        )


async def check_redis_health() -> ServiceHealthCheck:
    """Check Redis connectivity and health"""
    start_time = time.time()
    
    try:
        # Test basic connectivity
        ping_start = time.time()
        is_healthy = cache_manager.health_check()
        ping_time = (time.time() - ping_start) * 1000
        
        if not is_healthy:
            raise Exception("Redis ping failed")
        
        # Get Redis info
        redis_info = cache_manager.redis_client.info()
        
        # Calculate cache hit ratio
        hits = redis_info.get('keyspace_hits', 0)
        misses = redis_info.get('keyspace_misses', 0)
        total = hits + misses
        hit_ratio = (hits / total * 100) if total > 0 else 0
        
        details = RedisHealthDetails(
            connected=True,
            ping_time_ms=ping_time,
            memory_usage_mb=redis_info.get('used_memory', 0) / 1024 / 1024,
            connected_clients=redis_info.get('connected_clients', 0),
            total_commands_processed=redis_info.get('total_commands_processed', 0),
            keyspace_hits=hits,
            keyspace_misses=misses,
            cache_hit_ratio=hit_ratio
        )
        
        response_time = (time.time() - start_time) * 1000
        
        return ServiceHealthCheck(
            service_name="redis",
            status=HealthStatus.HEALTHY,
            message="Redis is accessible and responding",
            response_time_ms=response_time,
            last_check=datetime.now(),
            details=details.dict()
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealthCheck(
            service_name="redis",
            status=HealthStatus.UNHEALTHY,
            message=f"Redis check failed: {str(e)}",
            response_time_ms=response_time,
            last_check=datetime.now(),
            details={"error": str(e)}
        )


async def check_celery_health() -> ServiceHealthCheck:
    """Check Celery workers and queue health"""
    start_time = time.time()
    
    try:
        # Get worker stats
        inspect = celery_app.control.inspect()
        
        # Check active workers
        active_workers = inspect.active()
        stats = inspect.stats()
        
        workers_info = []
        total_workers = 0
        total_active_tasks = 0
        total_processed_tasks = 0
        
        if active_workers:
            for worker_name, tasks in active_workers.items():
                total_workers += 1
                total_active_tasks += len(tasks)
                
                worker_stats = stats.get(worker_name, {}) if stats else {}
                
                workers_info.append(CeleryWorkerInfo(
                    worker_name=worker_name,
                    status="active",
                    active_tasks=len(tasks),
                    processed_tasks=worker_stats.get('total', {}).get('app.worker.tasks.login_task', 0),
                    pool_size=worker_stats.get('pool', {}).get('max-concurrency', 0),
                    pool_processes=worker_stats.get('pool', {}).get('processes', [])
                ))
        
        # Check broker connectivity by trying to get queue info
        try:
            reserved_tasks = inspect.reserved()
            broker_connected = reserved_tasks is not None
        except:
            broker_connected = False
        
        # Try to get some queue stats
        try:
            # This is a simple test to check if result backend is working
            test_result = AsyncResult('test-health-check', app=celery_app)
            result_backend_connected = True
        except:
            result_backend_connected = False
        
        details = CeleryHealthDetails(
            broker_connected=broker_connected,
            result_backend_connected=result_backend_connected,
            active_workers=workers_info,
            total_workers=total_workers,
            pending_tasks=0,  # This would require more complex queue inspection
            active_tasks=total_active_tasks,
            processed_tasks=total_processed_tasks,
            failed_tasks=0  # This would require access to result backend stats
        )
        
        response_time = (time.time() - start_time) * 1000
        
        # Determine health status
        if total_workers == 0:
            health_status = HealthStatus.UNHEALTHY
            message = "No active Celery workers found"
        elif not broker_connected:
            health_status = HealthStatus.DEGRADED
            message = "Celery broker connection issues"
        else:
            health_status = HealthStatus.HEALTHY
            message = f"{total_workers} active workers, {total_active_tasks} active tasks"
        
        return ServiceHealthCheck(
            service_name="celery",
            status=health_status,
            message=message,
            response_time_ms=response_time,
            last_check=datetime.now(),
            details=details.dict()
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealthCheck(
            service_name="celery",
            status=HealthStatus.UNHEALTHY,
            message=f"Celery check failed: {str(e)}",
            response_time_ms=response_time,
            last_check=datetime.now(),
            details={"error": str(e)}
        )


async def check_twitter_scraper_health() -> ServiceHealthCheck:
    """Check Twitter scraper login state and health"""
    start_time = time.time()
    
    try:
        # Check login status
        login_status = twitter_scraper.check_login_status()
        
        details = TwitterScraperHealthDetails(
            state_file_exists=login_status.get("state_file_exists", False),
            state_file_path=login_status.get("state_file_path", ""),
            state_file_size=login_status.get("state_file_size", 0),
            cookies_count=login_status.get("cookies_count", 0),
            login_required=login_status.get("login_required", True),
            has_credentials=login_status.get("has_credentials", False),
            last_login_check=datetime.now(),
            error=login_status.get("error")
        )
        
        response_time = (time.time() - start_time) * 1000
        
        # Determine health status
        if login_status.get("error"):
            health_status = HealthStatus.UNHEALTHY
            message = f"Twitter scraper error: {login_status.get('error')}"
        elif login_status.get("login_required"):
            health_status = HealthStatus.DEGRADED
            message = "Twitter login required - scraper needs authentication"
        else:
            health_status = HealthStatus.HEALTHY
            message = "Twitter scraper is authenticated and ready"
        
        return ServiceHealthCheck(
            service_name="twitter_scraper",
            status=health_status,
            message=message,
            response_time_ms=response_time,
            last_check=datetime.now(),
            details=details.dict()
        )
        
    except Exception as e:
        response_time = (time.time() - start_time) * 1000
        return ServiceHealthCheck(
            service_name="twitter_scraper",
            status=HealthStatus.UNHEALTHY,
            message=f"Twitter scraper check failed: {str(e)}",
            response_time_ms=response_time,
            last_check=datetime.now(),
            details={"error": str(e)}
        )


def get_system_health() -> SystemHealthDetails:
    """Get system health information"""
    try:
        # Get system info
        memory = psutil.virtual_memory()
        cpu_percent = psutil.cpu_percent(interval=1)
        disk = psutil.disk_usage('/')
        
        # Get process info
        process = psutil.Process()
        uptime = time.time() - process.create_time()
        
        return SystemHealthDetails(
            uptime_seconds=uptime,
            memory_usage_mb=memory.used / 1024 / 1024,
            cpu_usage_percent=cpu_percent,
            disk_usage_percent=disk.percent,
            python_version=sys.version,
            application_version=settings.project_version
        )
        
    except Exception as e:
        return SystemHealthDetails(
            uptime_seconds=0,
            memory_usage_mb=0,
            cpu_usage_percent=0,
            disk_usage_percent=0,
            python_version=sys.version,
            application_version=settings.project_version
        )


@router.get(
    "",
    response_model=StandardResponse[HealthCheckResponse],
    summary="Comprehensive health check",
    description="Check the health of all system components including database, Redis, Celery workers, and Twitter scraper"
)
async def health_check(
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Comprehensive health check endpoint"""
    overall_start_time = time.time()
    
    try:
        # Run all health checks concurrently
        health_checks = await asyncio.gather(
            check_database_health(),
            check_redis_health(),
            check_celery_health(),
            check_twitter_scraper_health(),
            return_exceptions=True
        )
        
        # Filter out any exceptions and convert to ServiceHealthCheck objects
        services = []
        for check in health_checks:
            if isinstance(check, ServiceHealthCheck):
                services.append(check)
            else:
                # Handle exception case
                services.append(ServiceHealthCheck(
                    service_name="unknown",
                    status=HealthStatus.UNHEALTHY,
                    message=f"Health check failed: {str(check)}",
                    response_time_ms=0,
                    last_check=datetime.now(),
                    details={"error": str(check)}
                ))
        
        # Get system health
        system_health = get_system_health()
        
        # Determine overall health status
        unhealthy_services = [s for s in services if s.status == HealthStatus.UNHEALTHY]
        degraded_services = [s for s in services if s.status == HealthStatus.DEGRADED]
        
        if unhealthy_services:
            overall_status = HealthStatus.UNHEALTHY
            overall_message = f"{len(unhealthy_services)} services are unhealthy"
        elif degraded_services:
            overall_status = HealthStatus.DEGRADED
            overall_message = f"{len(degraded_services)} services are degraded"
        else:
            overall_status = HealthStatus.HEALTHY
            overall_message = "All services are healthy"
        
        total_response_time = (time.time() - overall_start_time) * 1000
          # Build additional details
        details = {
            "total_services_checked": len(services),
            "healthy_services": len([s for s in services if s.status == HealthStatus.HEALTHY]),
            "degraded_services": len(degraded_services),
            "unhealthy_services": len(unhealthy_services),
            "environment": settings.environment,
            "debug_mode": settings.environment == "development",
            "api_version": settings.api_v1_str
        }
        
        health_response = HealthCheckResponse(
            status=overall_status,
            timestamp=datetime.now(),
            overall_health=overall_message,
            services=services,
            system=system_health,
            details=details,
            response_time_ms=total_response_time
        )
        
        return StandardResponse(
            status="success",
            message="Health check completed",
            data=health_response
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Health check failed: {str(e)}"
        )
