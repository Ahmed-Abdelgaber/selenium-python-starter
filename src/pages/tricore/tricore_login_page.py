from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class TricoreLoginPage(BasePage):
    URL = "https://trl.rhodesgroup.com/"

    USERNAME = (By.CSS_SELECTOR, "input[name='username'], input[type='text']")
    PASSWORD = (By.CSS_SELECTOR, "input[name='password'], input[type='password']")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button[type='submit'], input[type='submit']")
    CURRENT_SCREEN = (By.CSS_SELECTOR, "span[class='current-screen ng-star-inserted']")

    def open(self) -> "TricoreLoginPage":
        return self.go_to(self.URL)

    def login(self, username: str, password: str) -> None:
        self.type(*self.USERNAME, username)
        self.type(*self.PASSWORD, password)
        self.click(*self.LOGIN_BUTTON)

    def is_logged(self) -> bool:
        inbox = self.text_of(*self.CURRENT_SCREEN)
        if inbox != "Inbox":
            return False
        return True