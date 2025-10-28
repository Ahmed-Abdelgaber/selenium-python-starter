import pytest
from src.pages.tricore.tricore_login_page import TricoreLoginPage
from src.tests.conftest import driver

@pytest.mark.smoke
def test_open_tricore_login_page(driver):
    page = TricoreLoginPage(driver).open()
    assert page.is_loaded()
    page.login("sneelagaru", "Menaul11311%")
    