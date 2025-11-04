from __future__ import annotations

import re
import time
from datetime import datetime

from src.core.config import load_config
from src.core.logger import get_logger
from src.core.pdf_download import (
    allow_downloads_cdp,
    clean_download_dir,
    rename_downloaded_file,
    snapshot_downloads,
    wait_for_new_download,
)
from src.pages.tricore.tricore_results_page import TricoreResultsPage


class TricoreResultsFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.tricore.results")
        self.download_dir = load_config().download_tricore_dir

    def search_and_download(
        self,
        per_page: int = 10,
        total_items: int | None = None,
        *,
        patient_name: str,
        report_date: str | None = None,
    ) -> list[str]:
        self.logger.info("Selecting first Tricore result")
        results_page = TricoreResultsPage(self.driver)
        time.sleep(10)
        results_page.select_first_result()
        time.sleep(15)

        self.logger.info("Preparing Tricore download directory")
        allow_downloads_cdp(self.driver, self.download_dir)
        clean_download_dir(self.download_dir, only_extensions=(".pdf",))

        last_handle = self.driver.current_window_handle

        downloaded_files: list[str] = []
        normalized_patient = self._normalize_patient_name(patient_name)
        date_segment = self._normalize_report_date(report_date)
        total_index = 0

        page_index = 0
        while True:
            page_index += 1
            self.logger.info("Selecting Tricore results on page %d", page_index)
            results_page.select_all_results()
            time.sleep(3)

            before_files = snapshot_downloads(self.download_dir)
            pdf_handle = results_page.download_selected_results()
            downloaded_path = wait_for_new_download(
                self.download_dir, before_files, timeout=120
            )

            if pdf_handle:
                try:
                    self.driver.switch_to.window(pdf_handle)
                    time.sleep(3)
                finally:
                    try:
                        self.driver.close()
                    except Exception:
                        pass
                    try:
                        self.driver.switch_to.window(last_handle)
                    except Exception:
                        pass

            if not downloaded_path:
                self.logger.warning(
                    "Timed out waiting for Tricore PDF download on page %d",
                    page_index + 1,
                )
            else:
                total_index += 1
                target_name = f"tricore_{normalized_patient}_{date_segment}-{total_index}.pdf"
                final_path = rename_downloaded_file(
                    downloaded_path,
                    self.download_dir,
                    target_name,
                    overwrite=False,
                    keep_extension=True,
                )
                downloaded_files.append(final_path)
                self.logger.info(
                    "Tricore PDF for page %d saved to '%s'",
                    page_index + 1,
                    final_path,
                )

            if results_page.go_to_next_page():
                self.logger.info("Moving to next Tricore results page")
                time.sleep(5)
                last_handle = self.driver.current_window_handle
            else:
                self.logger.info("Reached last Tricore results page")
                break

        if not downloaded_files:
            raise TimeoutError("No Tricore PDFs were downloaded during the flow")

        return downloaded_files

    @staticmethod
    def _normalize_patient_name(value: str) -> str:
        cleaned = re.sub(r"[^A-Za-z0-9]+", "-", value or "")
        cleaned = cleaned.strip("-")
        return cleaned or "patient"

    @staticmethod
    def _normalize_report_date(value: str | None) -> str:
        if value:
            digits = re.sub(r"[^0-9]", "", value)
            if len(digits) >= 8:
                return digits[:8]
            if digits:
                return digits
        return datetime.utcnow().strftime("%Y%m%d")
