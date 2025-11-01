# test_selector_smoke.py
import pytest
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# @pytest.mark.selector
def test_print_button_click():
    opts = Options()
    opts.add_argument("--disable-gpu")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    opts.add_argument("--disable-renderer-backgrounding")
    opts.add_argument("--disable-background-timer-throttling")
    opts.add_argument("--disable-backgrounding-occluded-windows")
    opts.add_argument("--no-first-run")
    opts.add_argument("--no-default-browser-check")

    # CAS/SSO often needs 3rd-party cookies across redirects
    prefs = {
        "profile.block_third_party_cookies": False,
        "profile.default_content_setting_values.cookies": 1,
        "plugins.always_open_pdf_externally": True,
        "download.default_directory": "/tmp/quest_downloads",
        "download.prompt_for_download": False,
        "download.directory_upgrade": True,
    }
    opts.add_experimental_option("prefs", prefs)
    opts.add_experimental_option("debuggerAddress", "127.0.0.1:9222")
    driver = webdriver.Chrome(options=opts)

    btn = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.CSS_SELECTOR, "mat-select[aria-label='Items per page:']"))
    )

    driver.execute_script("arguments[0].scrollIntoView({block:\"center\"});", btn)
    try:
        btn.click()
        
        btn2 = WebDriverWait(driver, 5).until(
        EC.element_to_be_clickable((By.XPATH, "//div[contains(@class,'mat-select-panel') and @aria-label='Items per page:']//mat-option//span[normalize-space()='100']"))
        )
        
        btn2.click()
        
    except Exception:
        driver.execute_script("arguments[0].click()", btn)
    driver.quit()