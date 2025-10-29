from __future__ import annotations

# from src.tests.conftest import driver
from src.flows.quest.login import QuestLoginFlow
from src.flows.quest.search import QuestSearchFlow


def RunQuest(driver,username: str, password: str, patient_name: str, patient_dob: str) -> None:
    login_flow = QuestLoginFlow(driver)
    search_flow = QuestSearchFlow(driver)
    try:
        login_flow.login(username, password)
        search_flow.search_and_open(patient_name, patient_dob)
    finally:
        driver.quit()


# if __name__ == "__main__":
#     RunQuest()
