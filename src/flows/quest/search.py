from __future__ import annotations

from src.core.logger import get_logger
from src.pages.quest.quest_search_page import QuestSearchPage


class QuestSearchFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.quest.search")

    def open_results_page(self) -> QuestSearchPage:
        self.logger.info("Opening Quest results page")
        page = QuestSearchPage(self.driver)
        page.open_results_page()
        page.is_loaded()
        self.logger.info("Quest results page loaded")
        return page

    def search_and_open(self, patient_name: str, patient_dob: str) -> QuestSearchPage:
        page = self.open_results_page()

        self.logger.info("Searching for patient '%s' with DOB '%s'", patient_name, patient_dob)
        page.search_patient(patient_name, patient_dob)

        try:
            if page.has_results():
                self.logger.info("Results found for patient '%s'", patient_name)
                self.logger.info("Opening first result for patient '%s'", patient_name)
                page.open_search_results()
                self.logger.info("Opened search result for patient '%s'", patient_name)
            else:
                self.logger.error("No results found for patient '%s'", patient_name)
                raise AssertionError("Quest search did not return results")
        except Exception as exc:
            self.logger.exception("Quest search flow failed for '%s': %s", patient_name, exc)
            raise

        return page

    def close(self) -> None:
        self.logger.info("Closing Quest driver")
        self.driver.quit()
