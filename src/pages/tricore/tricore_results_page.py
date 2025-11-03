import time

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By

from src.core.base_page import BasePage


class TricoreResultsPage(BasePage):
    NO_SEARCH_RESULTS_MESSAGE = (By.XPATH, "//td[contains(@class,'k-table-td')][normalize-space(string(.))='No records available.']")
    CHECKBOX = (By.XPATH, "(//tr[contains(@class,'k-master-row')][1]//input[@type='checkbox'])[1]")
    RESULTS_BUTTON = (By.XPATH, "//span[contains(@class,'mdc-button__label')][normalize-space(string(.))='Results']/ancestor::button[1]")
    PAGE_SIZE_DROPDOWN = (By.CSS_SELECTOR, "kendo-dropdownlist[kendogridpagerdropdown]")
    PAGE_SIZE_40_OPTION = (By.XPATH, "//kendo-list[@id='k-list-1']//li[.//span[text()='40']]")
    ITEMS_NUMBER = (By.XPATH, "#resultGrid1 kendo-pager-info")
    NEXT_PAGE_BUTTON = (By.CSS_SELECTOR, "#resultGrid1 kendo-pager-next-buttons button[aria-label='Go to the next page']")
    SELECT_ALL_CHECKBOX = (By.XPATH, "//input[@id='selectAllCheckboxId4']")
    PRINT_ALL_DOWNLOAD_BUTTON = (By.XPATH, "//button[@id='printReport2']//span[@class='mat-mdc-button-touch-target']")
    LOADING_OVERLAY = (By.CSS_SELECTOR, "div.k-loading-image")
    
    def has_results(self) -> bool:
        return not self.find(*self.NO_SEARCH_RESULTS_MESSAGE)
        
    def select_first_result(self):
        self.click(*self.CHECKBOX)
        self.click(*self.RESULTS_BUTTON)
        self.wait_for_results_ready()
        time.sleep(5)
        
    def set_page_size_to_40(self):
        self.click(*self.PAGE_SIZE_DROPDOWN)
        self.click(*self.PAGE_SIZE_40_OPTION)

    def get_items_number_text(self) -> str:
        return self.text_of(*self.ITEMS_NUMBER)

    def wait_for_results_ready(self) -> None:
        try:
            self.wait.until(lambda drv: not drv.find_elements(*self.LOADING_OVERLAY))
        except TimeoutException:
            pass

    def go_to_next_page(self) -> bool:
        try:
            self.click(*self.NEXT_PAGE_BUTTON)
            self.wait_for_results_ready()
            return True
        except Exception:
            return False

    def select_all_results(self):
        self.wait_for_results_ready()
        time.sleep(2)
        self.click(*self.SELECT_ALL_CHECKBOX)

    def download_selected_results(self) -> str | None:
        existing_handles = set(self.driver.window_handles)
        self.click(*self.PRINT_ALL_DOWNLOAD_BUTTON)
        try:
            self.wait.until(lambda drv: len(drv.window_handles) > len(existing_handles))
        except TimeoutException:
            return None

        new_handles = [handle for handle in self.driver.window_handles if handle not in existing_handles]
        return new_handles[-1] if new_handles else None
        
