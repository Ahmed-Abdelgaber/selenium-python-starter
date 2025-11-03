from __future__ import annotations

from src.core.logger import get_logger
from src.pages.xr.xr_login_page import XrLoginPage
from src.pages.xr.xr_reports_page import XrReportsPage


class XrLoginFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.xr.login")

    def login(self, username: str, password: str) -> None:
        page = XrLoginPage(self.driver).open()
        self.logger.info("Submitting XR credentials for '%s'", username)
        page.enter_credentials(username, password)
        page.submit()
        page.accept_prompt()
        page.open_reports()
        XrReportsPage(self.driver).wait_until_loaded()
        self.logger.info("XR reports page loaded for '%s'", username)

