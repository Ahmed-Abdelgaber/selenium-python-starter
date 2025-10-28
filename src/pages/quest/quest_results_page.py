from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class QuestResultsPage(BasePage):
  RESULTS_NAV_BUTTON = (By.CSS_SELECTOR, "button#route-results-io2")
  EXTERNAL_HISTORICAL_RESULTS_BUTTON = (By.CSS_SELECTOR, "div#mat-tab-label-0-2")
  PATIENT_NAME_FIELD = (By.CSS_SELECTOR, "input[type='text'], input[data-placeholder='Patient Name']")
  PATIENT_DOB_FIELD = (By.CSS_SELECTOR, "input[type='text'], input[data-placeholder='Patient DOB']")
  SEARCH_BUTTON = (By.CSS_SELECTOR, "button#nonPracticePatientSearch")
  SEARCH_RESULT = ((By.CSS_SELECTOR, "div[class='qd-result-card-io__container ng-star-inserted']"))
  CONTINUE_BUTTON = (By.CSS_SELECTOR, "button[data-testid='confirmation-content-dialog-continueBtn'], button[type='button']")
  
  def open_results_page(self) -> "QuestResultsPage":
    self.click(*self.RESULTS_NAV_BUTTON)
    
  def open_external_historical_results(self) -> None:
    self.click(*self.EXTERNAL_HISTORICAL_RESULTS_BUTTON)

  def search_patient(self, patient_name: str, patient_dob: str) -> None:
    self.type(*self.PATIENT_NAME_FIELD, patient_name)
    self.type(*self.PATIENT_DOB_FIELD, patient_dob)
    self.click(*self.SEARCH_BUTTON)
    
  def has_results(self) -> bool:
    return self.find(*self.SEARCH_RESULT) is not None
    
  def is_loaded(self) -> bool:
    return self.find(*self.EXTERNAL_HISTORICAL_RESULTS_BUTTON) is not None

  def open_search_results(self) -> None:
    self.click(*self.SEARCH_RESULT)
    self.click(*self.CONTINUE_BUTTON)