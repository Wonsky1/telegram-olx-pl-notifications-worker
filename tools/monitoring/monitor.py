"""High-level orchestrator that periodically scrapes items and persists them.

This is a refactor of the original `tools.utils.find_new_items` function.
"""

from __future__ import annotations

import asyncio
import logging
from datetime import datetime
from typing import Type

import pytz
from sqlalchemy.orm import Session

from db.database import ItemRecord, MonitoringTask
from tools.models import Item
from tools.processing.description import DescriptionSummarizer
from tools.scraping.base import BaseScraper

logger = logging.getLogger(__name__)


class ItemMonitor:
    """Periodically checks all `MonitoringTask` URLs using the provided scraper."""

    def __init__(
        self,
        db: Session,
        scraper_cls: Type[BaseScraper],
        cycle_sleep_seconds: int = 3,
    ) -> None:
        self.db = db
        self.scraper: BaseScraper = scraper_cls()
        self.summarizer = DescriptionSummarizer()
        self.cycle_sleep_seconds = cycle_sleep_seconds

    async def run_once(self):
        """Scrape each task URL once and persist new items."""
        distinct_urls = self.db.query(MonitoringTask.url).distinct().all()
        logger.info("ItemMonitor starting scraping loop for %s URLs", len(distinct_urls))

        for (url,) in distinct_urls:
            try:
                existing_urls = {u for (u,) in self.db.query(ItemRecord.item_url).all()}
                new_items = await self.scraper.fetch_new_items(
                    url=url,
                    existing_urls=existing_urls,
                    summarizer=self.summarizer,
                )
            except Exception as exc:
                logger.error("Failed fetching items for %s: %s", url, exc, exc_info=True)
                continue

            self._persist_items(new_items, source_url=url)
            logger.info("URL %s processed; added %s new items", url, len(new_items))

            await asyncio.sleep(self.cycle_sleep_seconds)

        logger.info("ItemMonitor finished all URLs")

    def _persist_items(self, items: list[Item], source_url: str):
        poland_tz = pytz.timezone("Europe/Warsaw")
        for item in items:
            item_record = ItemRecord(
                item_url=item.item_url,
                title=item.title,
                price=item.price,
                location=item.location,
                created_at=item.created_at,
                created_at_pretty=item.created_at_pretty,
                image_url=item.image_url,
                description=item.description,
                source_url=source_url,
                first_seen=datetime.now(poland_tz).replace(tzinfo=None),
            )
            self.db.add(item_record)
            self.db.commit()
            logger.info("New item persisted: %s | %s", item.title, item.item_url)

    async def close(self):
        await self.scraper.close()
