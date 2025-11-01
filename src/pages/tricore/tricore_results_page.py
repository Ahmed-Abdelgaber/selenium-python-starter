from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class TricoreResultsPage(BasePage):
    NO_SEARCH_RESULTS_MESSAGE = (By.XPATH, "//td[contains(@class,'k-table-td')][normalize-space(string(.))='No records available.']")
    CHECKBOX = (By.XPATH, "(//tr[contains(@class,'k-master-row')][1]//input[@type='checkbox'])[1]")
    RESULTS_BUTTON = (By.XPATH, "//span[contains(@class,'mdc-button__label')]"
        "[normalize-space(string(.))='Results']/ancestor::button[1]")
    PAGE_SIZE_DROPDOWN = (By.CSS_SELECTOR, "kendo-dropdownlist[kendogridpagerdropdown]")
    PAGE_SIZE_40_OPTION = (By.XPATH, "//kendo-list[@id='k-list-1']//li[.//span[text()='40']]")
    ITEMS_NUMBER = (By.XPATH, "#resultGrid1 kendo-pager-info")
    NEXT_PAGE_BUTTON = (By.CSS_SELECTOR, "#resultGrid1 kendo-pager-next-buttons button[aria-label='Go to the next page']")
    SELECT_ALL_CHECKBOX = (By.XPATH, "//input[@id='selectAllCheckboxId4']")
    PRINT_ALL_DOWNLOAD_BUTTON = (By.CSS_SELECTOR, "#resultGrid1 button#printReport2")
    
    def has_results(self) -> bool:
        return not self.find(*self.NO_SEARCH_RESULTS_MESSAGE)
        
    def select_first_result(self):
        self.click(*self.CHECKBOX)
        self.click(*self.RESULTS_BUTTON)
        
    def set_page_size_to_40(self):
        self.click(*self.PAGE_SIZE_DROPDOWN)
        self.click(*self.PAGE_SIZE_40_OPTION)
        
    def get_items_number_text(self) -> str:
        return self.text_of(*self.ITEMS_NUMBER)
    
    def go_to_next_page(self):
        self.click(*self.NEXT_PAGE_BUTTON)
    
    def select_all_results(self):
        self.click(*self.SELECT_ALL_CHECKBOX)

    def download_selected_results(self):
        self.click(*self.PRINT_ALL_DOWNLOAD_BUTTON)
        
