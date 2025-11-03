from __future__ import annotations

import time

from selenium.common.exceptions import TimeoutException

from src.core.logger import get_logger
from src.pages.zio.zio_login_page import ZioLoginPage


SESSION_LIMIT_RETRY_DELAY = 180
MAX_LOGIN_ATTEMPTS = 2


class ZioLoginFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.zio.login")

    def login(self, username: str, password: str) -> ZioLoginPage:
        attempt = 1
        while attempt <= MAX_LOGIN_ATTEMPTS:
            self.logger.info("Starting ZIO login attempt %d/%d", attempt, MAX_LOGIN_ATTEMPTS)
            page = ZioLoginPage(self.driver).open()

            self.logger.info("Submitting ZIO credentials for '%s'", username)
            page.enter_email(username)
            page.continue_to_password()
            page.enter_password(password)
            page.submit()

            if page.has_session_limit_error():
                self.logger.warning(
                    "ZIO session limit encountered; waiting %s seconds before retrying",
                    SESSION_LIMIT_RETRY_DELAY,
                )
                time.sleep(SESSION_LIMIT_RETRY_DELAY)
                attempt += 1
                continue

            if page.wait_for_dashboard_ready():
                self.logger.info("ZIO dashboard loaded successfully for '%s'", username)
                time.sleep(5)
                return page

            errors = page.get_error_messages()
            if errors:
                message = errors[0]
            else:
                message = "Unknown ZIO login failure"
            self.logger.warning("ZIO login attempt %d failed: %s", attempt, message)
            self._reset_session()
            attempt += 1

        raise TimeoutException("ZIO login failed after multiple attempts")

    def _reset_session(self) -> None:
        self.logger.info("Clearing ZIO browser session before retry")
        try:
            self.driver.delete_all_cookies()
        except Exception:
            self.logger.debug("Failed to delete cookies during ZIO reset", exc_info=True)
        try:
            self.driver.execute_script("window.sessionStorage.clear(); window.localStorage.clear();")
        except Exception:
            self.logger.debug("Failed to clear storage during ZIO reset", exc_info=True)
        time.sleep(2)
