from __future__ import annotations

import argparse
import os
import sys

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger
from src.core.retry import retry
from src.flows.tricore.login import TricoreLoginFlow
from src.flows.tricore.search import TricoreSearchFlow
from src.flows.tricore.results import TricoreResultsFlow

LOGGER = get_logger("scripts.tricore")


def RunTricore(
    driver,
    username: str,
    password: str,
    first_name: str,
    last_name: str,
    dob: str,
    gender: str,
) -> list[str]:
    LOGGER.info("Starting Tricore automation run")
    config = load_config()

    def _run(current_driver) -> list[str]:
        LOGGER.debug("Initializing Tricore flows")
        login_flow = TricoreLoginFlow(current_driver)
        search_flow = TricoreSearchFlow(current_driver)
        results_flow = TricoreResultsFlow(current_driver)

        LOGGER.info("Executing Tricore login flow for '%s'", username)
        login_flow.login(username, password)
        LOGGER.info("Executing Tricore search flow for '%s %s'", first_name, last_name)
        search_flow.search_patient(
            first_name,
            last_name,
            dob,
            gender,
        )
        LOGGER.info("Executing Tricore results flow")
        downloaded_files = results_flow.search_and_download()
        LOGGER.info("Tricore automation completed with %d file(s)", len(downloaded_files))
        return downloaded_files

    return retry(
        _run,
        driver,
        driver_factory=lambda: create_driver(config),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run Tricore automation flow.")
    parser.add_argument(
        "--username",
        default=os.getenv("TRICORE_USERNAME"),
        help="Tricore username (env: TRICORE_USERNAME)",
    )
    parser.add_argument(
        "--password",
        default=os.getenv("TRICORE_PASSWORD"),
        help="Tricore password (env: TRICORE_PASSWORD)",
    )
    parser.add_argument(
        "--first-name",
        default=os.getenv("TRICORE_FIRST_NAME"),
        help="Patient first name (env: TRICORE_FIRST_NAME)",
    )
    parser.add_argument(
        "--last-name",
        default=os.getenv("TRICORE_LAST_NAME"),
        help="Patient last name (env: TRICORE_LAST_NAME)",
    )
    parser.add_argument(
        "--dob",
        default=os.getenv("TRICORE_DOB"),
        help="Patient date of birth (env: TRICORE_DOB)",
    )
    parser.add_argument(
        "--gender",
        default=os.getenv("TRICORE_GENDER"),
        help="Patient gender (env: TRICORE_GENDER)",
    )

    args = parser.parse_args()
    missing = [
        flag
        for flag, value in {
            "--username": args.username,
            "--password": args.password,
            "--first-name": args.first_name,
            "--last-name": args.last_name,
            "--dob": args.dob,
            "--gender": args.gender,
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
        RunTricore(
            driver_instance,
            cli_args.username,
            cli_args.password,
            cli_args.first_name,
            cli_args.last_name,
            cli_args.dob,
            cli_args.gender,
        )
    except Exception as exc:
        LOGGER.exception("Tricore flow terminated with error: %s", exc)
        sys.exit(1)
    finally:
        LOGGER.info("Leaving Tricore browser session open for inspection")
