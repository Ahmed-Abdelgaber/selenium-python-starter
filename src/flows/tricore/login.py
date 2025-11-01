from __future__ import annotations

from selenium.common.exceptions import TimeoutException
import time

from src.core.logger import get_logger
from src.pages.tricore.tricore_login_page import TricoreLoginPage


class TricoreLoginFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.tricore.login")

    def open_login_page(self) -> TricoreLoginPage:
        self.logger.info("Opening Tricore login page")
        page = TricoreLoginPage(self.driver).open()
        try:
            page.wait_visible(*page.LOGIN_BUTTON)
        except TimeoutException as exc:
            self.logger.exception("Timed out waiting for Tricore login page to load: %s", exc)
            raise
        self.logger.info("Tricore login page loaded")
        return page

    def login(self, username: str, password: str) -> TricoreLoginPage:
        page = self.open_login_page()

        self.logger.info("Submitting Tricore credentials for '%s'", username)
        page.login(username, password)

        try:
            if page.is_logged():
                self.logger.info("Tricore login successful for '%s'", username)
                time.sleep(5)  # wait for potential redirects after login
            else:
                self.logger.error("Tricore login status check returned False for '%s'", username)
                raise AssertionError("Tricore login validation failed")
        except Exception as exc:
            self.logger.exception("Tricore login failed for '%s': %s", username, exc)
            raise

        return page

    def close(self) -> None:
        self.logger.info("Closing Tricore driver")
        self.driver.quit()
