from dataclasses import dataclass
import os
from pathlib import Path
from typing import Optional

from dotenv import load_dotenv

def _to_bool(val: str | None, default: bool = False) -> bool:
    if val is None:
        return default
    return str(val).strip().lower() in {"1", "true", "yes", "y", "on"}

@dataclass(frozen=True)
class Config:
    base_url: str
    browser: str
    headless: bool
    incognito: bool
    window_width: int
    window_height: int
    wait_timeout: int
    page_load_timeout: int
    download_quest_dir: str
    download_zio_dir: str
    download_xr_dir: str
    download_tricore_dir: str
    download_s3_bucket: str | None = None
    download_s3_prefix: str | None = None
    download_s3_prefix_zio: str | None = None
    download_s3_prefix_xr: str | None = None
    download_s3_prefix_quest: str | None = None
    download_s3_prefix_tricore: str | None = None
    download_s3_region: str | None = None
    download_s3_url_expiration: int | None = None
    download_s3_direct: bool = False

def load_config(cli: dict | None = None) -> Config:
    """
    Merge precedence: CLI opts > .env > defaults
    """
    load_dotenv(override=False)

    def _env(k: str, default: str | None = None) -> str | None:
        return os.getenv(k, default)

    base = {
        "base_url": _env("BASE_URL", "https://example.com"),
        "browser": _env("BROWSER", "chrome"),
        "headless": _to_bool(_env("HEADLESS", "true")),
        "incognito": _to_bool(_env("INCOGNITO", "false")),
        "window_width": int(_env("WINDOW_WIDTH", "1280")),
        "window_height": int(_env("WINDOW_HEIGHT", "800")),
        "wait_timeout": int(_env("WAIT_TIMEOUT", "10")),
        "page_load_timeout": int(_env("PAGE_LOAD_TIMEOUT", "30")),
        "download_quest_dir": _env("DOWNLOAD_QUEST_DIR", "downloads/quest"),
        "download_zio_dir": _env("DOWNLOAD_ZIO_DIR", "downloads/zio"),
        "download_xr_dir": _env("DOWNLOAD_XR_DIR", "downloads/xr"),
        "download_tricore_dir": _env("DOWNLOAD_TRICORE_DIR", "downloads/tricore"),
        "download_s3_bucket": _env("DOWNLOAD_S3_BUCKET"),
        "download_s3_prefix": _env("DOWNLOAD_S3_PREFIX"),
        "download_s3_prefix_zio": _env("DOWNLOAD_S3_PREFIX_ZIO"),
        "download_s3_prefix_xr": _env("DOWNLOAD_S3_PREFIX_XR"),
        "download_s3_prefix_quest": _env("DOWNLOAD_S3_PREFIX_QUEST"),
        "download_s3_prefix_tricore": _env("DOWNLOAD_S3_PREFIX_TRICORE"),
        "download_s3_region": _env("DOWNLOAD_S3_REGION"),
        "download_s3_url_expiration": _env("DOWNLOAD_S3_URL_EXPIRATION"),
        "download_s3_direct": _env("DOWNLOAD_S3_DIRECT"),
    }

    cli = cli or {}
    merged = {
        **base,
        **{k: v for k, v in cli.items() if v is not None},
    }

    for key in ("download_quest_dir", "download_zio_dir", "download_xr_dir", "download_tricore_dir"):
        path_value = merged.get(key)
        if isinstance(path_value, str):
            merged[key] = str(Path(path_value).expanduser().resolve())

    s3_string_fields = (
        "download_s3_bucket",
        "download_s3_prefix",
        "download_s3_prefix_zio",
        "download_s3_prefix_xr",
        "download_s3_prefix_quest",
        "download_s3_prefix_tricore",
        "download_s3_region",
    )

    for key in s3_string_fields:
        value = merged.get(key)
        if isinstance(value, str):
            stripped = value.strip()
            merged[key] = stripped or None

    exp_value: Optional[str | int | None] = merged.get("download_s3_url_expiration")
    if isinstance(exp_value, str):
        cleaned = exp_value.strip()
        lowered = cleaned.lower()
        if not cleaned or lowered in {"no expiry", "no_expiry", "none", "never", "null"}:
            merged["download_s3_url_expiration"] = None
        else:
            try:
                merged["download_s3_url_expiration"] = int(cleaned)
            except ValueError as exc:
                raise ValueError(
                    "DOWNLOAD_S3_URL_EXPIRATION must be an integer number of seconds or unset"
                ) from exc

    direct_val = merged.get("download_s3_direct")
    if isinstance(direct_val, str):
        merged["download_s3_direct"] = _to_bool(direct_val, default=False)
    elif direct_val is None:
        merged["download_s3_direct"] = False

    return Config(**merged)  # type: ignore[arg-type]
