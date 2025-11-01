from __future__ import annotations

from src.core.logger import get_logger
from src.pages.quest.quest_logout_page import QuestLogoutPage
import time


class QuestLogoutFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.quest.logout")

    def logout(self) -> None:
        page = QuestLogoutPage(self.driver)
        self.logger.info("Initiating Quest logout sequence")
        try:
            page.logout()
            time.sleep(10)  # Wait for logout to complete
            self.logger.info("Quest logout completed successfully")
        except Exception as exc:
            self.logger.exception("Quest logout failed: %s", exc)
            raise
