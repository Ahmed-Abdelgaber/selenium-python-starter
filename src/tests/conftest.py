import os
import pathlib
import pytest
from datetime import datetime

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger

ARTIFACTS_DIR = pathlib.Path("artifacts")
SCREENSHOTS_DIR = ARTIFACTS_DIR / "screenshots"
LOG = get_logger("conftest")

def pytest_addoption(parser: pytest.Parser) -> None:
    parser.addoption("--browser", action="store", default=None, help="Browser: chrome|firefox|edge")
    parser.addoption("--headless", action="store", default=None, help="Headless: true|false")
    parser.addoption("--base-url", action="store", default=None, help="Override BASE_URL for tests")
    parser.addoption("--window-width", action="store", default=None, type=int)
    parser.addoption("--window-height", action="store", default=None, type=int)

@pytest.fixture(scope="session", autouse=True)
def _prepare_artifacts() -> None:
    SCREENSHOTS_DIR.mkdir(parents=True, exist_ok=True)
    (pathlib.Path("reports")).mkdir(parents=True, exist_ok=True)

@pytest.fixture(scope="session")
def config(pytestconfig) :
    cli_overrides = {
        "browser": pytestconfig.getoption("--browser"),
        "headless": pytestconfig.getoption("--headless"),
        "base_url": pytestconfig.getoption("--base-url"),
        "window_width": pytestconfig.getoption("--window-width"),
        "window_height": pytestconfig.getoption("--window-height"),
    }
    # Normalize booleans passed via CLI
    if isinstance(cli_overrides.get("headless"), str):
        cli_overrides["headless"] = str(cli_overrides["headless"]).lower() in {"1","true","yes","y","on"}
    return load_config(cli_overrides)

@pytest.fixture()
def driver(config):
    driver = create_driver(config)
    yield driver
    driver.quit()

@pytest.hookimpl(hookwrapper=True, tryfirst=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    rep = outcome.get_result()

    if rep.when == "call" and rep.failed and "driver" in item.fixturenames:
        drv = item.funcargs.get("driver")
        if drv:
            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = SCREENSHOTS_DIR / f"{item.name}_{timestamp}.png"
            try:
                drv.save_screenshot(str(filename))
                LOG.error("Saved screenshot to %s", filename)
                # Attach to pytest-html if available
                extra = getattr(rep, "extra", [])
                try:
                    from pytest_html import extras
                    extra.append(extras.image(str(filename)))
                    rep.extra = extra
                except Exception:
                    pass
            except Exception as e:
                LOG.error("Failed to capture screenshot: %s", e)
