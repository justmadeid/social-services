#!/usr/bin/env python3
"""
Database initialization script for Twitter Scraper API
"""
import asyncio
import sys
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.db.base import Base
from app.db.session import engine
from app.core.config import settings


async def init_db():
    """Initialize database tables."""
    print("Creating database tables...")
    
    async with engine.begin() as conn:
        # Create all tables
        await conn.run_sync(Base.metadata.create_all)
    
    print("Database tables created successfully!")


async def main():
    """Main function."""
    print(f"Initializing database: {settings.database_url}")
    
    try:
        await init_db()
        print("Database initialization completed!")
    except Exception as e:
        print(f"Database initialization failed: {e}")
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
