from fastapi import APIRouter, Depends, HTTPException, status
from celery.result import AsyncResult

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
