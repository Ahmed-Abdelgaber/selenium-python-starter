# src/tests/test_open_quest_login.py
import pytest
from src.pages.quest.quest_login_page import QuestCasLoginPage
import time

@pytest.mark.smoke
def test_open_quest_cas_login_page(driver):
    page = QuestCasLoginPage(driver).open()
    assert page.is_loaded()
    page.login("sneelagaru", "Menaul11311$$")
    time.sleep(60)
    assert page.is_logged()
    