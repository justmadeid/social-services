#!/usr/bin/env python3
"""
Test OSINT endpoints with minimal setup
"""
from fastapi import FastAPI
from app.api.endpoints.osint import router

# Create minimal FastAPI app
app = FastAPI()

# Include the OSINT router
app.include_router(router, prefix="/api/v1/osint/twitter", tags=["osint"])

def test_endpoints():
    """Test that endpoints are properly registered."""
    print("Testing OSINT endpoints registration...")
    
    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path') and hasattr(route, 'methods'):
            methods = ', '.join(route.methods)
            routes.append((methods, route.path))
    
    print(f"Total routes: {len(routes)}")
    
    # Filter OSINT routes
    osint_routes = [(methods, path) for methods, path in routes if 'osint' in path]
    
    print(f"OSINT routes found: {len(osint_routes)}")
    for methods, path in osint_routes:
        print(f"  {methods} {path}")
    
    # Expected endpoints
    expected_endpoints = [
        "/api/v1/osint/twitter/search/users",
        "/api/v1/osint/twitter/users/{username}/following", 
        "/api/v1/osint/twitter/users/{username}/followers",
        "/api/v1/osint/twitter/users/{username}/timeline"
    ]
    
    print(f"\nExpected endpoints:")
    for endpoint in expected_endpoints:
        print(f"  {endpoint}")
    
    # Check if all expected endpoints are present
    found_paths = [path for methods, path in osint_routes]
    missing = [ep for ep in expected_endpoints if ep not in found_paths]
    
    if not missing:
        print("\n✅ All expected OSINT endpoints are registered!")
        return True
    else:
        print(f"\n❌ Missing endpoints: {missing}")
        return False

if __name__ == "__main__":
    success = test_endpoints()
    if success:
        print("\n🎉 OSINT endpoints setup completed successfully!")
    else:
        print("\n❌ Some endpoints are missing")
