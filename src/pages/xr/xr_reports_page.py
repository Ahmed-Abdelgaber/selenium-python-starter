from __future__ import annotations

from typing import List, Optional

from selenium.webdriver.common.by import By
from selenium.webdriver.remote.webelement import WebElement
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.base_page import BasePage


class XrReportsPage(BasePage):
    LAST_NAME_INPUT = (By.ID, "tRptPLName")
    FIRST_NAME_INPUT = (By.ID, "tRptPFName")
    DOB_INPUT = (By.ID, "tRptPDOB")
    START_DATE_INPUT = (By.ID, "tRptStart")
    END_DATE_INPUT = (By.XPATH, "//input[@id='tRptEnd']")
    SEARCH_BUTTON = (By.ID, "btnRptAdvSrch")
    RESULTS_TABLE = (By.ID, "listRpt")
    ROWS = (By.CSS_SELECTOR, "#listRpt tr.jqgrow")
    VIEW_REPORT_BUTTON = (By.CSS_SELECTOR, "div.mip-report-btnB[title='View Report']")
    TITLE_SPAN = (By.CSS_SELECTOR, "span.Rpt-title")
    DOS_SPAN = (By.CSS_SELECTOR, "span.Rpt-date")
    SCREEN_BAR = (By.CSS_SELECTOR, "div.screenBar")
    PREVIEW_IFRAME = (By.CSS_SELECTOR, "iframe.screamframe")
    CLOSE_BUTTON = (By.CSS_SELECTOR, ".closeicon")

    def wait_until_loaded(self, timeout: int = 20) -> None:
        WebDriverWait(self.driver, timeout).until(EC.visibility_of_element_located(self.RESULTS_TABLE))

    def enter_last_name(self, value: str) -> None:
        self.type(*self.LAST_NAME_INPUT, value)

    def enter_first_name(self, value: str) -> None:
        self.type(*self.FIRST_NAME_INPUT, value)

    def enter_dob(self, value: str) -> None:
        self.type(*self.DOB_INPUT, value)

    def enter_start_date(self, value: str) -> None:
        self.type(*self.START_DATE_INPUT, value)

    def enter_end_date(self, value: str) -> None:
        self.type(*self.END_DATE_INPUT, value)

    def submit_search(self) -> None:
        self.click(*self.SEARCH_BUTTON)
        self.wait_until_loaded()

    def rows(self) -> List[WebElement]:
        return WebDriverWait(self.driver, 20).until(EC.presence_of_all_elements_located(self.ROWS))

    def get_title(self, row: WebElement) -> str:
        return row.find_element(*self.TITLE_SPAN).text.strip()

    def get_dos(self, row: WebElement) -> str:
        return row.find_element(*self.DOS_SPAN).text.strip()

    def open_row(self, row: WebElement) -> None:
        button = row.find_element(*self.VIEW_REPORT_BUTTON)
        self.driver.execute_script("arguments[0].scrollIntoView({block: 'center'});", button)
        button.click()

    def wait_for_preview(self) -> WebElement:
        WebDriverWait(self.driver, 20).until(EC.visibility_of_element_located(self.SCREEN_BAR))
        return WebDriverWait(self.driver, 20).until(EC.presence_of_element_located(self.PREVIEW_IFRAME))

    def close_preview(self) -> None:
        try:
            close_button = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.CLOSE_BUTTON))
            close_button.click()
            WebDriverWait(self.driver, 10).until(EC.invisibility_of_element_located(self.SCREEN_BAR))
        except Exception:
            pass
