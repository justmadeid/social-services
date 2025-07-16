import time
import asyncio
from typing import Dict, Any
from celery import current_task
from sqlalchemy.ext.asyncio import AsyncSession

from app.worker.celery_app import celery_app
from app.scraper.twitter_scraper import TwitterScraper
from app.core.security import security_manager
from app.core.exceptions import ScrapingException
from app.db.session import AsyncSessionLocal
from app.crud.crud_settings import settings_crud


async def get_credentials(credential_name: str) -> tuple[str, str]:
    """Get decrypted credentials from database."""
    async with AsyncSessionLocal() as db:
        credentials = await settings_crud.get_by_name(db, credential_name=credential_name)
        if not credentials:
            raise ScrapingException(f"Credential '{credential_name}' not found")
        
        if not credentials.is_active:
            raise ScrapingException(f"Credential '{credential_name}' is not active")
        
        # Decrypt password
        password = security_manager.decrypt_password(
            credentials.encrypted_password, 
            credentials.salt
        )
        
        return credentials.username, password


def update_task_progress(progress: int, message: str = None):
    """Update task progress."""
    if current_task:
        current_task.update_state(
            state='PROCESSING',
            meta={'progress': progress, 'message': message or f"Processing... {progress}%"}
        )


@celery_app.task(bind=True, name="app.worker.tasks.login_task")
def login_task(self, credential_name: str):
    """Background task for Twitter login."""
    try:
        update_task_progress(10, "Retrieving credentials")
        
        # Get credentials (we need to handle async in sync context)
        import asyncio
        username, password = asyncio.run(get_credentials(credential_name))
        
        update_task_progress(30, "Initializing scraper")
        
        # Create scraper instance
        scraper = TwitterScraper(headless=True, username=username, password=password)
        
        update_task_progress(50, "Attempting login")
        
        # Perform login
        scraper.login()
        
        update_task_progress(100, "Login completed successfully")
        
        return {
            "status": "success",
            "message": f"Login successful for credential '{credential_name}'",
            "credential_name": credential_name,
            "completed_at": time.time()
        }
        
    except Exception as e:
        # Return error info in a structured way instead of using update_state
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'credential_name': credential_name,
            'failed_at': time.time()
        }
        raise Exception(f"Login failed for '{credential_name}': {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.search_users_task")
def search_users_task(self, query: str, limit: int = 20):
    """Background task for searching Twitter users."""
    try:
        update_task_progress(10, "Initializing scraper")
        
        # Create scraper instance (assumes login state exists)
        scraper = TwitterScraper(headless=True)
        
        update_task_progress(30, f"Searching for users: {query}")
        
        # Perform search
        result = scraper.search_user(query, limit)
        
        update_task_progress(100, f"Found {len(result.get('users', []))} users")
        
        return result
        
    except Exception as e:
        # Return error info in a structured way
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'query': query,
            'limit': limit,
            'failed_at': time.time()
        }
        raise Exception(f"Search failed for query '{query}': {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.get_following_task")
def get_following_task(self, username: str, limit: int = 20):
    """Background task for getting user's following list."""
    try:
        update_task_progress(10, "Initializing scraper")
        
        # Create scraper instance
        scraper = TwitterScraper(headless=True)
        
        update_task_progress(30, f"Getting following list for: {username}")
        
        # Get following list
        result = scraper.following_user(username, limit)
        
        update_task_progress(100, f"Retrieved {len(result.get('users', []))} following users")
        
        return result
        
    except Exception as e:
        # Return error info in a structured way
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'username': username,
            'limit': limit,
            'failed_at': time.time()
        }
        raise Exception(f"Get following failed for '{username}': {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.get_followers_task")
def get_followers_task(self, username: str, limit: int = 20):
    """Background task for getting user's followers list."""
    try:
        update_task_progress(10, "Initializing scraper")
        
        # Create scraper instance
        scraper = TwitterScraper(headless=True)
        
        update_task_progress(30, f"Getting followers list for: {username}")
        
        # Get followers list
        result = scraper.followers_user(username, limit)
        
        update_task_progress(100, f"Retrieved {len(result.get('users', []))} followers")
        
        return result
        
    except Exception as e:
        # Return error info in a structured way
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'username': username,
            'limit': limit,
            'failed_at': time.time()
        }
        raise Exception(f"Get followers failed for '{username}': {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.get_timeline_task")
def get_timeline_task(self, username: str, count: int = 80, include_analysis: bool = True):
    """Background task for getting user's timeline with analysis."""
    try:
        update_task_progress(10, "Initializing scraper")
        
        # Create scraper instance
        scraper = TwitterScraper(headless=True)
        
        update_task_progress(30, f"Getting timeline for: {username}")
        
        # Get timeline
        result = scraper.timeline_tweet(username, count)
        
        # If analysis is not requested, remove it
        if not include_analysis:
            result.pop('hashtags', None)
            result.pop('mentions', None)
        
        timeline_count = len(result.get('timelines', []))
        hashtag_count = len(result.get('hashtags', []))
        mention_count = len(result.get('mentions', []))
        
        update_task_progress(100, f"Retrieved {timeline_count} tweets, {hashtag_count} hashtags, {mention_count} mentions")
        
        return result
        
    except Exception as e:
        # Return error info in a structured way
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'username': username,
            'count': count,
            'failed_at': time.time()
        }
        raise Exception(f"Get timeline failed for '{username}': {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.test_task")
def test_task(self, message: str = "Hello from Celery!"):
    """Test task to verify Celery is working properly."""
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 25, 'message': 'Starting test task...'}
        )
        time.sleep(2)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 50, 'message': 'Processing...'}
        )
        time.sleep(2)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 75, 'message': 'Almost done...'}
        )
        time.sleep(2)
        
        self.update_state(
            state='PROCESSING',
            meta={'progress': 100, 'message': 'Test completed successfully'}
        )
        
        return {
            "status": "success",
            "message": message,
            "timestamp": time.time(),
            "result": "Test task completed successfully"
        }
        
    except Exception as e:
        # Return error info in a structured way  
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'message': message,
            'failed_at': time.time()
        }
        raise Exception(f"Test task failed: {str(e)}")


@celery_app.task(bind=True, name="app.worker.tasks.test_failure_task")
def test_failure_task(self, message: str = "This task will fail"):
    """Test task that intentionally fails to test error handling."""
    try:
        self.update_state(
            state='PROCESSING',
            meta={'progress': 50, 'message': 'About to fail...'}
        )
        time.sleep(1)
        
        # Intentionally cause an error
        raise ValueError("This is an intentional test failure")
        
    except Exception as e:
        # Return error info in a structured way
        error_info = {
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__,
            'message': message,
            'failed_at': time.time()
        }
        raise Exception(f"Test failure task failed as expected: {str(e)}")
