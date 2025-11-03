from __future__ import annotations

import argparse
import os
import sys
import time
from typing import List, Optional

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger
from src.core.retry import retry
from src.flows.zio.login import ZioLoginFlow
from src.flows.zio.reports import ZioReportsFlow

LOGGER = get_logger("scripts.zio")


def RunZio(
    driver,
    username: str,
    password: str,
    first_name: Optional[str] = None,
    last_name: Optional[str] = None,
    *,
    download_all: bool = False,
) -> List[str]:
    LOGGER.info("Starting ZIO automation run")
    def _run(current_driver) -> List[str]:
        LOGGER.debug("Executing ZIO run core logic")
        login_flow = ZioLoginFlow(current_driver)
        reports_flow = ZioReportsFlow(current_driver)

        login_page = login_flow.login(username, password)
        reports_flow.open_reports()

        target_tokens: Optional[List[str]] = None
        if not download_all:
            if not first_name or not last_name:
                raise ValueError("first_name and last_name are required unless download_all is enabled")
            target_tokens = reports_flow.apply_name_filter(first_name, last_name)

        try:
            downloaded_files = reports_flow.download_reports(
                target_tokens=target_tokens,
            )
            LOGGER.info("ZIO automation completed with %d file(s)", len(downloaded_files))
            return downloaded_files
        finally:
            try:
                LOGGER.info("Logging out from ZIO session")
                login_page.logout()
                LOGGER.info("Pause to observe ZIO logout")
                time.sleep(5)
            except Exception:
                LOGGER.warning("ZIO logout encountered an issue", exc_info=True)

    config = load_config()

    return retry(
        _run,
        driver,
        driver_factory=lambda: create_driver(config),
    )


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run ZIO automation flow.")
    parser.add_argument("--username", default=os.getenv("ZIO_USERNAME"), help="ZIO username/email")
    parser.add_argument("--password", default=os.getenv("ZIO_PASSWORD"), help="ZIO password")
    parser.add_argument("--first-name", default=os.getenv("ZIO_FIRST_NAME"), help="Patient first name")
    parser.add_argument("--last-name", default=os.getenv("ZIO_LAST_NAME"), help="Patient last name")
    args = parser.parse_args()

    if not args.username or not args.password:
        parser.error("ZIO username and password are required (set env vars or CLI options).")

    return args


if __name__ == "__main__":
    configuration = load_config()
    cli_args = _parse_args()
    driver_instance = create_driver(configuration)
    try:
        RunZio(
            driver_instance,
            cli_args.username,
            cli_args.password,
            cli_args.first_name,
            cli_args.last_name,
        )
    except Exception as exc:
        LOGGER.exception("ZIO flow terminated with error: %s", exc)
        sys.exit(1)
    finally:
        try:
            driver_instance.quit()
        except Exception:
            LOGGER.warning("Unable to quit ZIO driver cleanly")
