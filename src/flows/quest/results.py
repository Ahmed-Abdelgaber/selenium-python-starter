from __future__ import annotations

import os
from typing import List
import time

from src.core.config import load_config
from src.core.logger import get_logger
from src.core.pdf_download import (
    allow_downloads_cdp,
    rename_downloaded_file,
    snapshot_downloads,
    wait_for_new_download,
    clean_download_dir
)
from src.pages.quest.quest_results_page import QuestSearchPage


class QuestResultsFlow:
    def __init__(self, driver) -> None:
        self.driver = driver
        self.logger = get_logger("flows.quest.results")
        self.download_dir = load_config().download_quest_dir

    def download_results(self) -> List[str]:
        """
        Loop over each Quest result card, download the corresponding file, rename it
        using the card's derived file name, and return the list of downloaded names.
        """
        self.logger.info("Starting Quest results download flow")
        page = QuestSearchPage(self.driver)
        cards = page.get_cards()

        if not cards:
            self.logger.warning("No Quest result cards found to download")
            return []

        allow_downloads_cdp(self.driver, self.download_dir)
        clean_download_dir(self.download_dir, only_extensions=(".pdf",))

        downloaded_files: List[str] = []

        for idx, card in enumerate(cards):
            card_number = idx + 1
            self.logger.info("Processing Quest result card %s", card_number)
            try:
                page.scroll_to_card(card)
                page.select_card(card)
                file_name = page.get_file_name(card, idx)

                before = snapshot_downloads(self.download_dir)
                page.click_print()
                time.sleep(5)
                page.click_open_in_interstitial()
                time.sleep(7)
                downloaded_path = wait_for_new_download(self.download_dir, before)
                if not downloaded_path:
                    raise TimeoutError("Timed out waiting for Quest result download")

                final_path = rename_downloaded_file(
                    downloaded_path,
                    self.download_dir,
                    file_name,
                )
                downloaded_name = os.path.basename(final_path)
                downloaded_files.append(str(final_path))
                self.logger.info(
                    "Downloaded Quest result card %s as '%s'",
                    card_number,
                    downloaded_name,
                )
                page.close_print_dialog()
            except Exception as exc:
                self.logger.exception("Failed to download Quest result card %s: %s", card_number, exc)
            finally:
                try:
                    if page._is_checked(card):  # type: ignore[attr-defined]
                        label = card.find_element(*page.CARD_CHECKBOX_LABEL)
                        self.driver.execute_script("arguments[0].click();", label)
                except Exception:
                    pass

        self.logger.info("Completed Quest results download flow; %s file(s) saved", len(downloaded_files))
        return downloaded_files
