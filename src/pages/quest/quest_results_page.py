from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from src.core.base_page import BasePage
import time

class QuestSearchPage(BasePage):
  RESULT_CARD = (By.CSS_SELECTOR, "mat-card[data-testid='rslt-nonpractice-card']")
  CARD_CHECKBOX_LABEL = (By.CSS_SELECTOR, "mat-checkbox label.mat-checkbox-layout")
  CARD_CHECKBOX_INPUT = (By.CSS_SELECTOR, "mat-checkbox input[type='checkbox']")
  CARD_TESTS = (By.CSS_SELECTOR, ".qd-result-non-practice-card__content .qd-result-card-io__left .ng-star-inserted")
  PRINT_BTN = (By.CSS_SELECTOR, "button[data-testid='non-practice-rslt-printBtn']")
  ITEMS_PER_PAGE_SELECT = (By.CSS_SELECTOR, "mat-select[aria-label='Items per page:']")
  ITEMS_PER_PAGE_PANEL  = (By.CSS_SELECTOR, "div.mat-select-panel[aria-label='Items per page:']")
  ITEMS_PER_PAGE_100    = (By.XPATH, "//div[contains(@class,'mat-select-panel') and @aria-label='Items per page:']//mat-option//span[normalize-space()='100']")
  IFRAME_PRINT     = (By.CSS_SELECTOR, "div.mat-dialog-container iframe#multiplePdfs, iframe#multiplePdfs")
  OPEN_BTN = (By.CSS_SELECTOR, "button#open-button")
  CLOSE_PRINT_DIALOG = (By.CSS_SELECTOR, "[data-testid='close-printRslt-dialog']")
  INTERSTITIAL_WRAPPER = (By.CSS_SELECTOR, ".interstitial-wrapper")
  INTERSTITIAL_OPEN_BTN = (By.CSS_SELECTOR, "#open-button")
  INTERSTITIAL_ANCHOR   = (By.CSS_SELECTOR, ".interstitial-wrapper a[href]")

  
  def get_cards(self):
    time.sleep(5)  # Wait for results to load
    self._increase_results_per_page()
    time.sleep(2)  # Wait for results to adjust
    return self.find_all(*self.RESULT_CARD, visible_only=True, timeout=15)
  
  def scroll_to_card(self, card_element) -> None:
    try:
      self.driver.execute_script("window.scrollBy(0, arguments[0]);", card_element.location['y'] - 200)
    except Exception:
      pass
    self.driver.execute_script("arguments[0].scrollIntoView({block:'center'});", card_element)
  
  def _is_checked(self, card_element) -> bool:
    try:
      cb_input = card_element.find_element(*self.CARD_CHECKBOX_INPUT)
      aria = cb_input.get_attribute("aria-checked")
      if aria and aria.lower() == "true":
          return True
      parent = card_element.find_element(By.CSS_SELECTOR, "mat-checkbox").get_attribute("class")
      return "mat-checkbox-checked" in parent
    except Exception:
      return False
    
  def select_card(self, card_element) -> None:
    label = card_element.find_element(*self.CARD_CHECKBOX_LABEL)
    try:
        self.driver.execute_script("arguments[0].click();", label)
    except Exception:
        inner = card_element.find_element(By.CSS_SELECTOR, "mat-checkbox .mat-checkbox-inner-container")
        self.driver.execute_script("arguments[0].click();", inner)
    self.wait.until(lambda d: self._is_checked(card_element))
    
  def get_file_name(self, card_element, idx) -> str:
    test_nodes = card_element.find_elements(*self.CARD_TESTS)
    parts = []
    for node in test_nodes:
    # textContent keeps any trailing ';' and spacing better than .text
      txt = (node.get_attribute("textContent") or "").replace("\xa0", " ").strip()
      if txt:
          # collapse internal whitespace but keep actual text
        txt = " ".join(txt.split())
        parts.append(txt)
    
    if parts:
        # Join with ";" to match the visual style (first item ends with " ;", next on a new line)
        title = ";".join(parts)
        # If the last part came with a trailing ';' from DOM, that's fine; no extra added.
    else:
        title = f"DEFAULT (empty title) for card #{idx+1}"
    
    return title
  
  def click_print(self) -> None:
    self.click(*self.PRINT_BTN)
  
  def click_open_in_interstitial(self) -> None:
    self.switch_to_frame(*self.IFRAME_PRINT)
    try:
      self.click(*self.OPEN_BTN, True)
    except Exception:
      # Fallback: click via JS
      open_btn = self.find(*self.OPEN_BTN)
      self.driver.execute_script("arguments[0].click();", open_btn)
    finally:
        self.driver.switch_to.default_content()

  def close_print_dialog(self) -> None:
    self.click(*self.CLOSE_PRINT_DIALOG)

  def _increase_results_per_page(self) -> None:
    self.click(*self.ITEMS_PER_PAGE_SELECT)
    self.find(*self.ITEMS_PER_PAGE_PANEL)
    self.click(*self.ITEMS_PER_PAGE_100)