import pytest

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.retry import RetryError
from src.scripts.quest import RunQuest

USERNAME = "sneelagaru"
PASSWORD = "Menaul11311$$"
PATIENT_NAME = "Maria Minjares"
PATIENT_DOB = "04/05/1954"


@pytest.mark.smoke
def test_open_quest_cas_login_page():
    config = load_config()
    driver = create_driver(config)
    try:
        RunQuest(driver, USERNAME, PASSWORD, PATIENT_NAME, PATIENT_DOB)
    except RetryError as exc:
        pytest.fail(f"Quest flow failed after retries: {exc.exceptions}")
    finally:
        try:
            driver.quit()
        except Exception:
            pass
    
