from __future__ import annotations
from selenium.webdriver.remote.webdriver import WebDriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.remote.webelement import WebElement
from selenium.common.exceptions import TimeoutException
from typing import List


class BasePage:
    def __init__(self, driver: WebDriver, wait_timeout: int = 30) -> None:
        self.driver = driver
        self.wait = WebDriverWait(driver, wait_timeout)

    # Navigation
    def go_to(self, url: str) -> "BasePage":
        self.driver.get(url)
        return self

    # Low-level finders
    def find(self, by: By, locator: str):
        return self.wait.until(EC.presence_of_element_located((by, locator)))

    def click(self, by: By, locator: str, wait_for: bool = False):
        if wait_for:
            el = self.wait.until(EC.element_to_be_clickable((by, locator)))
            el.click()
        else:
            el = self.find(by, locator)
            el.click()
        return el

    def type(self, by: By, locator: str, text: str, clear: bool = True):
        el = self.wait.until(EC.element_to_be_clickable((by, locator)))
        if clear:
            el.clear()
        el.send_keys(text)
        return el

    def text_of(self, by: By, locator: str, wait_for: str = None) -> str:
        if wait_for:
            self.wait.until(EC.text_to_be_present_in_element((by, locator), wait_for))
        el = self.find(by, locator)
        return el.text

    def wait_visible(self, by: By, locator: str):
        return self.wait.until(EC.visibility_of_element_located((by, locator)))
    
    def switch_to_frame(self, by: By, locator: str):
        frame = self.wait.until(EC.frame_to_be_available_and_switch_to_it((by, locator)))
        return frame
    
    def find_all(
    self,
    by: By,
    locator: str,
    *,
    visible_only: bool = False,
    timeout: int | None = None,
    raise_on_empty: bool = False,
    ) -> List[WebElement]:
        """
        Return a list of WebElements matching the locator.
        - visible_only: if True, wait for visibility; otherwise presence.
        - timeout: per-call timeout; defaults to self.wait's timeout when None.
        - raise_on_empty: if True, raise on empty; otherwise return [].
        """
        _wait = self.wait if timeout is None else WebDriverWait(self.driver, timeout)
        condition = EC.visibility_of_all_elements_located((by, locator)) if visible_only \
                    else EC.presence_of_all_elements_located((by, locator))
        try:
            elems = _wait.until(condition)
            return elems if isinstance(elems, list) else [elems]
        except TimeoutException:
            if raise_on_empty:
                raise
            return []
