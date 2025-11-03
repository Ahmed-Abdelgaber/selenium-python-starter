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

        self.logger.info("Switching to Quest portal window")
        page.switch_to_portal_window()
        if page.wait_for_portal_navigation():
            self.logger.info("Quest portal loaded for '%s'", username)
        else:
            self.logger.warning("Quest portal navigation not detected for '%s'", username)

        self.logger.info("Quest CAS login flow completed for '%s'", username)

        return page

    def close(self) -> None:
        self.logger.info("Closing Quest driver")
        self.driver.quit()
