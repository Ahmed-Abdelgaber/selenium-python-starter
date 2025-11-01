from __future__ import annotations

import math
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
    ) -> TricoreResultsPage:
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

        results_page = TricoreResultsPage(self.driver)
        try:
            results_page.wait_visible(*results_page.RESULTS_BUTTON)
        except TimeoutException as exc:
            self.logger.exception("Timed out waiting for Tricore results grid: %s", exc)
            raise
        self.logger.info("Tricore results grid loaded")
        return results_page

    def search_and_download(
        self,
        first_name: str,
        last_name: str,
        dob: str,
        gender: str,
        *,
        per_page: int = 10,
        total_items: int | None = None,
    ) -> TricoreResultsPage:
        results_page = self.search_patient(first_name, last_name, dob, gender)

        try:
            has_results = results_page.has_results()
        except TimeoutException:
            has_results = True

        if not has_results:
            self.logger.error("No Tricore results found for patient '%s %s'", first_name, last_name)
            raise AssertionError("Tricore search did not return results")

        self.logger.info("Selecting first Tricore result")
        results_page.select_first_result()

        if total_items is None:
            try:
                items_text = results_page.get_items_number_text()
                self.logger.info("Tricore items summary: '%s'", items_text)
                match = re.search(r"\bof\s+(\d{1,3}(?:,\d{3})*)\s+items?\b", items_text)
                if match:
                    total_items = int(match.group(1).replace(",", ""))
            except Exception as exc:
                self.logger.warning("Unable to determine total Tricore items: %s", exc)

        if not total_items:
            total_items = per_page

        loops = max(1, math.ceil(total_items / per_page))

        for page_index in range(loops):
            self.logger.info(
                "Selecting Tricore results on page %d of %d", page_index + 1, loops
            )
            results_page.select_all_results()
            if page_index < loops - 1:
                self.logger.info("Moving to next Tricore results page")
                results_page.go_to_next_page()

        self.logger.info("Downloading selected Tricore results")
        results_page.download_selected_results()
        return results_page

    def close(self) -> None:
        self.logger.info("Closing Tricore driver")
        self.driver.quit()
