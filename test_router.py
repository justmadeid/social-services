#!/usr/bin/env python3
"""
Direct endpoint test without creating full app
"""
from app.api.endpoints.osint import router

def test_osint_router():
    """Test the OSINT router directly."""
    print("OSINT Router routes:")
    for route in router.routes:
        if hasattr(route, 'path'):
            methods = ', '.join(route.methods) if hasattr(route, 'methods') else 'N/A'
            print(f"  {methods} {route.path}")
    
    print(f"\nTotal routes in OSINT router: {len(router.routes)}")

if __name__ == "__main__":
    test_osint_router()
