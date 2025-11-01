# utils/pdf_download.py
import os
import time
from pathlib import Path
from typing import Optional, Set
import re
import shutil



def allow_downloads_cdp(driver, download_dir: str):
    """
    Enable downloads in headless/new-headless via Chrome DevTools Protocol (CDP).
    Call this after creating the driver and before triggering the PDF navigation.
    """
    download_dir = str(Path(download_dir).resolve())
    try:
        driver.execute_cdp_cmd(
            "Page.setDownloadBehavior",
            {"behavior": "allow", "downloadPath": download_dir},
        )
    except Exception:
        # Some Selenium/Chrome versions don't require or allow this; ignore failures.
        pass


def snapshot_downloads(download_dir: str) -> Set[str]:
    """
    Take a quick snapshot (set of file names) of the download directory before the download starts.
    """
    p = Path(download_dir)
    p.mkdir(parents=True, exist_ok=True)
    return set(os.listdir(p))


def wait_for_new_download(download_dir: str, before: Set[str], timeout: int = 60) -> Optional[str]:
    """
    Wait until a new file appears in the download directory (excluding .crdownload files).
    Returns the absolute path of the new file, or None on timeout.
    """
    download_path = Path(download_dir)
    waited = 0
    while waited < timeout:
        time.sleep(1)
        waited += 1
        if not download_path.exists():
            continue

        current = set(os.listdir(download_path))
        new_files = [f for f in (current - before) if not f.endswith(".crdownload")]
        if new_files:
            # If multiple files arrive, return the first by name ordering.
            fname = sorted(new_files)[0]
            return str(download_path / fname)

    return None
  

def sanitize_filename(name: str, max_length: int = 180) -> str:
    """
    Make a filename safe for most filesystems:
    - Replace disallowed chars with underscores
    - Collapse repeated underscores/spaces
    - Trim and truncate to max_length
    """
    if not name:
        return "file"

    # Replace forbidden characters
    safe = re.sub(r"[^\w\-. ]+", "_", name, flags=re.UNICODE)
    # Collapse multiple underscores/spaces
    safe = re.sub(r"[ _]+", "_", safe).strip("._ ")
    if not safe:
        safe = "file"

    # Truncate while preserving extension if present
    base = safe
    ext = ""
    if "." in safe:
        p = Path(safe)
        base, ext = p.stem, p.suffix
    if len(base) > max_length:
        base = base[:max_length]
    safe = f"{base}{ext}"

    # Avoid reserved names on Windows (harmless elsewhere)
    reserved = {"CON", "PRN", "AUX", "NUL"} | {f"COM{i}" for i in range(1, 10)} | {f"LPT{i}" for i in range(1, 10)}
    if safe.upper().split(".")[0] in reserved:
        safe = f"_{safe}"

    return safe or "file"

def rename_downloaded_file(
    downloaded_path: str,
    target_dir: str,
    desired_name: str,
    *,
    overwrite: bool = False,
    keep_extension: bool = True,
) -> str:
    """
    Rename/move the downloaded file to `target_dir / desired_name` safely.

    Behavior:
    - If `desired_name` contains an extension, it will be used as-is.
    - If `desired_name` has no extension:
        - Use the source file's extension when `keep_extension=True`.
        - Otherwise, no extension will be appended.
    - When `overwrite=False`, a numeric suffix (_1, _2, ...) is added if the target exists.

    Returns the absolute path of the final file.
    """
    src = Path(downloaded_path).resolve()
    if not src.exists():
        raise FileNotFoundError(f"Downloaded file not found: {src}")

    target_dir = Path(target_dir).resolve()
    target_dir.mkdir(parents=True, exist_ok=True)

    desired_path = Path(desired_name)
    if desired_path.suffix:
        base_name = desired_path.name  # use provided extension
    else:
        ext = src.suffix if keep_extension else ""
        base_name = f"{desired_path.name}{ext}"

    base_name = sanitize_filename(base_name)
    target = target_dir / base_name

    if not overwrite:
        # De-duplicate by appending _1, _2, ...
        if target.exists():
            stem = target.stem
            ext = target.suffix
            i = 1
            while True:
                candidate = target_dir / f"{stem}_{i}{ext}"
                if not candidate.exists():
                    target = candidate
                    break
                i += 1

    # Use shutil.move to handle cross-filesystem moves gracefully
    target = target.resolve()
    shutil.move(str(src), str(target))
    return str(target)

def clean_download_dir(download_dir: str, *, only_extensions: tuple[str, ...] = (), remove_subdirs: bool = False) -> int:
    """
    Remove existing files from the download directory.
    - only_extensions: optional tuple like (".pdf",) to limit deletions.
    - remove_subdirs: if True, delete sub-directories recursively.
    Returns the number of removed entries.
    """
    path = Path(download_dir).resolve()
    path.mkdir(parents=True, exist_ok=True)

    removed = 0
    exts = tuple(e.lower() for e in only_extensions)

    for entry in path.iterdir():
        try:
            if entry.is_file():
                # Skip in-progress Chrome downloads
                if entry.suffix.lower() == ".crdownload":
                    continue
                if exts and entry.suffix.lower() not in exts:
                    continue
                entry.unlink()
                removed += 1
            elif entry.is_dir() and remove_subdirs:
                shutil.rmtree(entry)
                removed += 1
        except Exception:
            # Ignore failures; continue cleaning others
            continue

    return removed

def download_pdf_from_preview(driver, pdf_url: str, download_dir: str, timeout: int = 60) -> Optional[str]:
    """
    Open the PDF URL in a new tab (Chrome may try to preview it),
    but due to the configured prefs it will be downloaded automatically.
    Returns the absolute path of the downloaded file, or None on timeout.
    """
    before = snapshot_downloads(download_dir)
    allow_downloads_cdp(driver, download_dir)
    driver.execute_script("window.open(arguments[0], '_blank');", pdf_url)
    return wait_for_new_download(download_dir, before, timeout=timeout)
