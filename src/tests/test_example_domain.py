import pytest
from src.pages.example_domain_page import ExampleDomainPage

@pytest.mark.smoke
def test_example_domain_title(driver):
    page = ExampleDomainPage(driver).open()
    assert page.heading_text() == "Example Domain"
