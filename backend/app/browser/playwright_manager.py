import asyncio
from typing import Optional
from playwright.async_api import async_playwright, Playwright, Browser, BrowserContext, Page
from app.core.config import settings
from app.core.logging_config import logger
from app.core.security import should_block_resource, is_safe_url


class PlaywrightManager:
    """
    Manages Playwright browser instance, lifecycle, and anti-detection contexts.
    Applies safe resource blocking to speed up page navigation and prevent tracking.
    """

    def __init__(self):
        self._playwright: Optional[Playwright] = None
        self._browser: Optional[Browser] = None
        self._shared_context: Optional[BrowserContext] = None
        self._semaphore = asyncio.Semaphore(settings.MAX_CONCURRENT_PAGES)
        self._lock = asyncio.Lock()

    async def initialize(self) -> None:
        """Starts Playwright and launches the headless Chromium browser."""
        async with self._lock:
            if self._browser and self._browser.is_connected():
                return

            logger.info("Initializing Playwright browser manager...")
            try:
                self._playwright = await async_playwright().start()
                self._browser = await self._playwright.chromium.launch(
                    headless=settings.PLAYWRIGHT_HEADLESS,
                    args=[
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-dev-shm-usage",
                        "--disable-blink-features=AutomationControlled",
                        "--disable-infobars",
                        "--window-size=1280,800",
                    ]
                )
                self._shared_context = await self.create_stealth_context()
                logger.info("Playwright Chromium browser successfully launched.")
            except NotImplementedError:
                logger.error(
                    "Playwright requires asyncio ProactorEventLoop on Windows. "
                    "If running uvicorn with --reload, start with: --loop asyncio.windows_events:ProactorEventLoop"
                )
                raise
            except Exception as e:
                logger.error(f"Failed to launch Playwright browser: {e}")
                raise

    async def is_ready(self) -> bool:
        """Returns whether the browser is running and connected."""
        return self._browser is not None and self._browser.is_connected()

    async def get_context(self) -> BrowserContext:
        """Returns the shared stealth context or recreates if disconnected."""
        if not self._browser or not self._browser.is_connected():
            await self.initialize()
        if not self._shared_context:
            self._shared_context = await self.create_stealth_context()
        return self._shared_context

    async def create_stealth_context(self) -> BrowserContext:
        """Creates an isolated browser context with anti-bot detection configurations."""
        if not self._browser or not self._browser.is_connected():
            await self.initialize()

        context = await self._browser.new_context(
            user_agent=settings.USER_AGENT,
            viewport={"width": 1280, "height": 800},
            device_scale_factor=1,
            has_touch=False,
            is_mobile=False,
            java_script_enabled=True,
            bypass_csp=False,
            locale="en-US",
            timezone_id="America/New_York",
        )

        # Mask webdriver flag to avoid bot detection
        await context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', {
                get: () => undefined
            });
            Object.defineProperty(navigator, 'plugins', {
                get: () => [1, 2, 3, 4, 5]
            });
            Object.defineProperty(navigator, 'languages', {
                get: () => ['en-US', 'en']
            });
            window.chrome = {
                runtime: {}
            };
        """)

        # Set up safe route filtering (abort images, media, fonts, stylesheets, trackers)
        async def route_interceptor(route):
            request = route.request
            if should_block_resource(request.url, request.resource_type):
                await route.abort()
            else:
                await route.continue_()

        await context.route("**/*", route_interceptor)
        return context

    async def fetch_page_content(self, url: str) -> tuple[Optional[str], Optional[str], int]:
        """
        Navigates to the given URL safely within semaphore limits and extracts raw HTML and title.
        Returns: (html_content, page_title, status_code)
        """
        safe, reason = is_safe_url(url)
        if not safe:
            logger.warning(f"[Playwright] Blocked navigation to unsafe URL '{url}': {reason}")
            return None, f"Blocked: {reason}", 403

        async with self._semaphore:
            page: Optional[Page] = None
            try:
                context = await self.get_context()
                page = await context.new_page()
                page.set_default_timeout(settings.BROWSER_TIMEOUT_MS)
                logger.info(f"[Playwright] Navigating to: {url}")
                response = await page.goto(
                    url,
                    wait_until="domcontentloaded",
                    timeout=settings.BROWSER_TIMEOUT_MS
                )

                status_code = response.status if response else 200
                title = await page.title()
                html = await page.content()

                return html, title, status_code
            except Exception as e:
                logger.warning(f"[Playwright] Fast skip for {url}: {e}")
                return None, str(e), 500
            finally:
                if page:
                    try:
                        await page.close()
                    except Exception:
                        pass

    async def close(self) -> None:
        """Closes browser and Playwright process cleanly."""
        async with self._lock:
            if self._browser:
                try:
                    await self._browser.close()
                    logger.info("Playwright browser closed.")
                except Exception as e:
                    logger.warning(f"Error closing browser: {e}")
                self._browser = None

            if self._playwright:
                try:
                    await self._playwright.stop()
                    logger.info("Playwright stopped.")
                except Exception as e:
                    logger.warning(f"Error stopping Playwright: {e}")
                self._playwright = None


playwright_manager = PlaywrightManager()
