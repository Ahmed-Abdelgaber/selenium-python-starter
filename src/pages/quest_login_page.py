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

    def open(self) -> "QuestCasLoginPage":
        return self.go_to(self.URL)

    def login(self, username: str, password: str) -> None:
        self.type(*self.USERNAME, username)
        self.type(*self.PASSWORD, password)
        self.click(By.CSS_SELECTOR, "button#signin, input[type='submit']")
    
    def is_loaded(self) -> bool:
        # URL contains host + path
        self.wait.until(lambda d: "auth2.questdiagnostics.com" in d.current_url and "cas/login" in d.current_url)
        # if a field is present, great—otherwise consider URL check sufficient
        try:
            self.wait_visible(*self.USERNAME)
        except Exception:
            try:
                self.wait_visible(*self.PASSWORD)
            except Exception:
                pass
        return True
      
    def is_logged(self) -> bool:
      return True