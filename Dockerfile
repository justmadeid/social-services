FROM python:3.11-slim

# Set environment variables
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# Set work directory
WORKDIR /app

# Install system dependencies required for Playwright
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        gcc \
        curl \
        default-libmysqlclient-dev \
        pkg-config \
        # Playwright browser dependencies
        wget \
        gnupg \
        ca-certificates \
        fonts-liberation \
        libappindicator3-1 \
        libasound2 \
        libatk-bridge2.0-0 \
        libatk1.0-0 \
        libcups2 \
        libdbus-1-3 \
        libdrm2 \
        libgbm1 \
        libgtk-3-0 \
        libnspr4 \
        libnss3 \
        libx11-xcb1 \
        libxcomposite1 \
        libxdamage1 \
        libxfixes3 \
        libxrandr2 \
        libxss1 \
        libxtst6 \
        xdg-utils \
        && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies  
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Install Playwright (but not browsers yet)
RUN pip install playwright

# Copy application code
COPY ./app /app/app
COPY ./scripts /app/scripts
COPY alembic.ini* ./

# Create non-root user and set up permissions
RUN adduser --disabled-password --gecos '' apiuser
RUN chown -R apiuser:apiuser /app
# Ensure playwright cache directory is accessible
RUN mkdir -p /home/apiuser/.cache/ms-playwright
RUN chown -R apiuser:apiuser /home/apiuser/.cache
# Create state directory for session persistence
RUN mkdir -p /app/state
RUN chown -R apiuser:apiuser /app/state

USER apiuser

# Install Playwright browsers as the apiuser
RUN playwright install chromium
RUN playwright install firefox  
RUN playwright install webkit

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
