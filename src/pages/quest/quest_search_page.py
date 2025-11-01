from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class QuestSearchPage(BasePage):
  RESULTS_NAV_BUTTON = (By.CSS_SELECTOR, "button#route-results-io2")
  EXTERNAL_HISTORICAL_RESULTS_BUTTON = (By.XPATH, "//div[@role='tab'][.//span[@data-testid='non-practice-historical-tab']]")
  PATIENT_NAME_FIELD = (By.CSS_SELECTOR, "input[data-testid='non-practice-historical-patientName']")
  PATIENT_DOB_FIELD = (By.CSS_SELECTOR, "input[data-testid='non-practice-historical-dob']")
  SEARCH_BUTTON = (By.CSS_SELECTOR, "button#nonPracticePatientSearch")
  SEARCH_RESULT = (By.CSS_SELECTOR, "div[class='qd-result-card-io__container ng-star-inserted']")
  CONTINUE_BUTTON = (By.CSS_SELECTOR, "button[data-testid='confirmation-content-dialog-continueBtn']")
  
  def open_results_page(self) -> "QuestSearchPage":
    self.click(*self.RESULTS_NAV_BUTTON)
    
  def open_external_historical_results(self) -> None:
    self.click(*self.EXTERNAL_HISTORICAL_RESULTS_BUTTON, True)

  def search_patient(self, patient_name: str, patient_dob: str) -> None:
    self.open_external_historical_results()
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
    