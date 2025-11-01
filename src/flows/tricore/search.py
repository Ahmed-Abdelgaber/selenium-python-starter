from __future__ import annotations

from selenium.common.exceptions import TimeoutException

from src.core.logger import get_logger
from src.pages.tricore.tricore_results_page import TricoreResultsPage
from src.pages.tricore.tricore_search_page import TricoreSearchPage


class TricoreSearchFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.tricore.search")

    def open_search_page(self) -> TricoreSearchPage:
        self.logger.info("Opening Tricore patient search")
        page = TricoreSearchPage(self.driver)
        page.open_search_patient()
        try:
            page.wait_visible(*page.FIRST_NAME)
        except TimeoutException as exc:
            self.logger.exception("Timed out waiting for Tricore search form to load: %s", exc)
            raise
        self.logger.info("Tricore patient search form loaded")
        return page

    def search_patient(
        self,
        first_name: str,
        last_name: str,
        dob: str,
        gender: str,
    ):
        page = self.open_search_page()

        gender_value = (gender or "").strip().lower()
        self.logger.info(
            "Searching Tricore for patient '%s %s' DOB '%s' gender '%s'",
            first_name,
            last_name,
            dob,
            gender_value or "unspecified",
        )
        page.search_patient(first_name, last_name, dob, gender_value)
        self.logger.info("Tricore search completed")

