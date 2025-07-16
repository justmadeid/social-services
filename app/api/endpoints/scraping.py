from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import time
import asyncio
from celery.result import AsyncResult

from app.api.dependencies import rate_limit
from app.schemas.task import TaskResponse
from app.schemas.common import StandardResponse
from app.schemas.twitter import SearchUsersRequest
from app.worker.tasks import search_users_task, get_following_task, get_followers_task, get_timeline_task
from app.worker.celery_app import celery_app
from app.core.config import settings

router = APIRouter()


async def get_task_status_with_retry(task_id: str, max_retries: int = 3, delay: float = 0.1):
    """Get task status with retry to catch status changes."""
    for attempt in range(max_retries):
        task_result = AsyncResult(task_id, app=celery_app)
        if task_result.status != "PENDING":
            return task_result.status
        if attempt < max_retries - 1:
            await asyncio.sleep(delay)
    return "PENDING"


@router.post(
    "/search/users",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Search Twitter users",
    description="Search for Twitter users based on query string"
)
async def search_users(
    search_request: SearchUsersRequest,
    _: None = Depends(rate_limit)
):
    """Search for Twitter users."""
    try:
        # Queue search task
        task = search_users_task.delay(search_request.name, search_request.limit)
        
        # Wait briefly and check for status change
        task_status = await get_task_status_with_retry(task.id)
        
        return StandardResponse(
            status="accepted",
            message="User search task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status=task_status,
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={"query": search_request.name, "limit": search_request.limit}
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue search task: {str(e)}"
        )


@router.get(
    "/users/{username}/following",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Get user following list",
    description="Get list of users that the specified user follows"
)
async def get_user_following(
    username: str,
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results to return"),
    _: None = Depends(rate_limit)
):
    """Get user's following list."""
    try:
        # Queue following task
        task = get_following_task.delay(username, limit)
        
        return StandardResponse(
            status="accepted",
            message="Following list task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status=task.status,
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={"username": username, "limit": limit}
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue following task: {str(e)}"
        )


@router.get(
    "/users/{username}/followers",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Get user followers list",
    description="Get list of users that follow the specified user"
)
async def get_user_followers(
    username: str,
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results to return"),
    _: None = Depends(rate_limit)
):
    """Get user's followers list."""
    try:
        # Queue followers task
        task = get_followers_task.delay(username, limit)
        
        return StandardResponse(
            status="accepted",
            message="Followers list task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status=task.status,
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={"username": username, "limit": limit}
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue followers task: {str(e)}"
        )


@router.get(
    "/users/{username}/timeline",
    response_model=StandardResponse[TaskResponse],
    status_code=status.HTTP_202_ACCEPTED,
    summary="Get user timeline analysis",
    description="Get user's timeline with tweets, hashtag analysis, and mention analysis"
)
async def get_user_timeline(
    username: str,
    count: Optional[int] = Query(
        settings.default_tweet_count,
        ge=settings.min_tweet_count,
        le=settings.max_tweet_count,
        description="Number of tweets to analyze"
    ),
    include_analysis: Optional[bool] = Query(True, description="Include hashtag and mention analysis"),
    _: None = Depends(rate_limit)
):
    """Get user's timeline with analysis."""
    try:
        # Queue timeline task
        task = get_timeline_task.delay(username, count, include_analysis)
        
        return StandardResponse(
            status="accepted",
            message="Timeline analysis task queued successfully",
            data=TaskResponse(
                task_id=task.id,
                status=task.status,
                status_url=f"/api/v1/tasks/{task.id}",
                parameters={
                    "username": username,
                    "count": count,
                    "include_analysis": include_analysis
                }
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to queue timeline task: {str(e)}"
        )
