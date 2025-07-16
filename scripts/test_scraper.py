#!/usr/bin/env python3
"""
Standalone Twitter scraper testing script
"""
import sys
import json
import asyncio
from pathlib import Path

# Add the app directory to the Python path
sys.path.append(str(Path(__file__).parent.parent))

from app.scraper.twitter_scraper import TwitterScraper
from app.core.config import settings


async def test_scraper():
    """Test the Twitter scraper functionality."""
    print("Twitter Scraper Test")
    print("===================")
    
    # Initialize scraper
    username = input("Enter Twitter username: ")
    password = input("Enter Twitter password: ")
    
    scraper = TwitterScraper(headless=True, username=username, password=password)
    
    while True:
        print("\nSelect an option:")
        print("1. Login")
        print("2. Search users")
        print("3. Get following list")
        print("4. Get followers list")
        print("5. Get timeline")
        print("6. Exit")
        
        choice = input("Enter choice (1-6): ")
        
        try:
            if choice == "1":
                print("Logging in...")
                scraper.login()
                print("Login successful!")
                
            elif choice == "2":
                query = input("Enter search query: ")
                limit = int(input("Enter limit (default 20): ") or "20")
                print(f"Searching for users: {query}")
                result = scraper.search_user(query, limit)
                print(json.dumps(result, indent=2))
                
            elif choice == "3":
                target_username = input("Enter username: ")
                limit = int(input("Enter limit (default 20): ") or "20")
                print(f"Getting following list for: {target_username}")
                result = scraper.following_user(target_username, limit)
                print(json.dumps(result, indent=2))
                
            elif choice == "4":
                target_username = input("Enter username: ")
                limit = int(input("Enter limit (default 20): ") or "20")
                print(f"Getting followers list for: {target_username}")
                result = scraper.followers_user(target_username, limit)
                print(json.dumps(result, indent=2))
                
            elif choice == "5":
                target_username = input("Enter username: ")
                count = int(input("Enter tweet count (default 80): ") or "80")
                print(f"Getting timeline for: {target_username}")
                result = scraper.timeline_tweet(target_username, count)
                print(json.dumps(result, indent=2))
                
            elif choice == "6":
                print("Goodbye!")
                break
                
            else:
                print("Invalid choice!")
                
        except Exception as e:
            print(f"Error: {e}")


if __name__ == "__main__":
    asyncio.run(test_scraper())
