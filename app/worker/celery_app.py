from celery import Celery
from app.core.config import settings

# Create Celery application
celery_app = Celery(
    "twitter_scraper_worker",
    broker=settings.celery_broker_url,
    backend=settings.celery_result_backend,
    include=["app.worker.tasks"]
)

# Configure Celery
celery_app.conf.update(
    # Task serialization
    task_serializer="json",
    accept_content=["json"],
    result_serializer="json",
    
    # Timezone configuration
    timezone="UTC",
    enable_utc=True,
    
    # Result backend configuration
    result_expires=3600,  # Results expire after 1 hour
    result_persistent=True,
    
    # Exception handling
    task_track_started=True,
    task_ignore_result=False,
    result_backend_transport_options={
        'master_name': 'mymaster',
        'visibility_timeout': 3600,
    },
    
    # Task routing disabled - all tasks go to default queue
    # task_routes={
    #     "app.worker.tasks.login_task": {"queue": "login"},
    #     "app.worker.tasks.search_users_task": {"queue": "scraping"},
    #     "app.worker.tasks.get_following_task": {"queue": "scraping"},
    #     "app.worker.tasks.get_followers_task": {"queue": "scraping"},
    #     "app.worker.tasks.get_timeline_task": {"queue": "scraping"},
    # },
    
    # Worker configuration
    worker_prefetch_multiplier=1,
    task_acks_late=True,
    worker_max_tasks_per_child=50,
    
    # Retry configuration
    task_reject_on_worker_lost=True,
    task_default_retry_delay=60,
    task_max_retries=3,
    
    # Monitoring
    worker_send_task_events=True,
    task_send_sent_event=True,
)
