from __future__ import annotations

import re
from pathlib import Path
from typing import List, Optional

from selenium.common.exceptions import TimeoutException

from src.core.config import load_config
from src.core.logger import get_logger
from src.core.pdf_download import (
    download_pdf_from_preview,
    rename_downloaded_file,
    sanitize_filename,
)
from src.pages.xr.xr_reports_page import XrReportsPage


class XrReportsFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.xr.reports")
        cfg = load_config()
        self.download_dir = Path(cfg.download_xr_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        self.page = XrReportsPage(self.driver)

    def search_reports(
        self,
        last_name: str,
        first_name: str,
        dob: Optional[str] = None,
        *,
        start_date: Optional[str] = None,
        end_date: Optional[str] = None,
    ) -> None:
        self.logger.info("Searching XR reports for %s, %s", last_name, first_name)
        self.page.enter_last_name(last_name)
        self.page.enter_first_name(first_name)
        if dob:
            try:
                normalized_dob = self._normalize_dob(dob)
                formatted_dob = f"{normalized_dob[0:2]}/{normalized_dob[2:4]}/{normalized_dob[4:8]}"
                self.page.enter_dob(formatted_dob)
            except Exception:
                self.logger.warning("Unable to set XR DOB; continuing")
        else:
            self.logger.info("No DOB provided; skipping DOB filter")
        if start_date:
            try:
                formatted_start = self._format_ddmmyyyy(start_date)
                self.page.enter_start_date(formatted_start)
            except Exception:
                self.logger.warning("Unable to set XR start date; continuing")
        if end_date:
            try:
                formatted_end = self._format_ddmmyyyy(end_date)
                self.page.enter_end_date(formatted_end)
            except Exception:
                self.logger.warning("Unable to set XR end date; continuing")
        self.page.submit_search()

    def download_reports(
        self,
        last_name: str,
        first_name: str,
        dob: Optional[str] = None,
    ) -> List[str]:
        collected: List[str] = []
        row_index = 0
        main_window = self.driver.current_window_handle
        if dob:
            normalized_dob = self._normalize_dob(dob)
            dob_month = normalized_dob[0:2]
            dob_day = normalized_dob[2:4]
            dob_year = normalized_dob[4:8]
            dob_label = f"{dob_month}/{dob_day}/{dob_year}"
        else:
            dob_label = "UNKNOWN"

        while True:
            rows = self.page.rows()
            if row_index >= len(rows):
                break

            row = rows[row_index]
            try:
                try:
                    title_text = self.page.get_title(row)
                    if not title_text:
                        raise ValueError("XR report title element returned empty text")
                except Exception as title_error:
                    raise RuntimeError(
                        f"Unable to read XR report title for row {row_index + 1}"
                    ) from title_error

                dos_text = self.page.get_dos(row)

                self.page.open_row(row)
                iframe = self.page.wait_for_preview()
                pdf_src = iframe.get_attribute("src") or ""
                if not pdf_src.startswith("http"):
                    pdf_src = f"https://portal.xraynm.com{pdf_src}"

                downloaded_path = download_pdf_from_preview(
                    self.driver,
                    pdf_src,
                    str(self.download_dir),
                    timeout=120,
                )
                if not downloaded_path:
                    raise TimeoutException("Download timed out")

                desired_name = sanitize_filename(
                    f"{title_text}_{last_name}_{first_name}_DOB_{dob_label}_DOS_{self._sanitize(dos_text)}.pdf"
                )
                final_path = rename_downloaded_file(
                    downloaded_path,
                    str(self.download_dir),
                    desired_name,
                    overwrite=False,
                    keep_extension=True,
                )
                collected.append(final_path)
                self.logger.info("Saved XR report to %s", Path(final_path).name)

                extra_handles = [handle for handle in self.driver.window_handles if handle != main_window]
                for handle in extra_handles:
                    self.driver.switch_to.window(handle)
                    self.driver.close()
                    self.logger.debug("finished download")

            except Exception as exc:
                screenshot = self.download_dir / f"xr_error_report_{row_index + 1}.png"
                try:
                    self.driver.save_screenshot(str(screenshot))
                except Exception:
                    self.logger.warning("Unable to capture XR screenshot", exc_info=True)
                self.logger.warning("Error processing XR report %d: %s", row_index + 1, exc)
            finally:
                try:
                    self.driver.switch_to.default_content()
                except Exception:
                    pass
                try:
                    self.page.close_preview()
                except Exception:
                    pass
                if row_index + 1 < len(rows):
                    self.driver.execute_script("window.scrollBy(0, 250);")
                row_index += 1

        if not collected:
            raise ValueError("No XR reports were downloaded")
        return collected

    @staticmethod
    def _normalize_dob(value: str) -> str:
        digits = re.sub(r"[^\d]", "", value)
        if len(digits) != 8:
            raise ValueError("DOB must include 8 digits (MMDDYYYY or YYYYMMDD)")
        month = digits[0:2]
        day = digits[2:4]
        year = digits[4:8]
        if int(month) > 12:
            year = digits[0:4]
            month = digits[4:6]
            day = digits[6:8]
        return f"{month}{day}{year}"

    @staticmethod
    def _format_ddmmyyyy(value: str) -> str:
        digits = re.sub(r"[^\d]", "", value or "")
        if len(digits) != 8:
            raise ValueError("Date filters must include 8 digits (DDMMYYYY)")

        day = int(digits[0:2])
        month = int(digits[2:4])
        year = int(digits[4:8])
        if not (1 <= day <= 31 and 1 <= month <= 12):
            raise ValueError("Date filters must follow DDMMYYYY format")

        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    @staticmethod
    def _format_mmddyyyy(value: str) -> str:
        digits = re.sub(r"[^\d]", "", value or "")
        if len(digits) != 8:
            raise ValueError("DOB must include 8 digits (MMDDYYYY)")

        month = int(digits[0:2])
        day = int(digits[2:4])
        year = int(digits[4:8])
        if not (1 <= month <= 12 and 1 <= day <= 31):
            raise ValueError("DOB must follow MMDDYYYY format")

        return f"{digits[0:2]}/{digits[2:4]}/{digits[4:8]}"

    @staticmethod
    def _sanitize(value: str) -> str:
        cleaned = re.sub(r"[^\dA-Za-z]+", "_", value.strip())
        return cleaned.strip("_") or "report"
