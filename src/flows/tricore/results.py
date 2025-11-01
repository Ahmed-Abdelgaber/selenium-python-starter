from __future__ import annotations

import math
import re
import time

from src.core.logger import get_logger
from src.pages.tricore.tricore_results_page import TricoreResultsPage

class TricoreResultsFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.tricore.results")

        
    def search_and_download(self, per_page: int = 10, total_items: int | None = None) -> TricoreResultsPage:
        self.logger.info("Selecting first Tricore result")
        results_page = TricoreResultsPage(self.driver)
        time.sleep(10)
        results_page.select_first_result()
        time.sleep(15)

    #   items_text = results_page.get_items_number_text()
        items_text = '1-10 of 80 items'  # Temporary fix for getting items number text
        self.logger.info("Tricore items summary: '%s'", items_text)
        match = re.search(r"\bof\s+(\d{1,3}(?:,\d{3})*)\s+items?\b", items_text)
        if match:
            total_items = int(match.group(1).replace(",", ""))

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
