# src/core/driver_factory.py
from __future__ import annotations

import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options as ChromeOptions
from selenium.webdriver.firefox.options import Options as FirefoxOptions
from selenium.webdriver.edge.options import Options as EdgeOptions
from selenium.webdriver.remote.webdriver import WebDriver

from .config import Config


def _is_true(val: str | None) -> bool:
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}


def _chrome(cfg: Config) -> WebDriver:
    opts = ChromeOptions()

    # Faster: don't wait for every subresource (DOMContentLoaded is enough)
    opts.page_load_strategy = "eager"

    # Headless mode (allow opting into old headless if new is flaky in your env)
    if cfg.headless:
        if _is_true(os.getenv("HEADLESS_OLD")):
            opts.add_argument("--headless")       # classic headless
        else:
            opts.add_argument("--headless=new")   # default headless

    # Window & stability flags
    opts.add_argument(f"--window-size={cfg.window_width},{cfg.window_height}")
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")

    # CAS/SSO often needs 3rd-party cookies across redirects
    prefs = {
        "profile.block_third_party_cookies": False,
        "profile.default_content_setting_values.cookies": 1,
        "plugins.always_open_pdf_externally": True,
        "download.default_directory": cfg.download_quest_dir,
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    opts.add_experimental_option("prefs", prefs)

    # Optional (uncomment if a site is overly strict about automation flags)
    # opts.add_experimental_option("excludeSwitches", ["enable-automation"])
    # opts.add_experimental_option("useAutomationExtension", False)

    driver = webdriver.Chrome(options=opts)
    driver.set_page_load_timeout(cfg.page_load_timeout)
    driver.set_script_timeout(cfg.page_load_timeout)
    driver.delete_all_cookies()
    return driver


def _firefox(cfg: Config) -> WebDriver:
    opts = FirefoxOptions()
    opts.page_load_strategy = "eager"
    if cfg.headless:
        opts.add_argument("-headless")

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
