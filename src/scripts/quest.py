from __future__ import annotations

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.retry import retry
from src.flows.quest.login import QuestLoginFlow
from src.flows.quest.logout import QuestLogoutFlow
from src.flows.quest.results import QuestResultsFlow
from src.flows.quest.search import QuestSearchFlow


def RunQuest(driver,username: str, password: str, patient_name: str, patient_dob: str) -> None:
    config = load_config()

    def _execute(current_driver) -> None:
        login_flow = QuestLoginFlow(current_driver)
        search_flow = QuestSearchFlow(current_driver)
        results_flow = QuestResultsFlow(current_driver)

        success = False
        try:
            login_flow.login(username, password)
            search_flow.search_and_open(patient_name, patient_dob)
            downloaded_files = results_flow.download_results()
            if not downloaded_files:
                raise AssertionError("Quest results download is empty")
            success = True
        finally:
            if success:
                QuestLogoutFlow(current_driver).logout()
                current_driver.quit()

    def _handle_retry_cleanup(current_driver, exc) -> None:
        QuestLogoutFlow(current_driver).logout()

    return retry(
        _execute,
        driver,
        driver_factory=lambda: create_driver(config),
        before_retry=_handle_retry_cleanup,
    )


# if __name__ == "__main__":
#     RunQuest()
