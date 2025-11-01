from selenium.webdriver.common.by import By
from src.core.base_page import BasePage
import time

class QuestLogoutPage(BasePage):
    ACCOUNT_SETTINGS_BUTTON = (By.CSS_SELECTOR, 'button[aria-label="Account Settings"]')
    SIGN_OUT_BUTTON = (By.CSS_SELECTOR, "button.qd-account__menu-actions--button:has(.icon-signout)")

    def logout(self) -> None:
      # time.sleep(60 * 60)
      self.click(*self.ACCOUNT_SETTINGS_BUTTON)
      time.sleep(10)  # Wait for the menu to open
      self.click(*self.SIGN_OUT_BUTTON)
      time.sleep(10)  # Wait for logout to process