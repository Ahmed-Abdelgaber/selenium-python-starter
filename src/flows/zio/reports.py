from __future__ import annotations

import re
import time
from pathlib import Path
from typing import Iterable, List, Optional

import fitz  # PyMuPDF
from selenium.common.exceptions import TimeoutException

from src.core.config import load_config
from src.core.logger import get_logger
from src.core.pdf_download import (
    allow_downloads_cdp,
    rename_downloaded_file,
    sanitize_filename,
    snapshot_downloads,
    wait_for_new_download,
)
from src.pages.zio.zio_reports_page import ZioReportsPage


DOWNLOAD_TIMEOUT = 120


class ZioReportsFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.zio.reports")
        cfg = load_config()
        self.download_dir = Path(cfg.download_zio_dir)
        self.download_dir.mkdir(parents=True, exist_ok=True)
        allow_downloads_cdp(self.driver, str(self.download_dir))
        self.page = ZioReportsPage(self.driver)

    def open_reports(self) -> None:
        self.logger.info("Navigating to ZIO reports section")
        self.page.open_reports_section()
        time.sleep(3)
        self.page.wait_for_results()

    def apply_name_filter(self, first_name: Optional[str], last_name: Optional[str]) -> Optional[List[str]]:
        if not first_name and not last_name:
            self.logger.info("No patient name provided; processing all available reports")
            return None

        parts = [part.strip() for part in (first_name or "", last_name or "") if part and part.strip()]
        full_name = " ".join(parts)
        if not full_name:
            self.logger.info("Computed patient name is empty after trimming; skipping name filter")
            return None

        self.logger.info("Applying ZIO patient filter for '%s'", full_name)
        self.page.apply_name_filter(full_name)
        self.page.wait_for_loading()
        time.sleep(1)
        tokens = [token.upper() for token in re.split(r"\s+", full_name) if token]
        return tokens or None

    def download_reports(
        self,
        *,
        target_tokens: Optional[Iterable[str]] = None,
        max_reports: Optional[int] = None,
    ) -> List[str]:
        processed: List[str] = []
        index = 0

        self.page.wait_for_results()

        while True:
            if max_reports is not None and index >= max_reports:
                break

            rows = self.page.rows()
            if index >= len(rows):
                break

            row = rows[index]
            row_checkbox = None

            try:
                patient_name = self.page.get_patient_name(row)
                patient_dob = self.page.get_patient_dob(row)
                report_type = self.page.get_report_type(row)

                normalized_name = self._normalize_name(patient_name)
                if target_tokens and not all(token in normalized_name for token in target_tokens):
                    index += 1
                    continue

                row_checkbox = self.page.get_row_checkbox(row)
                self.page.scroll_into_view(row_checkbox)
                time.sleep(1.0)

                before_snapshot = snapshot_downloads(str(self.download_dir))
                row_checkbox.click()
                time.sleep(1.5)


                download_button = self.page.get_download_button()
                try:
                    download_button.click()
                except Exception:
                    self.driver.execute_script("arguments[0].click();", download_button)

                new_pdf_path = wait_for_new_download(
                    str(self.download_dir), before_snapshot, timeout=DOWNLOAD_TIMEOUT
                )
                if not new_pdf_path:
                    raise TimeoutException("Timed out waiting for ZIO report download")

                dos_start, _ = self._extract_dos(Path(new_pdf_path))
                dos_clean = dos_start.split(",")[0]

                desired_name = sanitize_filename(
                    f"{report_type}_{patient_name.replace(',', '_')}_DOB_{patient_dob}_DOS_{dos_clean}.pdf"
                )
                final_path = Path(
                    rename_downloaded_file(
                        new_pdf_path,
                        str(self.download_dir),
                        desired_name,
                        overwrite=False,
                        keep_extension=True,
                    )
                )
                processed.append(str(final_path))
                self.logger.info("Downloaded ZIO report '%s'", final_path.name)

            except Exception as exc:
                screenshot_path = self.download_dir / f"zio_error_row_{index + 1}.png"
                try:
                    self.driver.save_screenshot(str(screenshot_path))
                    self.logger.error("Captured screenshot for failed row: %s", screenshot_path)
                except Exception:
                    self.logger.warning("Unable to capture screenshot for failed ZIO row", exc_info=True)
                raise RuntimeError(f"Failed to process ZIO row {index + 1}: {exc}") from exc
            finally:
                if row_checkbox:
                    try:
                        row_checkbox.click()
                    except Exception:
                        pass
                index += 1

        if not processed:
            raise ValueError("No matching ZIO reports were downloaded")
        return processed

    @staticmethod
    def _normalize_name(value: str) -> str:
        cleaned = value.replace(",", " ").replace("_", " ").strip().upper()
        cleaned = re.sub(r"\s+", " ", cleaned)
        return cleaned

    @staticmethod
    def _extract_dos(pdf_path: Path) -> tuple[str, str]:
        with fitz.open(pdf_path) as pdf:
            text = "".join(page.get_text() for page in pdf)
        match = re.search(
            r"Enrollment Period\s*([\d/]{8},\s*\d{1,2}:\d{2}[ap]m)\s*to\s*([\d/]{8},\s*\d{1,2}:\d{2}[ap]m)",
            text,
            re.IGNORECASE,
        )
        if not match:
            raise ValueError("DOS not found in the PDF")
        return match.group(1), match.group(2)
