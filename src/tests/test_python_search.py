import pytest
from src.pages.python_home_page import PythonHomePage

@pytest.mark.regression
def test_python_search_returns_results(driver):
    results = PythonHomePage(driver).open().search("selenium")
    assert results.has_results()
