from fastapi import APIRouter, Depends, HTTPException, status, Query, Request
from celery.result import AsyncResult
from typing import Optional, List, Dict, Any
import json

from app.api.dependencies import rate_limit
from app.schemas.task import TaskStatusResponse
from app.schemas.common import StandardResponse
from app.worker.celery_app import celery_app

router = APIRouter()


@router.get(
    "/{task_id}",
    response_model=StandardResponse[TaskStatusResponse],
    summary="Get task status",
    description="Check the status of any background task and retrieve results"
)
async def get_task_status(
    task_id: str,
    _: None = Depends(rate_limit)
):
    """Get task status and results."""
    try:
        # Get task result from Celery
        task_result = AsyncResult(task_id, app=celery_app)
        
        if not task_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found"
            )
        
        # Prepare response based on task state
        task_data = TaskStatusResponse(
            task_id=task_id,
            status=task_result.state
        )
        
        if task_result.state == "PENDING":
            task_data.message = "Task is queued for processing"
            # In production, you might want to get creation time from Redis
            
        elif task_result.state == "PROCESSING":
            task_data.message = "Task is currently being processed"
            # Get progress info if available
            if task_result.info and isinstance(task_result.info, dict):
                task_data.progress = task_result.info.get('progress', 0)
                task_data.message = task_result.info.get('message', task_data.message)
                
        elif task_result.state == "SUCCESS":
            task_data.message = "Task completed successfully"
            task_data.result = task_result.result
            # Get execution time if available
            if task_result.info and isinstance(task_result.info, dict):
                task_data.execution_time = task_result.info.get('execution_time')
                
        elif task_result.state == "FAILURE":
            task_data.message = "Task failed to complete"
            # Handle exception info properly
            if task_result.info:
                if isinstance(task_result.info, Exception):
                    task_data.error = f"{type(task_result.info).__name__}: {str(task_result.info)}"
                elif isinstance(task_result.info, dict):
                    task_data.error = task_result.info.get('error', str(task_result.info))
                else:
                    task_data.error = str(task_result.info)
            else:
                task_data.error = "Unknown error"
            
        elif task_result.state == "RETRY":
            task_data.message = "Task is being retried"
            if task_result.info and isinstance(task_result.info, dict):
                task_data.retry_count = task_result.info.get('retry_count', 0)
                
        elif task_result.state == "REVOKED":
            task_data.message = "Task was cancelled"
            
        else:
            task_data.message = f"Task status: {task_result.state}"
        
        return StandardResponse(
            status="success",
            data=task_data
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to retrieve task status: {str(e)}"
        )


@router.delete(
    "/{task_id}",
    response_model=StandardResponse[dict],
    summary="Cancel task",
    description="Cancel a pending or running task"
)
async def cancel_task(
    task_id: str,
    _: None = Depends(rate_limit)
):
    """Cancel a task."""
    try:
        task_result = AsyncResult(task_id, app=celery_app)
        
        if not task_result:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Task '{task_id}' not found"
            )
        
        if task_result.state in ["SUCCESS", "FAILURE", "REVOKED"]:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot cancel task in state: {task_result.state}"
            )
        
        # Revoke the task
        celery_app.control.revoke(task_id, terminate=True)
        
        return StandardResponse(
            status="success",
            message=f"Task '{task_id}' cancelled successfully",
            data={"task_id": task_id, "action": "cancelled"}
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to cancel task: {str(e)}"
        )


@router.get(
    "/",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Get tasks overview",
    description="Get overview of all tasks including active, scheduled, and completed tasks"
)
async def get_tasks_overview(
    _: None = Depends(rate_limit)
):
    """Get overview of all tasks."""
    try:
        # Get Celery inspect instance
        inspect = celery_app.control.inspect()
        
        # Get active tasks
        active_tasks = inspect.active()
        scheduled_tasks = inspect.scheduled()
        registered_tasks = inspect.registered()
        stats = inspect.stats()
        
        # Process active tasks
        active_list = []
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    active_list.append({
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "worker": worker,
                        "args": task.get("args", []),
                        "kwargs": task.get("kwargs", {}),
                        "time_start": task.get("time_start"),
                        "delivery_info": task.get("delivery_info", {})
                    })
        
        # Process scheduled tasks
        scheduled_list = []
        if scheduled_tasks:
            for worker, tasks in scheduled_tasks.items():
                for task in tasks:
                    scheduled_list.append({
                        "task_id": task.get("id"),
                        "name": task.get("name"),
                        "worker": worker,
                        "eta": task.get("eta"),
                        "priority": task.get("priority")
                    })
        
        # Get worker stats
        worker_stats = {}
        if stats:
            for worker, stat in stats.items():
                worker_stats[worker] = {
                    "pool": stat.get("pool", {}),
                    "total": stat.get("total", {}),
                    "rusage": stat.get("rusage", {}),
                    "clock": stat.get("clock")
                }
        
        overview = {
            "active_tasks": active_list,
            "scheduled_tasks": scheduled_list,
            "registered_tasks": list(registered_tasks.values())[0] if registered_tasks else [],
            "worker_stats": worker_stats,
            "summary": {
                "active_count": len(active_list),
                "scheduled_count": len(scheduled_list),
                "workers_count": len(worker_stats)
            }
        }
        
        return StandardResponse(
            status="success",
            message="Tasks overview retrieved successfully",
            data=overview
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get tasks overview: {str(e)}"
        )


@router.get(
    "/active",
    response_model=StandardResponse[List[Dict[str, Any]]],
    summary="Get active tasks",
    description="Get list of currently running tasks"
)
async def get_active_tasks(
    _: None = Depends(rate_limit)
):
    """Get currently active/running tasks."""
    try:
        inspect = celery_app.control.inspect()
        active_tasks = inspect.active()
        
        tasks_list = []
        if active_tasks:
            for worker, tasks in active_tasks.items():
                for task in tasks:
                    task_id = task.get("id")
                    
                    # Get additional task details from AsyncResult
                    task_result = AsyncResult(task_id, app=celery_app)
                    
                    task_info = {
                        "task_id": task_id,
                        "name": task.get("name"),
                        "worker": worker,
                        "status": task_result.state,
                        "args": task.get("args", []),
                        "kwargs": task.get("kwargs", {}),
                        "time_start": task.get("time_start"),
                        "progress": 0,
                        "message": "Processing...",
                        "delivery_info": task.get("delivery_info", {})
                    }
                    
                    # Get progress info if available
                    if task_result.info and isinstance(task_result.info, dict):
                        task_info["progress"] = task_result.info.get("progress", 0)
                        task_info["message"] = task_result.info.get("message", "Processing...")
                    
                    tasks_list.append(task_info)
        
        return StandardResponse(
            status="success",
            message=f"Found {len(tasks_list)} active tasks",
            data=tasks_list
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get active tasks: {str(e)}"
        )


@router.get(
    "/history",
    response_model=StandardResponse[List[Dict[str, Any]]],
    summary="Get task history",
    description="Get recent task history (requires result backend with persistence)"
)
async def get_task_history(
    limit: Optional[int] = Query(50, ge=1, le=200, description="Number of recent tasks to retrieve"),
    _: None = Depends(rate_limit)
):
    """Get recent task history."""
    try:
        # Note: This is a basic implementation. For full task history,
        # you would need to implement task result persistence in your result backend
        # or use a tool like Flower
        
        # This endpoint primarily shows the structure for task history
        # In a production environment, you might want to:
        # 1. Store task metadata in a database
        # 2. Use Celery's result backend with persistence
        # 3. Use monitoring tools like Flower
        
        return StandardResponse(
            status="success",
            message="Task history endpoint - requires result backend persistence",
            data=[
                {
                    "note": "Task history requires result backend persistence",
                    "recommendation": "Use Celery Flower for comprehensive task monitoring",
                    "flower_url": "http://localhost:5555",
                    "implementation": "For custom history, store task metadata in database"
                }
            ]
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get task history: {str(e)}"
        )


@router.get(
    "/debug/cors",
    response_model=StandardResponse[Dict[str, Any]],
    summary="Debug CORS configuration",
    description="Debug endpoint to test CORS configuration"
)
async def debug_cors(request: Request):
    """Debug CORS configuration."""
    return StandardResponse(
        status="success",
        message="CORS debug successful",
        data={
            "request_headers": dict(request.headers),
            "origin": request.headers.get("origin"),
            "user_agent": request.headers.get("user-agent"),
            "method": request.method,
            "url": str(request.url),
            "cors_configured": True
        }
    )
