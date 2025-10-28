from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class PythonHomePage(BasePage):
    SEARCH_INPUT = (By.ID, "id-search-field")
    SEARCH_BTN = (By.ID, "submit")

    def open(self) -> "PythonHomePage":
        return self.go_to("https://www.python.org/")

    def search(self, term: str):
        self.type(*self.SEARCH_INPUT, text=term)
        self.click(*self.SEARCH_BTN)
        from .python_search_results_page import PythonSearchResultsPage
        return PythonSearchResultsPage(self.driver, self.wait._timeout)  # reuse timeout
