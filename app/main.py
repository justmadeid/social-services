from fastapi import FastAPI, HTTPException, Depends, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.trustedhost import TrustedHostMiddleware
from fastapi.responses import JSONResponse
import time
import uuid
from contextlib import asynccontextmanager

from app.core.config import settings
from app.core.exceptions import APIException, ValidationException
from app.api.endpoints import settings as settings_router
from app.api.endpoints import auth as auth_router
from app.api.endpoints import tasks as tasks_router
from app.api.endpoints import scraping as scraping_router
from app.api.endpoints import osint as osint_router
from app.api.endpoints import health as health_router
from app.db.session import engine
from app.db.base import Base


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("Starting up Twitter Scraper API...")
    yield
    # Shutdown
    print("Shutting down Twitter Scraper API...")


# Create FastAPI application
app = FastAPI(
    title=settings.project_name,
    version=settings.project_version,
    description="A robust, scalable Twitter scraping API with asynchronous task processing",
    lifespan=lifespan,
    docs_url="/docs",
    redoc_url="/redoc",
)

# Add middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # React default
        "http://localhost:3001",  # Alternative React port
        "http://localhost:8080",  # Vue.js default
        "http://localhost:8081",  # Alternative Vue port
        "http://localhost:4200",  # Angular default
        "http://127.0.0.1:3000",
        "http://127.0.0.1:8080",
        "http://127.0.0.1:4200",
        "*"  # Fallback for development
    ],
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS", "PATCH"],
    allow_headers=["*"],
    expose_headers=["X-Request-ID", "X-Process-Time"],
)

app.add_middleware(
    TrustedHostMiddleware,
    allowed_hosts=["*"]  # Configure this for production
)


# Request ID middleware
@app.middleware("http")
async def add_request_id(request: Request, call_next):
    request_id = str(uuid.uuid4())
    request.state.request_id = request_id
    
    start_time = time.time()
    response = await call_next(request)
    process_time = time.time() - start_time
    
    response.headers["X-Request-ID"] = request_id
    response.headers["X-Process-Time"] = str(process_time)
    
    return response


# Exception handlers
@app.exception_handler(APIException)
async def api_exception_handler(request: Request, exc: APIException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.message,
            "code": exc.code,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(ValidationException)
async def validation_exception_handler(request: Request, exc: ValidationException):
    return JSONResponse(
        status_code=status.HTTP_400_BAD_REQUEST,
        content={
            "status": "error",
            "message": "Validation error",
            "errors": exc.errors,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    return JSONResponse(
        status_code=exc.status_code,
        content={
            "status": "error",
            "message": exc.detail,
            "request_id": getattr(request.state, "request_id", None)
        }
    )


# Health check endpoint
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": time.time(),
        "version": settings.project_version
    }


# Include routers
app.include_router(
    settings_router.router,
    prefix=f"{settings.api_v1_str}/settings",
    tags=["settings"]
)

app.include_router(
    auth_router.router,
    prefix=f"{settings.api_v1_str}/login",
    tags=["authentication"]
)

app.include_router(
    tasks_router.router,
    prefix=f"{settings.api_v1_str}/tasks",
    tags=["tasks"]
)

app.include_router(
    scraping_router.router,
    prefix=settings.api_v1_str,
    tags=["scraping"]
)

app.include_router(
    osint_router.router,
    prefix="/api/v1/osint/twitter",
    tags=["osint"]
)

app.include_router(
    health_router.router,
    prefix=f"{settings.api_v1_str}/health",
    tags=["health"]
)


# Root endpoint
@app.get("/")
async def root():
    return {
        "message": "Twitter Scraper API",
        "version": settings.project_version,
        "docs": "/docs",
        "redoc": "/redoc"
    }


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "app.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True if settings.environment == "development" else False,
        log_level=settings.log_level.lower()
    )
