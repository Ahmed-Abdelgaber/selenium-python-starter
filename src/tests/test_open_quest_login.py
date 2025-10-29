# src/tests/test_open_quest_login.py
import pytest
from src.pages.quest.quest_login_page import QuestCasLoginPage
import time
from src.tests.conftest import driver
from src.scripts.quest import RunQuest

USERNAME = "sneelagaru"
PASSWORD = "Menaul11311$$"
PATIENT_NAME = "Maria Minjares"
PATIENT_DOB = "04/05/1954"

@pytest.mark.smoke
def test_open_quest_cas_login_page(driver):
    RunQuest(driver, USERNAME, PASSWORD, PATIENT_NAME, PATIENT_DOB)
    time.sleep(2)
    