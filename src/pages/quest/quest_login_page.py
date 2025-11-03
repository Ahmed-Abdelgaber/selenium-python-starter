from __future__ import annotations

from selenium.common.exceptions import TimeoutException
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
        try:
            self.click(*self.COOKIES_BUTTON)
        except TimeoutException:
            pass

    def is_loaded(self) -> bool:
        return self.find(*self.LOGIN_BUTTON) is not None

    def switch_to_portal_window(self) -> None:
        """
        Ensure we are focused on the Quanum portal window once CAS completes.
        Quest may keep the same tab or spawn a new one depending on SSO rules.
        """
        try:
            self.wait.until(lambda drv: len(drv.window_handles) >= 1)
        except TimeoutException:
            return

        try:
            newest = self.driver.window_handles[-1]
            if self.driver.current_window_handle != newest:
                self.driver.switch_to.window(newest)
        except Exception:
            pass

    def wait_for_portal_navigation(self) -> bool:
        """Block until the Quanum portal finishes redirecting away from CAS."""
        try:
            self.wait.until(
                lambda drv: "quanum.questdiagnostics.com" in drv.current_url.lower()
            )
            return True
        except TimeoutException:
            return False
