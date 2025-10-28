from __future__ import annotations

from src.core.logger import get_logger
from src.pages.quest.quest_login_page import QuestCasLoginPage


class QuestLoginFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.quest.login")

    def open_login_page(self) -> QuestCasLoginPage:
        self.logger.info("Opening Quest CAS login page")
        page = QuestCasLoginPage(self.driver).open()
        page.is_loaded()
        self.logger.info("Quest CAS login page loaded")
        return page

    def login(self, username: str, password: str) -> QuestCasLoginPage:
        page = self.open_login_page()

        self.logger.info("Submitting Quest CAS credentials for '%s'", username)
        page.login(username, password)

        try:
            if page.is_logged():
                self.logger.info("Quest CAS login successful for '%s'", username)
            else:
                self.logger.error("Quest CAS login status check returned False for '%s'", username)
                raise AssertionError("Quest CAS login validation failed")
        except Exception as exc:
            self.logger.exception("Quest CAS login failed for '%s': %s", username, exc)
            raise

        return page

    def close(self) -> None:
        self.logger.info("Closing Quest driver")
        self.driver.quit()
