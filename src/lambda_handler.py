from __future__ import annotations

import json
import os
from typing import Any, Dict
from pathlib import Path
import traceback

import boto3
from botocore.exceptions import ClientError
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

LOGGER = get_logger("lambda")

_SECRETS_CLIENT = boto3.client("secretsmanager")

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

    secret_arn = SECRET_ENV_MAP.get(site)
    if not secret_arn:
        raise ValueError(
            f"Credentials not provided and no secret ARN configured for site '{site}'. Set the {site.upper()}_SECRET_ARN environment variable."
        )

    try:
        response = _SECRETS_CLIENT.get_secret_value(SecretId=secret_arn)
    except ClientError as exc:
        raise RuntimeError(f"Unable to retrieve credentials secret for site '{site}': {exc}") from exc

    if "SecretString" in response:
        secret_payload = response["SecretString"]
    else:
        secret_payload = response.get("SecretBinary", b"").decode("utf-8")

    try:
        secret_data = json.loads(secret_payload)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Credentials secret for site '{site}' is not valid JSON") from exc

    username = secret_data.get("username")
    password = secret_data.get("password")
    if not username or not password:
        raise ValueError(
            f"Credentials secret for site '{site}' must contain 'username' and 'password' fields"
        )

    return str(username), str(password)


def handler(event: Dict[str, Any], context: Any) -> Dict[str, Any]:
    LOGGER.info("Lambda invocation payload: %s", json.dumps(event))

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
            uploaded = uploader.upload_files(site, files)
            for obj in uploaded:
                s3_objects.append(
                    {
                        "s3_file_name": obj.key.split("/")[-1],
                        "s3_file_url": obj.url or obj.s3_uri,
                        "s3_uri": obj.s3_uri,
                    }
                )

        return {
            "site": site,
            "count": len(files),
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
