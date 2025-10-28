# src/pages/quest_login_page.py
from selenium.webdriver.common.by import By
from src.core.base_page import BasePage



class QuestCasLoginPage(BasePage):
    URL = (
        "https://auth2.questdiagnostics.com/cas/login"
        "?service=https%3A%2F%2Fphysician.quanum.questdiagnostics.com%2Fhcp-server-web%2Flogin%2Fcas"
    )

    # keep selectors conservative to avoid brittleness
    USERNAME = (By.CSS_SELECTOR, "input#username, input[name='username'], input[type='text']")
    PASSWORD = (By.CSS_SELECTOR, "input#password, input[name='password'], input[type='password']")
    LOGIN_BUTTON = (By.CSS_SELECTOR, "button#signin, input[type='submit']")
    COOKIES_BUTTON = (By.CSS_SELECTOR, "button#onetrust-accept-btn-handler")
    GREETING_PHRASE = (By.CSS_SELECTOR, ".qd-header__title b, .qd-header__title strong")

    def open(self) -> "QuestCasLoginPage":
        return self.go_to(self.URL)

    def login(self, username: str, password: str) -> None:
        self.type(*self.USERNAME, username)
        self.type(*self.PASSWORD, password)
        self.click(*self.LOGIN_BUTTON)
        if self.find(*self.COOKIES_BUTTON):
            self.click(*self.COOKIES_BUTTON)
    
    def is_loaded(self) -> bool:
        return self.find(*self.LOGIN_BUTTON) is not None
    
    def is_logged(self) -> bool:
        self.wait_visible(*self.GREETING_PHRASE)
        name = self.text_of(*self.GREETING_PHRASE)
        if name == "Suresh Neelagaru":
            return True
        return False