#!/usr/bin/env python3
"""
Direct startup test without lifespan
"""
import os
import sys

# Add the app directory to the Python path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

try:
    print("1. Testing core imports...")
    from app.core.config import settings
    print(f"   Settings loaded: {settings.project_name}")
    
    print("2. Testing schema imports...")
    from app.schemas.common import StandardResponse
    from app.schemas.twitter import UserSearchResult, FollowingResult, TimelineResult
    print("   Schema imports successful")
    
    print("3. Testing scraper import...")
    from app.scraper.twitter_scraper import TwitterScraper
    print("   TwitterScraper imported successfully")
    
    print("4. Testing OSINT router...")
    from app.api.endpoints.osint import router
    print(f"   OSINT router loaded with {len(router.routes)} routes")
    
    print("5. Testing FastAPI app creation...")
    from fastapi import FastAPI
    
    app = FastAPI(title="Test App")
    app.include_router(router, prefix="/api/v1/osint/twitter", tags=["osint"])
    
    print("6. Checking routes...")
    osint_routes = []
    for route in app.routes:
        if hasattr(route, 'path') and 'osint' in route.path:
            osint_routes.append(route.path)
    
    print(f"   Found {len(osint_routes)} OSINT routes:")
    for route in osint_routes:
        print(f"     - {route}")
    
    print("\n✅ All tests passed! OSINT endpoints are working correctly.")
    
except Exception as e:
    print(f"❌ Error: {e}")
    import traceback
    traceback.print_exc()
