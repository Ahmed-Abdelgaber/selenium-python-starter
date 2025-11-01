from __future__ import annotations

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.retry import retry
from src.flows.tricore.login import TricoreLoginFlow
from src.flows.tricore.search import TricoreSearchFlow
from src.flows.tricore.results import TricoreResultsFlow


def RunTricore(
    driver,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    dob: str,
    gender: str
) -> None:
    config = load_config()

    def _execute(current_driver) -> None:
        login_flow = TricoreLoginFlow(current_driver)
        search_flow = TricoreSearchFlow(current_driver)
        results_flow = TricoreResultsFlow(current_driver)

        login_flow.login(username, password)
        search_flow.search_patient(
            first_name,
            last_name,
            dob,
            gender,
        )
        results_flow.search_and_download()

    return retry(
        _execute,
        driver,
        driver_factory=lambda: create_driver(config),
    )
