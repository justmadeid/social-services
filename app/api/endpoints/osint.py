from fastapi import APIRouter, Depends, HTTPException, status, Query
from typing import Optional
import asyncio
import concurrent.futures

from app.api.dependencies import rate_limit
from app.schemas.common import StandardResponse
from app.schemas.twitter import (
    UserSearchResult, 
    FollowingResult, 
    TimelineResult
)
from app.scraper.twitter_scraper import TwitterScraper
from app.core.config import settings

router = APIRouter()


def run_scraping_in_thread(func, *args, **kwargs):
    """Run a scraping function in a separate thread to avoid Playwright async context issues."""
    def run_sync():
        scraper = TwitterScraper(headless=True)
        return getattr(scraper, func)(*args, **kwargs)
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        future = executor.submit(run_sync)
        return future.result()


@router.get(
    "/search/users",
    response_model=StandardResponse[UserSearchResult],
    status_code=status.HTTP_200_OK,
    summary="Search Twitter users (OSINT - Direct)",
    description="Search for Twitter users based on query string - returns immediate results without task queuing"
)
async def search_users_osint(
    name: str = Query(..., description="Search query string"),
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results to return"),
    _: None = Depends(rate_limit)
):
    """Search for Twitter users with immediate results."""
    try:
        # Run scraping in separate thread to avoid Playwright async context issues
        result = run_scraping_in_thread('search_user', name, limit)
        
        return StandardResponse(
            status="success",
            message=f"Found {len(result.get('users', []))} users for query '{name}'",
            data=UserSearchResult(
                users=result.get('users', []),
                metadata=result.get('metadata', {})
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to search users: {str(e)}"
        )


@router.get(
    "/users/{username}/following",
    response_model=StandardResponse[FollowingResult],
    status_code=status.HTTP_200_OK,
    summary="Get user following list (OSINT - Direct)",
    description="Get list of users that the specified user follows - returns immediate results without task queuing"
)
async def get_user_following_osint(
    username: str,
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results to return"),
    _: None = Depends(rate_limit)
):
    """Get user's following list with immediate results."""
    try:
        # Run scraping in separate thread to avoid Playwright async context issues
        result = run_scraping_in_thread('following_user', username, limit)
        
        return StandardResponse(
            status="success",
            message=f"Retrieved {len(result.get('users', []))} users following @{username}",
            data=FollowingResult(
                users=result.get('users', []),
                metadata=result.get('metadata', {})
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get following list: {str(e)}"
        )


@router.get(
    "/users/{username}/followers",
    response_model=StandardResponse[FollowingResult],
    status_code=status.HTTP_200_OK,
    summary="Get user followers list (OSINT - Direct)",
    description="Get list of users that follow the specified user - returns immediate results without task queuing"
)
async def get_user_followers_osint(
    username: str,
    limit: Optional[int] = Query(20, ge=1, le=100, description="Number of results to return"),
    _: None = Depends(rate_limit)
):
    """Get user's followers list with immediate results."""
    try:
        # Run scraping in separate thread to avoid Playwright async context issues
        result = run_scraping_in_thread('followers_user', username, limit)
        
        return StandardResponse(
            status="success",
            message=f"Retrieved {len(result.get('users', []))} followers for @{username}",
            data=FollowingResult(
                users=result.get('users', []),
                metadata=result.get('metadata', {})
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get followers list: {str(e)}"
        )


@router.get(
    "/users/{username}/timeline",
    response_model=StandardResponse[TimelineResult],
    status_code=status.HTTP_200_OK,
    summary="Get user timeline analysis (OSINT - Direct)",
    description="Get user's timeline with tweets, hashtag analysis, and mention analysis - returns immediate results without task queuing"
)
async def get_user_timeline_osint(
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
    """Get user's timeline with analysis and immediate results."""
    try:
        # Run scraping in separate thread to avoid Playwright async context issues
        result = run_scraping_in_thread('timeline_tweet', username, count)
        
        # If analysis is not requested, remove it
        if not include_analysis:
            result.pop('hashtags', None)
            result.pop('mentions', None)
        
        timeline_count = len(result.get('timelines', []))
        hashtag_count = len(result.get('hashtags', []))
        mention_count = len(result.get('mentions', []))
        
        return StandardResponse(
            status="success",
            message=f"Retrieved {timeline_count} tweets, {hashtag_count} hashtags, {mention_count} mentions for @{username}",
            data=TimelineResult(
                timelines=result.get('timelines', []),
                hashtags=result.get('hashtags', []),
                mentions=result.get('mentions', []),
                metadata=result.get('metadata', {})
            )
        )
        
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Failed to get timeline: {str(e)}"
        )
