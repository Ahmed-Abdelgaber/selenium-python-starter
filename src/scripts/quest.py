from __future__ import annotations

from src.tests.conftest import driver
from src.flows.quest.login import QuestLoginFlow
from src.flows.quest.search import QuestSearchFlow


USERNAME = "CHANGE_ME"
PASSWORD = "CHANGE_ME"
PATIENT_NAME = "CHANGE_ME"
PATIENT_DOB = "01/01/1970"


def main() -> None:
    login_flow = QuestLoginFlow(driver)
    search_flow = QuestSearchFlow(driver)
    try:
        login_flow.login(USERNAME, PASSWORD)
        search_flow.search_and_open(PATIENT_NAME, PATIENT_DOB)
    finally:
        driver.quit()


if __name__ == "__main__":
    main()
