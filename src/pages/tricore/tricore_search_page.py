from selenium.webdriver.common.by import By
from src.core.base_page import BasePage

class TricoreResultsPage(BasePage):
  SEARCH_PATIENT_BUTTON = (By.CSS_SELECTOR, "button.mdc-button--raised:has(span.mdc-button__label:contains('Patient Search'))")
  FIRST_NAME = (By.ID, "firstName")
  LAST_NAME = (By.ID, "lastName")
  DOB = (By.CSS_SELECTOR, "input.mat-datepicker-input#mat-input-2")
  GENDER = (By.CSS_SELECTOR, "mat-select[role='combobox'][id='mat-select-0']")
  MALE_OPTION = (By.XPATH, "//mat-option[.//span[text()='Male']]")
  FEMALE_OPTION = (By.XPATH, "//mat-option[.//span[text()='Female']]")
  SEARCH_BUTTON = (By.CSS_SELECTOR, "button[type='submit']")
  
  def open_search_patient(self) -> None:
      self.click(*self.SEARCH_PATIENT_BUTTON)

  def search_patient(self, first_name: str, last_name: str, dob: str, gender: str) -> None:
      self.type(*self.FIRST_NAME, first_name)
      self.type(*self.LAST_NAME, last_name)
      self.type(*self.DOB, dob)
      self.click(*self.GENDER)
      if gender == 'male':
        self.click(*self.MALE_OPTION)
      else:
        self.click(*self.FEMALE_OPTION)
      self.click(*self.SEARCH_BUTTON)