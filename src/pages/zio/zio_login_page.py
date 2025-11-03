from __future__ import annotations

import os
import subprocess
import time
from pathlib import Path
from typing import Iterable, List

from selenium.common.exceptions import TimeoutException
from selenium.webdriver.common.by import By
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.support.ui import WebDriverWait

from src.core.base_page import BasePage


class ZioLoginPage(BasePage):
    URL = "https://www.ziosuite.com/en-us/login?ir_rurl=%2Fdashboard"

    EMAIL_INPUT = (By.ID, "login-email")
    CONTINUE_BUTTON = (By.ID, "login-continue")
    PASSWORD_INPUT = (By.ID, "login-password")
    SUBMIT_BUTTON = (By.ID, "login-submit")
    SESSION_LIMIT_ERROR = (
        By.XPATH,
        "//ul[contains(@class,'messages') and contains(@class,'error')]"
        "//li[contains(normalize-space(.), '5 session limit exceeded.')]",
    )
    ERROR_BANNERS = (
        By.XPATH,
        "//p[contains(@class, 'error-message') or contains(@class, 'alert')]",
    )
    DASHBOARD_INDICATORS: Iterable[tuple[By, str]] = (
        (By.XPATH, "//span[text()='Reports']"),
        (By.XPATH, "//tbody[contains(@class,'ng-star-inserted')]"),
    )
    PROFILE_MENU = (By.XPATH, "//div[@class='nav user-dropdown ng-star-inserted']//ul//li")
    LOGOUT_BUTTON = (By.XPATH, "//a[normalize-space()='Log Out']")

    def open(self) -> "ZioLoginPage":
        return self.go_to(self.URL)  # type: ignore[return-value]

    def enter_email(self, email: str) -> None:
        self.type(*self.EMAIL_INPUT, email)

    def continue_to_password(self) -> None:
        self.click(*self.CONTINUE_BUTTON)

    def enter_password(self, password: str) -> None:
        self.type(*self.PASSWORD_INPUT, password)

    def submit(self) -> None:
        self.click(*self.SUBMIT_BUTTON)

    def has_session_limit_error(self) -> bool:
        return bool(self.driver.find_elements(*self.SESSION_LIMIT_ERROR))

    def wait_for_dashboard_ready(self, timeout: int = 45) -> bool:
        deadline = time.time() + timeout
        while time.time() < deadline:
            if "dashboard" in (self.driver.current_url or "").lower():
                return True
            for locator in self.DASHBOARD_INDICATORS:
                if self.driver.find_elements(*locator):
                    return True
            time.sleep(1)
        return False

    def get_error_messages(self) -> List[str]:
        return [element.text.strip() for element in self.driver.find_elements(*self.ERROR_BANNERS)]

    def logout(self, wait_time: int = 5) -> None:
        try:
            menu = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.PROFILE_MENU))
            menu.click()
            time.sleep(1)
            logout_link = WebDriverWait(self.driver, 10).until(EC.element_to_be_clickable(self.LOGOUT_BUTTON))
            logout_link.click()
            time.sleep(wait_time)
        except Exception:
            pass
