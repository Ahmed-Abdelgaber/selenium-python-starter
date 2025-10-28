from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class PythonSearchResultsPage(BasePage):
    RESULTS = (By.CSS_SELECTOR, "ul.list-recent-events li, ul.list-recent-posts li, ul.list-recent-events.menu li")

    def has_results(self) -> bool:
        # Wait for any result-like list items to appear
        self.wait_visible(*self.RESULTS)
        return True
