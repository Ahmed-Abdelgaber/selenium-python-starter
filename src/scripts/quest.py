from __future__ import annotations

import argparse
import os
import sys
from typing import List

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger
from src.core.retry import retry
from src.flows.quest.login import QuestLoginFlow
from src.flows.quest.logout import QuestLogoutFlow
from src.flows.quest.results import QuestResultsFlow
from src.flows.quest.search import QuestSearchFlow

LOGGER = get_logger("scripts.quest")


def RunQuest(
    driver,
    username: str,
    password: str,
    patient_name: str,
    patient_dob: str,
) -> List[str]:
    LOGGER.info("Starting Quest automation run")

    config = load_config()

    def _run(current_driver) -> List[str]:
        LOGGER.debug("Initializing Quest flows")
        login_flow = QuestLoginFlow(current_driver)
        search_flow = QuestSearchFlow(current_driver)
        results_flow = QuestResultsFlow(current_driver)

        success = False
        try:
            LOGGER.info("Executing Quest login flow")
            login_flow.login(username, password)

            LOGGER.info("Executing Quest search flow")
            search_flow.search_and_open(patient_name, patient_dob)
            LOGGER.info("Executing Quest results flow")
            downloaded_files = results_flow.download_results()
            if not downloaded_files:
                raise AssertionError("Quest results download is empty")
            success = True
            LOGGER.info("Quest automation attempt completed successfully")
            return downloaded_files
        finally:
            if success:
                LOGGER.info("Logging out from Quest session")
                try:
                    QuestLogoutFlow(current_driver).logout()
                except Exception:
                    LOGGER.warning("Quest logout encountered an issue", exc_info=True)

    return retry(
        _run,
        driver,
        driver_factory=lambda: create_driver(config),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Quest automation flow.")
    parser.add_argument(
        "--username",
        default=os.getenv("QUEST_USERNAME"),
        help="Quest username (env: QUEST_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("QUEST_PASSWORD"),
        help="Quest password (env: QUEST_PASSWORD)",
    )
    parser.add_argument(
        "--patient-name",
        default=os.getenv("QUEST_PATIENT_NAME"),
        help="Patient full name to search (env: QUEST_PATIENT_NAME)",
    )
    parser.add_argument(
        "--patient-dob",
        default=os.getenv("QUEST_PATIENT_DOB"),
        help="Patient date of birth (env: QUEST_PATIENT_DOB)",
    )
    args = parser.parse_args()

    missing = [
        flag
        for flag, value in {
            "--username": args.username,
            "--password": args.password,
            "--patient-name": args.patient_name,
            "--patient-dob": args.patient_dob,
        }.items()
        if not value
    ]
    if missing:
        parser.error(f"missing required arguments: {', '.join(missing)}")
    return args


if __name__ == "__main__":
    configuration = load_config()
    cli_args = _parse_args()
    driver_instance = create_driver(configuration)
    try:
        RunQuest(
            driver_instance,
            cli_args.username,
            cli_args.password,
            cli_args.patient_name,
            cli_args.patient_dob,
        )
    except Exception as exc:
        LOGGER.exception("Quest flow terminated with error: %s", exc)
        sys.exit(1)
    finally:
        try:
            driver_instance.quit()
        except Exception:
            LOGGER.warning("Unable to quit Quest driver cleanly")
