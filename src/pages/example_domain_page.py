from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class ExampleDomainPage(BasePage):
    H1 = (By.CSS_SELECTOR, "h1")

    def open(self) -> "ExampleDomainPage":
        return self.go_to("https://example.com")

    def heading_text(self) -> str:
        return self.text_of(*self.H1)
