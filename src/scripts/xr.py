from __future__ import annotations

import argparse
import os
import sys
from typing import Optional

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger
from src.flows.xr.login import XrLoginFlow
from src.flows.xr.reports import XrReportsFlow

LOGGER = get_logger("scripts.xr")


def RunXr(
    driver,
    username: str,
    password: str,
    last_name: str,
    first_name: str,
    dob: Optional[str] = None,
    *,
    start_date: Optional[str] = None,
    end_date: Optional[str] = None,
) -> list[str]:
    LOGGER.info("Starting XR automation run")
    login_flow = XrLoginFlow(driver)
    reports_flow = XrReportsFlow(driver)

    login_flow.login(username, password)
    reports_flow.search_reports(
        last_name,
        first_name,
        dob=dob,
        start_date=start_date,
        end_date=end_date,
    )
    files = reports_flow.download_reports(
        last_name=last_name,
        first_name=first_name,
        dob=dob,
    )
    LOGGER.info("XR automation completed with %d file(s) downloaded", len(files))
    return files


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run XR automation flow.")
    parser.add_argument("--username", default=os.getenv("XR_USERNAME"), help="XR portal username")
    parser.add_argument("--password", default=os.getenv("XR_PASSWORD"), help="XR portal password")
    parser.add_argument("--last-name", default=os.getenv("XR_LAST_NAME"), help="Patient last name")
    parser.add_argument("--first-name", default=os.getenv("XR_FIRST_NAME"), help="Patient first name")
    parser.add_argument("--dob", default=os.getenv("XR_DOB"), help="Patient DOB (optional)")
    parser.add_argument("--start-date", default=os.getenv("XR_START_DATE"), help="Optional start date filter")
    parser.add_argument("--end-date", default=os.getenv("XR_END_DATE"), help="Optional end date filter")


    args = parser.parse_args()

    required = [args.username, args.password, args.last_name, args.first_name]
    if not all(required):
        parser.error("XR requires username, password, last-name, first-name, and dob.")

    return args


if __name__ == "__main__":
    configuration = load_config()
    cli_args = _parse_args()
    driver_instance = create_driver(configuration)
    try:
        RunXr(
            driver_instance,
            username=cli_args.username,
            password=cli_args.password,
            last_name=cli_args.last_name,
            first_name=cli_args.first_name,
            dob=cli_args.dob,
            start_date=cli_args.start_date,
            end_date=cli_args.end_date,
        )
    except Exception as exc:
        LOGGER.exception("XR flow terminated with error: %s", exc)
        sys.exit(1)
    finally:
        try:
            driver_instance.quit()
        except Exception:
            LOGGER.warning("Unable to quit XR driver cleanly")
