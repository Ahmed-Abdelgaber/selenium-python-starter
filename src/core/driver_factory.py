# src/core/driver_factory.py
from __future__ import annotations

import os
from pathlib import Path
import time
import subprocess
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver

from .config import Config
from .logger import get_logger
from typing import Optional
LOGGER = get_logger("driver")


def _is_true(val: str | None) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _chrome(cfg: Config) -> WebDriver:
    opts = ChromeOptions()

    tmp_base = Path(os.getenv("CHROME_TMP_BASE", "/tmp/chrome"))
    (tmp_base / "data-path").mkdir(parents=True, exist_ok=True)
    (tmp_base / "cache").mkdir(parents=True, exist_ok=True)
    (tmp_base / "user-data").mkdir(parents=True, exist_ok=True)

    # Faster: don't wait for every subresource (DOMContentLoaded is enough)
    opts.page_load_strategy = "eager"

    if cfg.incognito:
        opts.add_argument("--incognito")

    # Headless mode (allow opting into old headless if new is flaky in your env)
    if cfg.headless:
        if _is_true(os.getenv("HEADLESS_OLD")):
            opts.add_argument("--headless")       # classic headless
        else:
            opts.add_argument("--headless=new")   # default headless
        LOGGER.info("Headless mode: %s", "classic --headless" if _is_true(os.getenv("HEADLESS_OLD")) else "new --headless=new")

    flags = [
        f"--window-size={cfg.window_width},{cfg.window_height}",
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--no-first-run",
        "--no-default-browser-check",
        "--disable-extensions",
        "--disable-background-networking",
        "--metrics-recording-only",
        "--mute-audio",
        "--hide-scrollbars",
        "--disable-software-rasterizer",
        "--use-gl=swiftshader",
        "--ignore-gpu-blocklist",
        "--no-zygote",
        "--enable-features=NetworkService,NetworkServiceInProcess",
        f"--user-data-dir={str((tmp_base / 'user-data').resolve())}",
        f"--data-path={str((tmp_base / 'data-path').resolve())}",
        f"--disk-cache-dir={str((tmp_base / 'cache').resolve())}",
        "--disable-features=VizDisplayCompositor",
        "--disable-crash-reporter",
        "--remote-debugging-pipe",
    ]
    for f in flags:
        opts.add_argument(f)

    # Resolve a download directory (fallback to quest dir to keep current behavior)
    download_dir = getattr(cfg, "download_dir", None) or cfg.download_quest_dir
    try:
        Path(download_dir).mkdir(parents=True, exist_ok=True)
    except Exception:
        LOGGER.warning("Could not create download dir %s; using /tmp/downloads", download_dir, exc_info=True)
        download_dir = "/tmp/downloads"
        Path(download_dir).mkdir(parents=True, exist_ok=True)

    prefs = {
        "profile.block_third_party_cookies": False,
        "profile.default_content_setting_values.cookies": 1,
        "plugins.always_open_pdf_externally": True,
        "download.default_directory": str(Path(download_dir).resolve()),
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    opts.add_experimental_option("prefs", prefs)

    # Optional (uncomment if a site is overly strict about automation flags)
    # opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    # opts.add_experimental_option("useAutomationExtension", False)

    binary_path = os.getenv("CHROME_BIN")
    # Probe versions to catch mismatch early (configurable/optional)
    probe_env = os.getenv("CHROME_PROBE_TIMEOUT", "5").strip()
    try:
        probe_timeout = max(0, int(probe_env))
    except Exception:
        probe_timeout = 5

    try:
        if probe_timeout > 0:
            if binary_path and Path(binary_path).exists():
                out = subprocess.run([binary_path, "--version"], capture_output=True, text=True, timeout=probe_timeout)
                LOGGER.info("Chromium version: %s", (out.stdout or out.stderr).strip())
            drv_probe_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
            if drv_probe_path and Path(drv_probe_path).exists():
                out = subprocess.run([drv_probe_path, "--version"], capture_output=True, text=True, timeout=probe_timeout)
                LOGGER.info("Chromedriver version: %s", (out.stdout or out.stderr).strip())
        else:
            LOGGER.info("Skipping Chrome/Driver version probe (CHROME_PROBE_TIMEOUT=%s)", probe_env)
    except subprocess.TimeoutExpired:
        LOGGER.warning("Chrome/Driver version probe timed out after %ss; continuing", probe_timeout)
    except Exception:
        LOGGER.warning("Could not probe Chrome/Driver versions", exc_info=True)

    if binary_path and Path(binary_path).exists():
        opts.binary_location = binary_path
        LOGGER.info("Using Chromium binary at %s", binary_path)

    driver_kwargs: dict[str, object] = {"options": opts}
    driver_path = os.getenv("CHROMEDRIVER_PATH", "/usr/bin/chromedriver")
    service_log = str((tmp_base / "chromedriver.log").resolve())
    if driver_path and Path(driver_path).exists():
        LOGGER.info("Using chromedriver at %s", driver_path)
        driver_kwargs["service"] = ChromeService(executable_path=driver_path, log_output=service_log)
    else:
        LOGGER.info("CHROMEDRIVER_PATH not set or not found at %s; letting Selenium resolve driver", driver_path)

    try:
        driver = webdriver.Chrome(**driver_kwargs)
    except Exception as e:
        LOGGER.error("Failed to start Chrome WebDriver. CHROME_BIN=%s CHROMEDRIVER_PATH=%s", binary_path, driver_path, exc_info=True)
        # One fallback attempt: drop explicit service to allow Selenium to resolve a compatible driver
        try:
            env_disable = os.environ.get("SELENIUM_MANAGER_DISABLE")
            if env_disable == "1":
                LOGGER.info("Temporarily enabling Selenium Manager for fallback driver resolution")
                os.environ["SELENIUM_MANAGER_DISABLE"] = "0"
            driver = webdriver.Chrome(options=opts)
            LOGGER.info("Started Chrome with Selenium Manager fallback")
        except Exception:
            # restore env if we modified it
            if os.environ.get("SELENIUM_MANAGER_DISABLE") == "0":
                os.environ["SELENIUM_MANAGER_DISABLE"] = "1"
            # Log chromedriver service log tail for easier debugging
            try:
                tail = ""
                with open(service_log, "r") as f:
                    tail = f.read()[-4000:]
                if tail:
                    LOGGER.error("Chromedriver log tail:\n%s", tail)
            except Exception:
                pass
            raise
        else:
            # restore env if we modified it
            if os.environ.get("SELENIUM_MANAGER_DISABLE") == "0":
                os.environ["SELENIUM_MANAGER_DISABLE"] = "1"
    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.set_script_timeout(cfg.page_load_timeout)
    time.sleep(1)
    return driver


def _firefox(cfg: Config) -> WebDriver:
    opts = FirefoxOptions()
    opts.page_load_strategy = "eager"
    if cfg.headless:
        opts.add_argument("-headless")
    if cfg.incognito:
        opts.add_argument("-private")

    # Allow all cookies (0 = accept all)
    opts.set_preference("network.cookie.cookieBehavior", 0)
    # Reduce tab process occlusion issues in some WMs (optional)
    # opts.set_preference("browser.tabs.remote.autostart", True)

    driver = webdriver.Firefox(options=opts)
    driver.set_window_size(cfg.window_width, cfg.window_height)
    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.set_script_timeout(cfg.page_load_timeout)
    driver.delete_all_cookies()
    return driver


def _edge(cfg: Config) -> WebDriver:
    opts = EdgeOptions()
    opts.page_load_strategy = "eager"
    if cfg.headless:
        opts.add_argument("--headless=new")
    if cfg.incognito:
        opts.add_argument("--inprivate")
    opts.add_argument(f"--window-size={cfg.window_width},{cfg.window_height}")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")

    # Similar cookie prefs as Chrome (Edge is Chromium-based)
    try:
        opts.add_experimental_option("prefs", {
            "profile.block_third_party_cookies": False,
            "profile.default_content_setting_values.cookies": 1,
        })
    except Exception:
        pass  # older Selenium/Edge may not support experimental options

    driver = webdriver.Edge(options=opts)
    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.set_script_timeout(cfg.page_load_timeout)
    driver.delete_all_cookies()
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

    return driver
