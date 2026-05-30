"""
Sessione Playwright condivisa: un solo browser per TUTTE le richieste Subito.it.
Risolve il problema di anti-bot detection quando si aprono troppi browser distinti.
"""

PLAYWRIGHT_AVAILABLE = False
try:
    from playwright.sync_api import sync_playwright
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    pass


class PlaywrightSession:
    """Singleton browser session — aperta una volta, riusata da tutti gli scraper."""

    def __init__(self):
        self._pw = None
        self._browser = None
        self._context = None

    def start(self):
        if not PLAYWRIGHT_AVAILABLE:
            return False
        self._pw = sync_playwright().start()
        self._browser = self._pw.chromium.launch(
            headless=True,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
                "--no-sandbox",
            ],
        )
        self._context = self._browser.new_context(
            user_agent=(
                "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
                "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0 Safari/537.36"
            ),
            locale="it-IT",
            timezone_id="Europe/Rome",
            viewport={"width": 1366, "height": 900},
            extra_http_headers={
                "Accept-Language": "it-IT,it;q=0.9,en;q=0.8",
                "Sec-Ch-Ua-Platform": '"macOS"',
            },
        )
        self._context.add_init_script("""
            Object.defineProperty(navigator, 'webdriver', { get: () => undefined });
            Object.defineProperty(navigator, 'languages', { get: () => ['it-IT', 'it', 'en'] });
            Object.defineProperty(navigator, 'plugins', { get: () => [1, 2, 3, 4, 5] });
            window.chrome = { runtime: {} };
        """)
        return True

    def stop(self):
        try:
            if self._context: self._context.close()
            if self._browser: self._browser.close()
            if self._pw: self._pw.stop()
        except Exception:
            pass
        self._pw = self._browser = self._context = None

    def fetch(self, url, wait_selector=None, wait_timeout=20000):
        if self._context is None:
            self.start()
        page = self._context.new_page()
        try:
            page.goto(url, wait_until="domcontentloaded", timeout=60000)
            if wait_selector:
                try:
                    page.wait_for_selector(wait_selector, timeout=wait_timeout)
                except Exception:
                    pass
            return page.content()
        finally:
            page.close()


# Singleton globale
_session = None


def get_session():
    global _session
    if _session is None:
        _session = PlaywrightSession()
        _session.start()
    return _session


def close_session():
    global _session
    if _session is not None:
        _session.stop()
        _session = None
