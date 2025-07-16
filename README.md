# Twitter Scraper API

A robust, scalable, and asynchronous web API for Twitter scraping with background task processing, caching, and secure credential management.

## Features

- **Asynchronous Processing**: All scraping operations run as background tasks
- **Caching**: Redis-based caching for improved performance
- **Secure Storage**: Encrypted credential storage with AES-256-GCM
- **RESTful API**: Clean REST endpoints with comprehensive documentation
- **Task Management**: Real-time task status monitoring
- **Containerized**: Docker and Docker Compose ready
- **Scalable**: Horizontal scaling with Celery workers

## Technology Stack

- **FastAPI**: High-performance web framework
- **Celery**: Distributed task queue
- **Redis**: Caching and message broker
- **MySQL**: Persistent data storage
- **Playwright**: Browser automation
- **Docker**: Containerization

## Quick Start

### Using Docker Compose (Recommended)

1. **Clone and setup**:
```bash
cd twitter-scraper-api
cp .env.example .env
# Edit .env with your configuration
```

2. **Start services**:
```bash
docker-compose up -d
```

3. **Initialize database**:
```bash
docker-compose exec api python scripts/init_db.py
```

4. **Access the API**:
- API Documentation: http://localhost:8000/docs
- Celery Flower: http://localhost:5555
- API Base URL: http://localhost:8000

### Manual Setup

1. **Install dependencies**:
```bash
pip install -r requirements.txt
playwright install webkit
```

2. **Setup services**:
- Start MySQL server
- Start Redis server

3. **Configure environment**:
```bash
cp .env.example .env
# Edit .env with your database and Redis URLs
```

4. **Initialize database**:
```bash
python scripts/init_db.py
```

5. **Start services**:
```bash
# Terminal 1: Start API
uvicorn app.main:app --reload

# Terminal 2: Start Celery worker
celery -A app.worker.celery_app worker --loglevel=info

# Terminal 3: Start Celery Flower (optional)
celery -A app.worker.celery_app flower
```

## API Usage

### Save Twitter Credentials

```bash
curl -X POST "http://localhost:8000/api/v1/twitter/settings" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_name": "my_account",
    "username": "twitter_username",
    "password": "twitter_password"
  }'
```

### Login to Twitter

```bash
curl -X POST "http://localhost:8000/api/v1/twitter/login" \
  -H "Content-Type: application/json" \
  -d '{
    "credential_name": "my_account"
  }'
```

### Search Users

```bash
curl -X POST "http://localhost:8000/api/v1/twitter/search/users" \
  -H "Content-Type: application/json" \
  -d '{
    "name": "elon",
    "limit": 10
  }'
```

### Get User Timeline

```bash
curl -X GET "http://localhost:8000/api/v1/twitter/users/elonmusk/timeline?count=50" \
```

### Check Task Status

```bash
curl -X GET "http://localhost:8000/api/v1/twitter/tasks/{task_id}" \
```

## API Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/api/v1/twitter/settings` | Save Twitter credentials |
| GET | `/api/v1/twitter/settings` | List saved credentials |
| POST | `/api/v1/twitter/login` | Login to Twitter |
| GET | `/api/v1/twitter/tasks/{task_id}` | Get task status |
| POST | `/api/v1/twitter/search/users` | Search Twitter users |
| GET | `/api/v1/twitter/users/{username}/following` | Get following list |
| GET | `/api/v1/twitter/users/{username}/followers` | Get followers list |
| GET | `/api/v1/twitter/users/{username}/timeline` | Get timeline with analysis |

## Workflow

1. **Save Credentials**: Store Twitter login credentials securely
2. **Login**: Authenticate with Twitter and save session state
3. **Queue Tasks**: Submit scraping requests (returns immediately with task ID)
4. **Monitor Progress**: Check task status using task ID
5. **Retrieve Results**: Get final results when task completes

## Configuration

Key environment variables:

```bash
# Database
DATABASE_URL=mysql+aiomysql://user:pass@host:port/db

# Redis
REDIS_URL=redis://host:port/db
CELERY_BROKER_URL=redis://host:port/db

# Security
SECRET_KEY=your-secret-key
ENCRYPTION_KEY=your-32-char-encryption-key
API_KEY=your-api-key

# Cache TTL (seconds)
CACHE_TTL_USER_DATA=3600
CACHE_TTL_TIMELINE_DATA=21600
```

## Development

### Project Structure

```
app/
├── api/                  # API routes and endpoints
├── core/                 # Core configuration and utilities
├── crud/                 # Database operations
├── db/                   # Database models and session
├── schemas/              # Pydantic schemas
├── scraper/              # Scraping business logic
└── worker/               # Celery worker configuration
```

### Testing

```bash
# Test the scraper directly
python scripts/test_scraper.py

# Run API tests (if implemented)
pytest
```

### Database Migrations

```bash
# Generate migration
alembic revision --autogenerate -m "description"

# Apply migration
alembic upgrade head
```

## Production Deployment

For production deployment:

1. Use `docker-compose.prod.yml`
2. Set strong passwords and API keys
3. Configure SSL/TLS
4. Set up monitoring and logging
5. Configure load balancing
6. Use external managed services for MySQL and Redis

## Security Considerations

- Twitter credentials are encrypted using AES-256-GCM
- API access controlled by API keys
- All sensitive data is properly encrypted
- Rate limiting should be implemented
- Use HTTPS in production

## Monitoring

- Health check endpoint: `/health`
- Celery Flower dashboard: http://localhost:5555
- API documentation: http://localhost:8000/docs

## Limitations

- Respects Twitter's rate limits and terms of service
- Requires valid Twitter credentials
- Browser automation may be detected by anti-bot measures
- Performance depends on network and Twitter's response times

## License

This project is for educational and research purposes. Ensure compliance with Twitter's Terms of Service and applicable laws.

## Support

For issues and questions, please check the API documentation at `/docs` or review the technical specification document.
