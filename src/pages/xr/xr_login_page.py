from __future__ import annotations

from selenium.webdriver.common.by import By

from src.core.base_page import BasePage


class XrLoginPage(BasePage):
    URL = "https://portal.xraynm.com/login.aspx?ReturnUrl=%2f"

    USERNAME_INPUT = (By.ID, "txtUser")
    PASSWORD_INPUT = (By.ID, "txtPass")
    LOGIN_BUTTON = (By.ID, "loginpop")
    ACCEPT_BUTTON = (By.ID, "btnLogin")
    REPORTS_BUTTON = (
        By.CSS_SELECTOR,
        'input.searchbutton[value="View Reports/Images"]',
    )

    def open(self) -> "XrLoginPage":
        return self.go_to(self.URL)  # type: ignore[return-value]

    def enter_credentials(self, username: str, password: str) -> None:
        self.type(*self.USERNAME_INPUT, username)
        self.type(*self.PASSWORD_INPUT, password)

    def submit(self) -> None:
        self.click(*self.LOGIN_BUTTON)

    def accept_prompt(self) -> None:
        self.click(*self.ACCEPT_BUTTON)

    def open_reports(self) -> None:
        self.click(*self.REPORTS_BUTTON)

