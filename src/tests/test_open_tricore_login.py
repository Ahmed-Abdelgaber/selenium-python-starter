import pytest

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.retry import RetryError
from src.scripts.tricore import RunTricore

USERNAME = "sneelagaru"
PASSWORD = "Menaul11311%"
FIRST_NAME = "Maria"
LAST_NAME = "Minjares"
DOB = "04/05/1954"
GENDER = "Female"
TOTAL_ITEMS = 80
PER_PAGE = 10


@pytest.mark.smoke
def test_open_tricore_login_page():
    config = load_config()
    driver = create_driver(config)
    try:
        RunTricore(
            driver,
            USERNAME,
            PASSWORD,
            FIRST_NAME,
            LAST_NAME,
            DOB,
            GENDER,
            per_page=PER_PAGE,
            total_items=TOTAL_ITEMS,
        )
    except RetryError as exc:
        pytest.fail(f"Tricore flow failed after retries: {exc.exceptions}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
