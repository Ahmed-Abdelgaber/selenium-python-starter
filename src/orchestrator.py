from __future__ import annotations

import json
import os
from typing import Any, Dict
from pathlib import Path
import traceback
from datetime import datetime
import re

import boto3
from botocore.exceptions import (
    BotoCoreError,
    ClientError,
    NoCredentialsError,
    NoRegionError,
)
from selenium.common.exceptions import WebDriverException

from src.core.config import load_config
from src.core.driver_factory import create_driver
from src.core.logger import get_logger
from src.core.retry import RetryError
from src.core.storage import S3Uploader
from src.scripts.quest import RunQuest
from src.scripts.tricore import RunTricore
from src.scripts.xr import RunXr
from src.scripts.zio import RunZio

LOGGER = get_logger("orchestrator")

_SECRETS_CLIENT = None

def _is_session_alive(driver) -> bool:
    try:
        if not driver:
            return False
        sid = getattr(driver, "session_id", None)
        if not sid:
            return False
        # Cheap ping that doesn't fetch full page source
        _ = driver.current_url
        return True
    except Exception:
        return False

def _save_failure_artifacts(driver, label: str) -> None:
    try:
        out = Path("/tmp/artifacts")
        out.mkdir(parents=True, exist_ok=True)
        if not _is_session_alive(driver):
            note = out / f"{label}.txt"
            try:
                note.write_text("Driver session is not alive; no HTML/screenshot captured.")
            except Exception:
                LOGGER.warning("Could not write text artifact", exc_info=True)
            LOGGER.warning("Driver session appears dead; skipped HTML/screenshot capture.")
            return
        html_path = out / f"{label}.html"
        png_path = out / f"{label}.png"
        try:
            page = getattr(driver, "page_source", "") or ""
            html_path.write_text(page)
        except Exception:
            LOGGER.warning("Could not write HTML artifact", exc_info=True)
        try:
            driver.save_screenshot(str(png_path))
        except Exception:
            LOGGER.warning("Could not write screenshot artifact", exc_info=True)
        LOGGER.info("Saved failure artifacts to %s", out)
    except Exception:
        LOGGER.warning("Artifact save wrapper failed", exc_info=True)

SECRET_ENV_MAP = {
    "zio": os.getenv("ZIO_SECRET_ARN"),
    "xr": os.getenv("XR_SECRET_ARN"),
    "quest": os.getenv("QUEST_SECRET_ARN"),
    "tricore": os.getenv("TRICORE_SECRET_ARN"),
}

STATIC_CREDENTIAL_MAP: Dict[str, Dict[str, str]] = {
    "xr": {"username": "sneelagaru", "password": "Medical8"},
    "quest": {"username": "sneelagaru", "password": "Menaul11311$$"},
    "zio": {"username": "suresh@nitovo.com", "password": "Menaul11311+"},
    "tricore": {"username": "sneelagaru", "password": "Menaul11311%"},
}

FLOW_MAP = {
    "xr": RunXr,
    "quest": RunQuest,
    "zio": RunZio,
    "tricore": RunTricore,
}


def _resolve_credentials(site: str, payload_credentials: Dict[str, Any] | None) -> tuple[str, str]:
    if payload_credentials:
        username = payload_credentials.get("username")
        password = payload_credentials.get("password")
        if username and password:
            return str(username), str(password)
        raise ValueError("credentials.username and credentials.password must both be provided when using inline credentials")

    secret_error: Exception | None = None
    secret_arn = SECRET_ENV_MAP.get(site)
    if secret_arn:
        try:
            secrets_client = _get_secrets_client()
            response = secrets_client.get_secret_value(SecretId=secret_arn)
            if "SecretString" in response:
                secret_payload = response["SecretString"]
            else:
                secret_payload = response.get("SecretBinary", b"").decode("utf-8")

            secret_data = json.loads(secret_payload)
            username = secret_data.get("username")
            password = secret_data.get("password")
            if not username or not password:
                raise ValueError(
                    f"Credentials secret for site '{site}' must contain 'username' and 'password' fields"
                )
            return str(username), str(password)
        except (ClientError, NoCredentialsError, NoRegionError, BotoCoreError, json.JSONDecodeError, ValueError) as exc:
            secret_error = exc
            LOGGER.warning(
                "Falling back to static credentials for site '%s' after secret lookup failure: %s",
                site,
                exc,
            )

    static_creds = STATIC_CREDENTIAL_MAP.get(site)
    if static_creds:
        return str(static_creds["username"]), str(static_creds["password"])

    if secret_error:
        raise RuntimeError(
            f"Unable to resolve credentials for site '{site}' using secret and no static fallback available."
        ) from secret_error

    raise ValueError(
        f"Credentials not provided and no secret ARN or static credentials configured for site '{site}'."
    )


def _normalize_report_date(value: str | None) -> str:
    if not value:
        return datetime.utcnow().strftime("%Y%m%d")
    digits = re.sub(r"[^0-9]", "", value)
    if len(digits) >= 8:
        return digits[:8]
    if digits:
        return digits
    return datetime.utcnow().strftime("%Y%m%d")


def handler(event: Dict[str, Any], context: Any = None) -> Dict[str, Any]:
    LOGGER.info("Automation request payload: %s", json.dumps(event))

    site = event.get("site") or event.get("site_name")
    if not site:
        raise ValueError("'site' is required in the payload")

    site = str(site).strip().lower()
    if site not in FLOW_MAP:
        raise ValueError(f"Unsupported site '{site}'. Expected one of: {', '.join(FLOW_MAP)}")

    username, password = _resolve_credentials(site, event.get("credentials"))

    patient = event.get("patient", {})
    if not isinstance(patient, dict):
        raise ValueError("'patient' must be an object with patient metadata")

    first_name = patient.get("first_name")
    last_name = patient.get("last_name")
    dob = patient.get("dob")
    if not first_name or not last_name:
        raise ValueError("patient.first_name and patient.last_name are required")

    if site == "quest" and not dob:
        raise ValueError("patient.dob is required for quest site")

    if site == "tricore":
        if not dob:
            raise ValueError("patient.dob is required for tricore site")

    flow_options = event.get("options", {}) or {}
    start_date = flow_options.get("start_date")
    end_date = flow_options.get("end_date")
    gender = flow_options.get("gender")
    if site == "tricore" and not gender:
        raise ValueError("options.gender is required for tricore site")

    cfg = load_config()
    driver = create_driver(cfg)
    uploader = S3Uploader.from_config(cfg)
    patient_full_name = f"{first_name} {last_name}".strip()
    report_date_source = (
        event.get("report_date")
        or flow_options.get("report_date")
        or flow_options.get("start_date")
        or flow_options.get("end_date")
        or ""
    )
    report_date = _normalize_report_date(report_date_source)
    try:
        LOGGER.info("Running flow '%s'", site)
        flow = FLOW_MAP[site]

        if site == "zio":
            files = flow(
                driver,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
            )
        elif site == "xr":
            files = flow(
                driver,
                username=username,
                password=password,
                last_name=last_name,
                first_name=first_name,
                dob=dob,
                start_date=start_date,
                end_date=end_date,
            )
        elif site == "quest":
            files = flow(
                driver,
                username=username,
                password=password,
                patient_name=f"{first_name} {last_name}",
                patient_dob=dob,
            )
        elif site == "tricore":
            files = flow(
                driver,
                username=username,
                password=password,
                first_name=first_name,
                last_name=last_name,
                dob=dob,
                gender=gender,
            )
        else:
            raise ValueError("No automation site selected; 'site' must be one of xr, quest, zio, tricore")

        files = list(files or [])
        LOGGER.info("Flow '%s' produced %d file(s)", site, len(files))

        s3_objects = []
        if uploader and files:
            uploaded = uploader.upload_files(
                site,
                files,
                patient_name=patient_full_name,
                report_date=report_date,
            )
            for obj in uploaded:
                s3_objects.append(
                    {
                        "s3_file_name": obj.report_name,
                        "s3_file_url": obj.s3_uri,
                        "s3_file_download": obj.download_url or obj.s3_uri,
                        "s3_console_url": obj.console_url,
                    }
                )

        return {
            "site": site,
            "site_name": site,
            "count": len(files),
            "patient_name": patient_full_name,
            "report_date": report_date,
            "patient_files": s3_objects,
        }
    except RetryError as exc:
        # Try to extract the original/root exception for clearer logs
        root = getattr(exc, "last_exception", None) or getattr(exc, "__cause__", None) or getattr(exc, "__context__", None)
        if root:
            LOGGER.error("Flow '%s' failed after retries. Root cause: %r", site, root, exc_info=True)
        else:
            LOGGER.error("Flow '%s' failed after retries.", site, exc_info=True)

        try:
            _save_failure_artifacts(driver, f"{site}_final_failure")
        except Exception:
            LOGGER.warning("Unable to persist failure artifacts for '%s'", site, exc_info=True)

        # Re-raise with root cause string if available so CloudWatch shows the actionable error
        message = f"{site} flow failed after retries: {root or exc}"
        raise RuntimeError(message) from (root or exc)
    except Exception as exc:
        LOGGER.exception("Unhandled error while running flow '%s'", site)
        try:
            _save_failure_artifacts(driver, f"{site}_unexpected_failure")
        except Exception:
            LOGGER.warning("Unable to persist unexpected failure artifacts for '%s'", site, exc_info=True)
        raise
    finally:
        try:
            driver.quit()
        except Exception:
            LOGGER.warning("Unable to quit driver cleanly for '%s'", site, exc_info=True)
def _get_secrets_client():
    global _SECRETS_CLIENT
    if _SECRETS_CLIENT is not None:
        return _SECRETS_CLIENT

    region = os.getenv("AWS_REGION") or os.getenv("AWS_DEFAULT_REGION")
    client_kwargs = {}
    if region:
        client_kwargs["region_name"] = region

    _SECRETS_CLIENT = boto3.client("secretsmanager", **client_kwargs)
    return _SECRETS_CLIENT
