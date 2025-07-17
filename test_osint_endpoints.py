#!/usr/bin/env python3
"""
Test script to verify OSINT endpoints are properly registered
"""
from app.main import app
from fastapi.testclient import TestClient

def test_osint_endpoints():
    """Test that OSINT endpoints are properly registered."""
    client = TestClient(app)
    
    # Get all routes
    routes = []
    for route in app.routes:
        if hasattr(route, 'path'):
            routes.append(route.path)
    
    # Check for OSINT routes
    osint_routes = [r for r in routes if 'osint' in r]
    print("OSINT routes found:")
    for route in osint_routes:
        print(f"  - {route}")
    
    # Test if the endpoints exist (without actually calling them)
    expected_routes = [
        "/api/v1/osint/twitter/search/users",
        "/api/v1/osint/twitter/users/{username}/following",
        "/api/v1/osint/twitter/users/{username}/followers",
        "/api/v1/osint/twitter/users/{username}/timeline"
    ]
    
    print("\nExpected routes:")
    for route in expected_routes:
        print(f"  - {route}")
    
    # Check if all expected routes exist
    found_routes = set(osint_routes)
    expected_routes_set = set(expected_routes)
    
    print(f"\nRoute check:")
    print(f"Expected: {len(expected_routes_set)} routes")
    print(f"Found: {len(found_routes)} routes")
    
    if expected_routes_set.issubset(found_routes):
        print("✅ All expected OSINT routes are registered!")
    else:
        missing = expected_routes_set - found_routes
        print(f"❌ Missing routes: {missing}")
    
    return len(osint_routes) > 0

if __name__ == "__main__":
    test_osint_endpoints()
