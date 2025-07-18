import asyncio
import json
import time
import re
import os
from os import path
from playwright.sync_api import sync_playwright
from datetime import datetime
from collections import Counter
from typing import Dict, List, Optional, Any
import hashlib

from app.core.config import settings
from app.core.exceptions import ScrapingException
from app.scraper.cache_manager import cache_manager


class TwitterScraper:
    """Refactored Twitter scraper with caching and error handling."""
    
    def __init__(self, headless: bool = True, username: Optional[str] = None, password: Optional[str] = None):
        self.headless = headless
        self.username = username
        self.password = password
        self.browser = None        # Set state file path - use a persistent location
        self._set_state_file_path()
        
    def _set_state_file_path(self):
        """Set the path for the state.json file, ensuring it's in a persistent location."""
        # Try to use a persistent directory based on environment
        if os.path.exists('/app/state'):
            # Docker environment - use mounted state volume
            state_dir = '/app/state'
        elif os.path.exists('/app'):
            # Docker environment - use app directory
            state_dir = '/app'
        elif os.path.exists('/tmp'):
            # Linux/Mac fallback to tmp directory
            state_dir = '/tmp'
        else:
            # Local development - use project root directory
            # Get the project root (go up from app/scraper/ to project root)
            current_file_dir = os.path.dirname(os.path.abspath(__file__))
            project_root = os.path.dirname(os.path.dirname(current_file_dir))
            state_dir = project_root
        
        self.state_file = os.path.join(state_dir, "state.json")
        print(f"State file will be saved to: {self.state_file}")
        
        # Ensure the directory exists and is writable
        try:
            os.makedirs(os.path.dirname(self.state_file), exist_ok=True)
        except Exception as e:
            print(f"Could not create state directory: {e}")
            # If we can't create the directory, fall back to current directory
            self.state_file = "state.json"
            print(f"Fallback state file location: {self.state_file}")

    def _generate_cache_key(self, operation: str, params: Dict[str, Any]) -> str:
        """Generate cache key for operation and parameters."""
        param_string = json.dumps(params, sort_keys=True)
        param_hash = hashlib.md5(param_string.encode()).hexdigest()
        return f"cache:{operation}:{param_hash}"

    def ensure_login(self):
        """Ensure user is logged in before scraping."""
        if not path.exists(self.state_file):
            print(f"State file not found at: {self.state_file}")
            if not self.username or not self.password:
                # Try to get active credentials from database as fallback
                print("No credentials provided, attempting to fetch from database...")
                try:
                    import asyncio
                    from app.db.session import AsyncSessionLocal
                    from app.crud.crud_settings import settings_crud
                    from app.core.security import security_manager
                    
                    async def get_fallback_credentials():
                        async with AsyncSessionLocal() as db:
                            active_credentials = await settings_crud.get_active_credentials(db)
                            if active_credentials:
                                # Use the first active credential
                                credential = active_credentials[0]
                                password = security_manager.decrypt_password(
                                    credential.encrypted_password, 
                                    credential.salt
                                )
                                return credential.username, password
                            return None, None                    # Run async code in a separate thread to avoid event loop conflict
                    import concurrent.futures
                    import threading
                    
                    def run_async_in_thread():
                        # Create a new event loop for this thread
                        loop = asyncio.new_event_loop()
                        asyncio.set_event_loop(loop)
                        try:
                            return loop.run_until_complete(get_fallback_credentials())
                        finally:
                            loop.close()
                    
                    # Run the async function in a separate thread
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        future = executor.submit(run_async_in_thread)
                        username, password = future.result()
                    
                    if username and password:
                        print(f"Using fallback credentials for user: {username}")
                        self.username = username
                        self.password = password
                        print("Attempting to login with fallback credentials...")
                        self.login()
                    else:
                        raise ScrapingException("No login state found, no credentials provided, and no active credentials in database")
                except Exception as e:
                    print(f"Failed to fetch fallback credentials: {e}")
                    raise ScrapingException("No login state found and no credentials provided")
            else:
                print("Attempting to login...")
                self.login()
        else:
            print(f"State file found at: {self.state_file}")
            # Verify the state file is valid
            try:
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    if not state_data.get('cookies'):
                        print("State file exists but contains no cookies, re-login required")
                        if not self.username or not self.password:
                            # Try to get active credentials from database as fallback
                            print("No credentials provided, attempting to fetch from database...")
                            try:
                                import asyncio
                                from app.db.session import AsyncSessionLocal
                                from app.crud.crud_settings import settings_crud
                                from app.core.security import security_manager
                                
                                async def get_fallback_credentials():
                                    async with AsyncSessionLocal() as db:
                                        active_credentials = await settings_crud.get_active_credentials(db)
                                        if active_credentials:
                                            # Use the first active credential
                                            credential = active_credentials[0]
                                            password = security_manager.decrypt_password(
                                                credential.encrypted_password, 
                                                credential.salt
                                            )
                                            return credential.username, password
                                        return None, None
                                
                                # Run async code in a separate thread to avoid event loop conflict
                                import concurrent.futures
                                import threading
                                
                                def run_async_in_thread():
                                    # Create a new event loop for this thread
                                    loop = asyncio.new_event_loop()
                                    asyncio.set_event_loop(loop)
                                    try:
                                        return loop.run_until_complete(get_fallback_credentials())
                                    finally:
                                        loop.close()
                                
                                # Run the async function in a separate thread
                                with concurrent.futures.ThreadPoolExecutor() as executor:
                                    future = executor.submit(run_async_in_thread)
                                    username, password = future.result()
                                
                                if username and password:
                                    print(f"Using fallback credentials for user: {username}")
                                    self.username = username
                                    self.password = password
                                    print("Attempting to login with fallback credentials...")
                                    self.login()
                                else:
                                    raise ScrapingException("State file corrupted, no credentials provided, and no active credentials in database")
                            except Exception as e:
                                print(f"Failed to fetch fallback credentials: {e}")
                                raise ScrapingException("State file corrupted and no credentials provided")
                        else:
                            self.login()
                    else:
                        print("Valid state file found, using existing session")
            except (json.JSONDecodeError, KeyError, FileNotFoundError):
                print("State file is corrupted or unreadable, re-login required")
                if not self.username or not self.password:
                    # Try to get active credentials from database as fallback
                    print("No credentials provided, attempting to fetch from database...")
                    try:
                        import asyncio
                        from app.db.session import AsyncSessionLocal
                        from app.crud.crud_settings import settings_crud
                        from app.core.security import security_manager
                        
                        async def get_fallback_credentials():
                            async with AsyncSessionLocal() as db:
                                active_credentials = await settings_crud.get_active_credentials(db)
                                if active_credentials:
                                    # Use the first active credential
                                    credential = active_credentials[0]
                                    password = security_manager.decrypt_password(
                                        credential.encrypted_password, 
                                        credential.salt
                                    )
                                    return credential.username, password
                                return None, None
                        
                        # Run async code in a separate thread to avoid event loop conflict
                        import concurrent.futures
                        import threading
                        
                        def run_async_in_thread():
                            # Create a new event loop for this thread
                            loop = asyncio.new_event_loop()
                            asyncio.set_event_loop(loop)
                            try:
                                return loop.run_until_complete(get_fallback_credentials())
                            finally:
                                loop.close()
                        
                        # Run the async function in a separate thread
                        with concurrent.futures.ThreadPoolExecutor() as executor:
                            future = executor.submit(run_async_in_thread)
                            username, password = future.result()
                        
                        if username and password:
                            print(f"Using fallback credentials for user: {username}")
                            self.username = username
                            self.password = password
                            print("Attempting to login with fallback credentials...")
                            self.login()
                        else:
                            raise ScrapingException("State file corrupted, no credentials provided, and no active credentials in database")
                    except Exception as e:
                        print(f"Failed to fetch fallback credentials: {e}")
                        raise ScrapingException("State file corrupted and no credentials provided")
                else:
                    self.login()

    def login(self):
        """Login to Twitter and save session state."""
        if not self.username or not self.password:
            raise ScrapingException("Username and password required for login")
            
        try:
            print(f"Starting login process for user: {self.username}")
            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1280, "height": 1024},
                    user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                )
                page = context.new_page()
                
                print("Navigating to Twitter login page...")
                page.goto("https://twitter.com/i/flow/login")
                page.wait_for_selector("[data-testid='google_sign_in_container']", timeout=30000)
                time.sleep(2)
                
                print("Filling username...")
                page.fill('input[type="text"]', self.username)
                time.sleep(2)
                page.locator("//span[text()='Next']").click()
                page.wait_for_selector("[data-testid='LoginForm_Login_Button']", timeout=30000)
                time.sleep(2)
                
                print("Filling password...")
                page.fill('input[type="password"]', self.password)
                time.sleep(2)
                page.locator("//span[text()='Log in']").click()
                time.sleep(5)
                
                # Wait for login to complete - check for home page or user profile
                try:
                    page.wait_for_selector("[data-testid='primaryColumn']", timeout=30000)
                    print("Login successful, saving session state...")
                except:
                    print("Login might have failed or taken longer than expected")
                
                # Save session state
                context.storage_state(path=self.state_file)
                print(f"Session state saved to: {self.state_file}")
                
                # Verify state file was created
                if os.path.exists(self.state_file):
                    file_size = os.path.getsize(self.state_file)
                    print(f"State file created successfully, size: {file_size} bytes")
                    
                    # Quick validation of the state file
                    with open(self.state_file, 'r') as f:
                        state_data = json.load(f)
                        if state_data.get('cookies'):
                            print(f"State file contains {len(state_data['cookies'])} cookies")
                        else:
                            print("Warning: State file contains no cookies")
                else:
                    print("Error: State file was not created")
                
                time.sleep(2)
                context.close()
                browser.close()
                print("Login process completed")
                
        except Exception as e:
            print(f"Login failed with error: {str(e)}")
            raise ScrapingException(f"Login failed: {str(e)}")

    def search_user(self, user_input: str, limit: int = 20) -> Dict[str, Any]:
        """Search for Twitter users."""
        # Check cache first
        cache_key = self._generate_cache_key("search_user", {"query": user_input, "limit": limit})
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        self.ensure_login()
        start_time = time.time()
        
        try:
            _xhr_calls = []

            def intercept_response(response):
                if response.request.resource_type == "xhr":
                    _xhr_calls.append(response)
                return response

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, 
                    storage_state=self.state_file
                )
                page = context.new_page()

                page.on("response", intercept_response)
                page.goto(f"https://twitter.com/search?q={user_input}&src=typed_query&f=user")
                page.wait_for_selector("[data-testid='cellInnerDiv']", timeout=30000)
                time.sleep(5)

                # Find search timeline XHR call
                tweet_calls = []
                for f in _xhr_calls:
                    if re.search("SearchTimeline", f.url):
                        tweet_calls = [f]
                        break

                users = []
                if tweet_calls:
                    for xhr in tweet_calls:
                        try:
                            data = xhr.json()
                            search_result = data['data']['search_by_raw_query']['search_timeline']['timeline']['instructions'][1]['entries']
                            
                            # Remove cursor entries
                            search_result = search_result[:-2] if len(search_result) > 2 else search_result
                            # del search_result[-2:]

                            for sr in search_result[:limit]:
                                try:
                                    legacy = sr['content']['itemContent']['user_results']['result']
                                    users.append({
                                        "user_id": legacy['rest_id'],
                                        "name": legacy.get('core', {}).get('name', ''),
                                        "screen_name": legacy.get('core', {}).get('screen_name', ''),
                                        "bio": legacy.get('legacy', {}).get('description', ''),
                                        "location": legacy.get('location', {}).get('location', ''),
                                        "followers": legacy.get('legacy', {}).get('followers_count', 0),
                                        "following": legacy.get('legacy', {}).get('friends_count', 0),
                                        "tweets": legacy.get('legacy', {}).get('statuses_count', 0),
                                        "favorites": legacy.get('legacy', {}).get('favourites_count', 0),
                                        "private": legacy.get('legacy', {}).get('protected', False),
                                        "verified": legacy.get('is_blue_verified', False),
                                        "avatar": legacy.get('avatar', {}).get('image_url', ''),
                                        "profile_banner": legacy.get('legacy', {}).get('profile_banner_url', ''),
                                        "created": legacy.get('core', {}).get('created_at', ''),
                                    })
                                except (KeyError, TypeError):
                                    continue
                        except (json.JSONDecodeError, KeyError):
                            continue

                context.close()
                browser.close()

                execution_time = time.time() - start_time
                result = {
                    "users": users,
                    "metadata": {
                        "query": user_input,
                        "result_count": len(users),
                        "execution_time": execution_time,
                        "cached": False
                    }
                }

                # Cache the result
                cache_manager.set(cache_key, result, ttl=settings.cache_ttl_user_data)
                return result

        except Exception as e:
            raise ScrapingException(f"User search failed: {str(e)}")

    def following_user(self, username: str, limit: int = 20) -> Dict[str, Any]:
        """Get users that the specified user follows."""
        # Check cache first
        cache_key = self._generate_cache_key("following_user", {"username": username, "limit": limit})
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        self.ensure_login()
        start_time = time.time()
        
        try:
            _xhr_calls = []

            def intercept_response(response):
                if response.request.resource_type == "xhr":
                    _xhr_calls.append(response)
                return response

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, 
                    storage_state=self.state_file
                )
                page = context.new_page()

                page.on("response", intercept_response)
                page.goto(f"https://twitter.com/{username}/following")
                page.wait_for_selector("[data-testid='cellInnerDiv']", timeout=30000)
                time.sleep(5)

                # Find following XHR call
                following_calls = []
                for f in _xhr_calls:
                    if re.search("Following", f.url):
                        following_calls = [f]
                        break

                users = []
                if following_calls:
                    for xhr in following_calls:
                        try:
                            data = xhr.json()
                            instruction = data['data']['user']['result']['timeline']['timeline']['instructions']
                            following_result = next(
                                (ins['entries'] for ins in instruction if ins['type'] == 'TimelineAddEntries'), 
                                []
                            )

                            # Remove cursor entries
                            following_result = following_result[:-2] if len(following_result) > 2 else following_result

                            for fr in following_result[:limit]:
                                try:
                                    legacy = fr['content']['itemContent']['user_results']['result']
                                    users.append({
                                        "id": legacy['rest_id'],
                                        "name": legacy.get('core', {}).get('name', ''),
                                        "username": legacy.get('core', {}).get('screen_name', ''),
                                        "bio"  : legacy.get('legacy', {}).get('description', ''),
                                        "followers": legacy.get('legacy', {}).get('followers_count', 0),
                                        "following": legacy.get('legacy', {}).get('friends_count', 0),
                                        "url": legacy.get('legacy', {}).get('url', ''),
                                        "tweets": legacy.get('legacy', {}).get('statuses_count', 0),
                                        "profile_image_url_https": legacy.get('avatar', {}).get('image_url', ''),
                                        "created": legacy.get('core', {}).get('created_at', ''),
                                        "blue_verified": legacy.get('is_blue_verified', False),
                                        "location": legacy.get('location', {}).get('location', ''),
                                    })
                                except (KeyError, TypeError):
                                    continue
                        except (json.JSONDecodeError, KeyError):
                            continue

                context.close()
                browser.close()

                execution_time = time.time() - start_time
                result = {
                    "users": users,
                    "metadata": {
                        "username": username,
                        "result_count": len(users),
                        "execution_time": execution_time,
                        "cached": False
                    }
                }

                # Cache the result
                cache_manager.set(cache_key, result, ttl=settings.cache_ttl_user_data)
                return result

        except Exception as e:
            raise ScrapingException(f"Following list retrieval failed: {str(e)}")

    def followers_user(self, username: str, limit: int = 20) -> Dict[str, Any]:
        """Get users that follow the specified user."""
        # Check cache first
        cache_key = self._generate_cache_key("followers_user", {"username": username, "limit": limit})
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        self.ensure_login()
        start_time = time.time()
        
        try:
            _xhr_calls = []

            def intercept_response(response):
                if response.request.resource_type == "xhr":
                    _xhr_calls.append(response)
                return response

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1920, "height": 1080}, 
                    storage_state=self.state_file
                )
                page = context.new_page()

                page.on("response", intercept_response)
                page.goto(f"https://twitter.com/{username}/followers")
                page.wait_for_selector("[data-testid='cellInnerDiv']", timeout=30000)
                time.sleep(5)

                # Find followers XHR call
                followers_calls = []
                for f in _xhr_calls:
                    if re.search("Followers", f.url):
                        followers_calls = [f]
                        break

                users = []
                if followers_calls:
                    for xhr in followers_calls:
                        try:
                            data = xhr.json()
                            instruction = data['data']['user']['result']['timeline']['timeline']['instructions']
                            followers_result = next(
                                (ins['entries'] for ins in instruction if ins['type'] == 'TimelineAddEntries'), 
                                []
                            )

                            # Remove cursor entries
                            followers_result = followers_result[:-2] if len(followers_result) > 2 else followers_result

                            for fr in followers_result[:limit]:
                                try:
                                    legacy = fr['content']['itemContent']['user_results']['result']
                                    users.append({
                                        "id": legacy['rest_id'],
                                        "name": legacy.get('core', {}).get('name', ''),
                                        "username": legacy.get('core', {}).get('screen_name', ''),
                                        "bio"  : legacy.get('legacy', {}).get('description', ''),
                                        "followers": legacy.get('legacy', {}).get('followers_count', 0),
                                        "following": legacy.get('legacy', {}).get('friends_count', 0),
                                        "url": legacy.get('legacy', {}).get('url', ''),
                                        "tweets": legacy.get('legacy', {}).get('statuses_count', 0),
                                        "profile_image_url_https": legacy.get('avatar', {}).get('image_url', ''),
                                        "created": legacy.get('core', {}).get('created_at', ''),
                                        "blue_verified": legacy.get('is_blue_verified', False),
                                        "location": legacy.get('location', {}).get('location', ''),
                                    })
                                except (KeyError, TypeError):
                                    continue
                        except (json.JSONDecodeError, KeyError):
                            continue

                context.close()
                browser.close()

                execution_time = time.time() - start_time
                result = {
                    "users": users,
                    "metadata": {
                        "username": username,
                        "result_count": len(users),
                        "execution_time": execution_time,
                        "cached": False
                    }
                }

                # Cache the result
                cache_manager.set(cache_key, result, ttl=settings.cache_ttl_user_data)
                return result

        except Exception as e:
            raise ScrapingException(f"Followers list retrieval failed: {str(e)}")

    def timeline_tweet(self, username: str, tweet_count: int = 80) -> Dict[str, Any]:
        """Get user's timeline with tweets, hashtag analysis, and mention analysis."""
        # Check cache first
        cache_key = self._generate_cache_key("timeline_tweet", {"username": username, "tweet_count": tweet_count})
        cached_result = cache_manager.get(cache_key)
        if cached_result:
            return cached_result

        self.ensure_login()
        start_time = time.time()
        
        try:
            _xhr_calls = []
            min_count = settings.min_tweet_count
            max_count = settings.max_tweet_count

            def intercept_response(response):
                if response.request.resource_type == "xhr":
                    _xhr_calls.append(response)
                return response

            with sync_playwright() as pw:
                browser = pw.chromium.launch(headless=self.headless)
                context = browser.new_context(
                    viewport={"width": 1800, "height": 1080}, 
                    storage_state=self.state_file
                )
                page = context.new_page()

                page.on("response", intercept_response)
                page.goto(f"https://twitter.com/{username}")
                page.wait_for_selector("[data-testid='tweet']", timeout=30000)
                time.sleep(5)

                _prev_height = -1
                _max_scrolls = int(round(tweet_count / 20, 0)) if min_count <= tweet_count <= max_count else 1
                _scroll_count = 0

                timeline = []
                hashtags_data = {}
                mentions_data = {}

                while _scroll_count < _max_scrolls:
                    page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    page.wait_for_timeout(1000)
                    new_height = page.evaluate("document.body.scrollHeight")
                    if new_height == _prev_height:
                        break
                    _prev_height = new_height
                    _scroll_count += 1
                    time.sleep(5)

                    # Process XHR calls for this scroll
                    user_tweets_calls = []
                    for f in _xhr_calls:
                        if re.search("UserTweets", f.url):
                            user_tweets_calls.append(f)

                    for xhr in user_tweets_calls:
                        try:
                            data = xhr.json()
                            instruction = data['data']['user']['result']['timeline']['timeline']['instructions']
                            tweet_result = next(
                                (ins['entries'] for ins in instruction if ins['type'] == 'TimelineAddEntries'), 
                                []
                            )

                            # Remove cursor entries
                            tweet_result = tweet_result[:-2] if len(tweet_result) > 2 else tweet_result

                            for tr in tweet_result:
                                try:
                                    if any("tweet" in s for s in tr['entryId'].split("-")):
                                        tweet_data = tr['content']['itemContent']['tweet_results']['result']
                                        legacy = tweet_data['legacy']
                                        view = tweet_data.get('views', {})
                                        core = tweet_data['core']['user_results']['result']['legacy']
                                        co = tweet_data['core']['user_results']['result']['core']

                                        hashtags = re.findall(r'#(\w+)', legacy['full_text'])
                                        mentions = re.findall(r'@(\w+)', legacy['full_text'])

                                        # Update hashtag and mention counters
                                        for hashtag in hashtags:
                                            hashtags_data.setdefault(hashtag, {"count": 0, "percentage": 0})
                                            hashtags_data[hashtag]["count"] += 1

                                        for mention in mentions:
                                            mentions_data.setdefault(mention, {"count": 0, "percentage": 0})
                                            mentions_data[mention]["count"] += 1

                                        # Handle media
                                        mediainf = ""
                                        if 'entities' in legacy and 'media' in legacy['entities'] and legacy['entities']['media']:
                                            media = legacy['entities']['media'][0]
                                            if media['type'] == 'video':
                                                mediainf = media.get('video_info', {}).get('variants', [{}])[0].get('url', '')
                                            elif media['type'] == 'photo':
                                                mediainf = media.get('media_url_https', '')

                                        # Calculate engagement
                                        follower = int(core.get('followers_count', 1))
                                        views = int(view.get('count', 0)) if view else 0
                                        like = int(legacy.get('favorite_count', 0))
                                        retweet = int(legacy.get('retweet_count', 0))
                                        reply = int(legacy.get('reply_count', 0))
                                        quote = int(legacy.get('quote_count', 0))
                                        
                                        engagement = ((views + like + retweet + reply + quote) / follower) * 100

                                        # Parse date
                                        date_tweet = legacy.get('created_at', '')
                                        iso8601_date_str = ""
                                        if date_tweet:
                                            try:
                                                date_convert = datetime.strptime(date_tweet, "%a %b %d %H:%M:%S %z %Y")
                                                iso8601_date_str = date_convert.isoformat()
                                            except:
                                                iso8601_date_str = date_tweet

                                        url_tweet = f"https://twitter.com/{username}/status/{legacy['id_str']}"
                                        
                                        timeline.append({
                                            "id": legacy['id_str'],
                                            "user_id": legacy.get('user_id_str', ''),
                                            "date": iso8601_date_str,
                                            "tweets": legacy.get('full_text', ''),
                                            "screen_name": co.get('screen_name', ''),
                                            "name": co.get('name', ''),
                                            "retweet": legacy.get('retweet_count', 0),
                                            "replies": legacy.get('reply_count', 0),
                                            "link_media": mediainf,
                                            "likes": legacy.get('favorite_count', 0),
                                            "link": url_tweet,
                                            "views": views,
                                            "quote": quote,
                                            "engagement": engagement,
                                            "hashtags": hashtags,
                                            "mentions": mentions,
                                            "source": tweet_data.get('source', '')
                                        })
                                except (KeyError, TypeError, AttributeError):
                                    continue
                        except (json.JSONDecodeError, KeyError):
                            continue

                context.close()
                browser.close()

                # Calculate percentages
                total_hashtags = sum(data["count"] for data in hashtags_data.values())
                total_mentions = sum(data["count"] for data in mentions_data.values())

                for hashtag, data in hashtags_data.items():
                    data["percentage"] = (data["count"] / total_hashtags) * 100 if total_hashtags > 0 else 0

                for mention, data in mentions_data.items():
                    data["percentage"] = (data["count"] / total_mentions) * 100 if total_mentions > 0 else 0

                hashtags_result = [
                    {"hashtags": hashtag, "count": data["count"], "percentage": data["percentage"]} 
                    for hashtag, data in hashtags_data.items()
                ]
                mentions_result = [
                    {"user_mention": mention, "count": data["count"], "percentage": data["percentage"]} 
                    for mention, data in mentions_data.items()
                ]

                execution_time = time.time() - start_time
                result = {
                    "timelines": timeline,
                    "hashtags": hashtags_result,
                    "mentions": mentions_result,
                    "metadata": {
                        "username": username,
                        "total_tweets": len(timeline),
                        "analysis_period": datetime.now().isoformat(),
                        "execution_time": execution_time,
                        "cached": False
                    }
                }                # Cache the result
                cache_manager.set(cache_key, result, ttl=settings.cache_ttl_timeline_data)
                return result
                
        except Exception as e:
            raise ScrapingException(f"Timeline retrieval failed: {str(e)}")
    
    def check_login_status(self) -> Dict[str, Any]:
        """Check the current login status and state file information."""
        status = {
            "state_file_path": self.state_file,
            "state_file_exists": os.path.exists(self.state_file),
            "state_file_size": 0,
            "cookies_count": 0,
            "valid_cookies_count": 0,
            "has_credentials": bool(self.username and self.password),
            "login_required": False,
            "session_valid": False
        }
        
        if status["state_file_exists"]:
            try:
                status["state_file_size"] = os.path.getsize(self.state_file)
                with open(self.state_file, 'r') as f:
                    state_data = json.load(f)
                    cookies = state_data.get('cookies', [])
                    status["cookies_count"] = len(cookies)
                    
                    # Check for valid, non-expired cookies
                    current_time = time.time()
                    valid_cookies = []
                    for cookie in cookies:
                        # Check if cookie has expiry and is not expired
                        if 'expires' in cookie:
                            if cookie['expires'] == -1 or cookie['expires'] > current_time:
                                valid_cookies.append(cookie)
                        else:
                            # Session cookies (no expiry) are considered valid
                            valid_cookies.append(cookie)
                    
                    status["valid_cookies_count"] = len(valid_cookies)
                    
                    # More sophisticated login requirement check
                    if len(cookies) == 0:
                        status["login_required"] = True
                        status["session_valid"] = False
                    elif len(valid_cookies) == 0:
                        status["login_required"] = True
                        status["session_valid"] = False
                        status["error"] = "All cookies are expired"
                    else:
                        # Check if we have Twitter authentication cookies
                        twitter_auth_cookies = [c for c in valid_cookies 
                                              if c.get('name') in ['auth_token', 'ct0', 'twid']]
                        if twitter_auth_cookies:
                            status["login_required"] = False
                            status["session_valid"] = True
                        else:
                            status["login_required"] = True
                            status["session_valid"] = False
                            status["error"] = "No Twitter authentication cookies found"
                            
            except (json.JSONDecodeError, FileNotFoundError, PermissionError) as e:
                status["error"] = str(e)
                status["login_required"] = True
                status["session_valid"] = False
        else:
            status["login_required"] = True
            status["session_valid"] = False
        
        return status

    def clear_state_file(self):
        """Clear the state file to force a fresh login."""
        if os.path.exists(self.state_file):
            try:
                os.remove(self.state_file)
                print(f"State file removed: {self.state_file}")
                return True
            except Exception as e:
                print(f"Error removing state file: {e}")
                return False
        return True


# Create singleton instance
twitter_scraper = TwitterScraper(headless=True)
