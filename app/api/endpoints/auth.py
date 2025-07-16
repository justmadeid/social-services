from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession

from app.api.dependencies import rate_limit
from app.crud.crud_settings import settings_crud
from app.db.session import get_async_session
from app.schemas.task import TaskResponse
from app.schemas.common import StandardResponse
from app.worker.tasks import login_task
from app.schemas.settings import LoginRequest

router = APIRouter()


@router.post(
    "",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Login to Twitter",
    description="Trigger Twitter login process as background task"
)
async def login(
    login_request: LoginRequest,
    db: AsyncSession = Depends(get_async_session),
    _: None = Depends(rate_limit)
):
    """Trigger Twitter login as background task."""
    try:
        # Verify credentials exist
        credentials = await settings_crud.get_by_name(db, credential_name=login_request.credential_name)
        if not credentials:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Credential '{login_request.credential_name}' not found"
            )
        
        if not credentials.is_active:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Credential '{login_request.credential_name}' is not active"
            )
        
        # Queue login task
        task = login_task.delay(login_request.credential_name)
        
        return StandardResponse(
            status="accepted",
            message="Login task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status="PENDING",
                status_url=f"/api/v1/tasks/{task.id}"
            )
        )
        
    except HTTPException:
        raise
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue login task: {str(e)}"
        )


@router.post(
    "/test",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Test Task",
    description="Trigger a simple test task to verify task processing"
)
async def test_task(
    message: str = "Hello from API!",
    _: None = Depends(rate_limit)
):
    """Trigger a simple test task."""
    try:
        from app.worker.tasks import test_task as test_task_func
        
        # Queue test task
        task = test_task_func.delay(message)
        
        return StandardResponse(
            status="accepted",
            message="Test task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status="PENDING",
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={"message": message}
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue test task: {str(e)}"
        )


@router.post(
    "/test-failure",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Test Failure Task",
    description="Trigger a task that will fail to test error handling"
)
async def test_failure_task(
    message: str = "This task will fail",
    _: None = Depends(rate_limit)
):
    """Trigger a test task that will fail."""
    try:
        from app.worker.tasks import test_failure_task as test_failure_task_func
        
        # Queue failure test task
        task = test_failure_task_func.delay(message)
        
        return StandardResponse(
            status="accepted",
            message="Test failure task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status="PENDING",
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={"message": message}
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue test failure task: {str(e)}"
        )
