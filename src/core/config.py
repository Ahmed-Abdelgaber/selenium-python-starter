from dataclasses import dataclass
import os
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
    window_width: int
    window_height: int
    wait_timeout: int
    page_load_timeout: int
    download_quest_dir: str

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
        "window_width": int(_env("WINDOW_WIDTH", "1280")),
        "window_height": int(_env("WINDOW_HEIGHT", "800")),
        "wait_timeout": int(_env("WAIT_TIMEOUT", "10")),
        "page_load_timeout": int(_env("PAGE_LOAD_TIMEOUT", "30")),
        "download_quest_dir": _env("DOWNLOAD_QUEST_DIR", "/downloads/quest"),
    }

    cli = cli or {}
    merged = {
        **base,
        **{k: v for k, v in cli.items() if v is not None},
    }

    return Config(**merged)  # type: ignore[arg-type]
