from __future__ import annotations

import re

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
        formatted_dob = self._format_mmddyyyy(dob)
        page.search_patient(first_name, last_name, formatted_dob, gender_value)
        self.logger.info("Tricore search completed")

    @staticmethod
    def _format_mmddyyyy(value: str) -> str:
        digits = re.sub(r"[^\d]", "", value or "")
        if len(digits) != 8:
            raise ValueError("Tricore DOB must contain 8 digits (MMDDYYYY)")

        month = int(digits[0:2])
        day = int(digits[2:4])
        year = int(digits[4:8])
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError("Tricore DOB must follow MMDDYYYY format")

        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"
