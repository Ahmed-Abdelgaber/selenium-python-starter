from __future__ import annotations

import logging
import time
from typing import List

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.base_page import BasePage


LOGGER = logging.getLogger(__name__)


class ZioReportsPage(BasePage):
    REPORTS_TAB = (By.XPATH, "//span[text()='Reports']")
    POSTED_FINAL_LINK = (By.XPATH, "//a[contains(text(), 'Posted Final')]")
    TABLE_BODY = (By.XPATH, "//tbody[contains(@class, 'ng-star-inserted')]")
    TABLE_ROWS = (By.XPATH, ".//tr[.//td]")
    SEARCH_INPUT = (By.XPATH, "//input[@id='table-keywords']")
    SEARCH_SUBMIT = (
        By.XPATH,
        "//form[contains(@class, 'search-box')]//button[@type='submit']",
    )
    DOWNLOAD_BUTTON = (
        By.XPATH,
        "//button[contains(@class,'download-btn') and normalize-space()='Download']",
    )
    ROW_CHECKBOX = (
        By.XPATH,
        ".//span[@class='checkbox-custom rectangular']",
    )
    ROW_CHECKBOX_FALLBACK = (
        By.XPATH,
        ".//span[contains(@class,'checkbox-custom') and contains(@class,'rectangular')]",
    )
    PATIENT_CELL = (By.CLASS_NAME, "col-patient")
    PATIENT_ANCHOR = (By.TAG_NAME, "a")
    PATIENT_DOB = (By.CLASS_NAME, "tr-subtext")
    REPORT_TYPE_CELL = (By.CLASS_NAME, "col-report-type")
    LOADING_OVERLAY = (By.CSS_SELECTOR, "div.k-loading-image")

    def open_reports_section(self) -> None:
        self.click(*self.REPORTS_TAB)
        self.click(*self.POSTED_FINAL_LINK)
        self.wait_for_loading()
        self.wait_until_ready()

    def apply_name_filter(self, full_name: str) -> None:
        self.wait_for_loading()
        LOGGER.debug("Applying ZIO name filter for '%s'", full_name)
        self.wait_until_ready()
        search_input = WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(self.SEARCH_INPUT)
        )
        search_input.clear()
        search_input.send_keys(full_name)
        search_input.send_keys(Keys.ENTER)
        LOGGER.debug("Submitting ZIO name filter for '%s'", full_name)
        try:
            button = WebDriverWait(self.driver, 10).until(
                EC.element_to_be_clickable(self.SEARCH_SUBMIT)
            )
        except TimeoutException:
            LOGGER.debug("Default submit button not clickable; attempting legacy locator")
            legacy_path = (
                "//form[contains(@class, 'search-box')]//button[@type='submit']"
                "//*[name()='svg']//*[name()='path' and contains(@d,'M10.4517 1')]"
            )
            svg_path = WebDriverWait(self.driver, 10).until(
                EC.presence_of_element_located((By.XPATH, legacy_path))
            )
            button = svg_path.find_element(By.XPATH, "ancestor::button[1]")
        try:
            button.click()
        except Exception:
            LOGGER.debug("Falling back to JS click for ZIO search submit")
            self.driver.execute_script("arguments[0].click();", button)
        time.sleep(2)
        LOGGER.debug("Waiting for ZIO results table to refresh")
        self.wait_for_loading()
        self.wait_for_results()

    def wait_until_ready(self, timeout: int = 20) -> None:
        WebDriverWait(self.driver, timeout).until(EC.element_to_be_clickable(self.SEARCH_INPUT))

    def wait_for_loading(self, timeout: int = 20) -> None:
        WebDriverWait(self.driver, timeout).until(
            lambda drv: not drv.find_elements(*self.LOADING_OVERLAY)
        )

    def wait_for_results(self, timeout: int = 20) -> None:
        WebDriverWait(self.driver, timeout).until(lambda _: self._has_rows())

    def _has_rows(self) -> bool:
        try:
            tbody = self.find(*self.TABLE_BODY)
        except TimeoutException:
            return False
        return bool(tbody.find_elements(*self.TABLE_ROWS))

    def rows(self) -> List[WebElement]:
        tbody = self.find(*self.TABLE_BODY)
        return tbody.find_elements(*self.TABLE_ROWS)

    def get_row_checkbox(self, row: WebElement) -> WebElement:
        try:
            return row.find_element(*self.ROW_CHECKBOX)
        except Exception:
            return row.find_element(*self.ROW_CHECKBOX_FALLBACK)

    def get_patient_cell(self, row: WebElement) -> WebElement:
        return row.find_element(*self.PATIENT_CELL)

    def get_patient_name(self, row: WebElement) -> str:
        patient = self.get_patient_cell(row).find_element(*self.PATIENT_ANCHOR)
        return patient.text.strip()

    def get_patient_dob(self, row: WebElement) -> str:
        return self.get_patient_cell(row).find_element(*self.PATIENT_DOB).text.strip()

    def get_report_type(self, row: WebElement) -> str:
        return row.find_element(*self.REPORT_TYPE_CELL).text.strip()

    def get_download_button(self) -> WebElement:
        return WebDriverWait(self.driver, 20).until(
            EC.element_to_be_clickable(self.DOWNLOAD_BUTTON)
        )

    def scroll_into_view(self, element: WebElement) -> None:
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", element)
        time.sleep(0.5)
