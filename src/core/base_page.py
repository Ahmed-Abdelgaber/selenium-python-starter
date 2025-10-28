from __future__ import annotations
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement

class BasePage:
    def __init__(self, driver: WebDriver, wait_timeout: int = 10) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)

    # Navigation
    def go_to(self, url: str) -> "BasePage":
        self.driver.get(url)
        return self

    # Low-level finders
    def find(self, by: By, locator: str):
        return self.wait.until(EC.presence_of_element_located((by, locator)))

    def click(self, by: By, locator: str):
        el = self.wait.until(EC.element_to_be_clickable((by, locator)))
        el.click()
        return el

    def type(self, by: By, locator: str, text: str, clear: bool = True):
        el = self.find(by, locator)
        if clear:
            el.clear()
        el.send_keys(text)
        return el

    def text_of(self, by: By, locator: str) -> str:
        el = self.find(by, locator)
        return el.text

    def wait_visible(self, by: By, locator: str):
        return self.wait.until(EC.visibility_of_element_located((by, locator)))
