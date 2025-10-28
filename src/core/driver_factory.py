from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver

from .config import Config

def _chrome(cfg: Config) -> WebDriver:
    opts = ChromeOptions()
    if cfg.headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--window-size={cfg.window_width},{cfg.window_height}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    driver = webdriver.Chrome(options=opts)
    return driver

def _firefox(cfg: Config) -> WebDriver:
    opts = FirefoxOptions()
    if cfg.headless:
        opts.add_argument("-headless")
    driver = webdriver.Firefox(options=opts)
    driver.set_window_size(cfg.window_width, cfg.window_height)
    return driver

def _edge(cfg: Config) -> WebDriver:
    opts = EdgeOptions()
    if cfg.headless:
        opts.add_argument("--headless=new")
    opts.add_argument(f"--window-size={cfg.window_width},{cfg.window_height}")
    driver = webdriver.Edge(options=opts)
    return driver

def create_driver(cfg: Config) -> WebDriver:
    browser = (cfg.browser or "chrome").strip().lower()
    if browser in ("chrome", "chromium"):
        driver = _chrome(cfg)
    elif browser in ("firefox", "ff"):
        driver = _firefox(cfg)
    elif browser in ("edge", "msedge"):
        driver = _edge(cfg)
    else:
        raise ValueError(f"Unsupported browser: {cfg.browser}")

    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.delete_all_cookies()
    return driver
