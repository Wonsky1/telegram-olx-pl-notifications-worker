"""Scraper implementation for OLX marketplace listings."""

from __future__ import annotations

import logging
import time
from datetime import datetime
from typing import List, Set

import pytz
import requests
from bs4 import BeautifulSoup

from core.config import settings
from tools.models import Item
from tools.processing.description import DescriptionSummarizer
from tools.utils.time_helpers import TimeUtils
from .base import BaseScraper

logger = logging.getLogger(__name__)


class OLXScraper(BaseScraper):
    """OLX marketplace scraper.

    Designed to reproduce the original behaviour previously located in
    `tools.utils.get_new_items` and `tools.utils.get_item_description`.
    """

    HEADERS = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
        "Accept-Encoding": "gzip, deflate, br, zstd",
        "Accept-Language": "pl-PL,pl;q=0.9,en-GB;q=0.8,en;q=0.7",
        "Cache-Control": "max-age=0",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/126.0.0.0 Safari/537.36",
        "X-Forwarded-For": "83.0.0.0",  # Polish IP range to get Polish timezone
        "CF-IPCountry": "PL",
    }

    async def fetch_new_items(
        self,
        url: str,
        existing_urls: Set[str],
        summarizer: DescriptionSummarizer,
    ) -> List[Item]:
        logger.info("Fetching OLX items from %s", url)

        response = requests.get(url, headers=self.HEADERS)
        logger.debug("OLX response status code: %s", response.status_code)
        soup = BeautifulSoup(response.text, "html.parser")
        divs = soup.find_all("div", attrs={"data-testid": "l-card"})

        new_items: List[Item] = []
        skipped_count = 0
        for div in divs:
            location_date = div.find("p", attrs={"data-testid": "location-date"}).get_text(strip=True)
            if "Dzisiaj" not in location_date:
                logger.debug("Skipping non-today item: %s", location_date)
                continue

            location, time_str = location_date.split("Dzisiaj o ")
            location = location.strip().rstrip("-").strip()

            if not TimeUtils.within_last_minutes(time_str):
                logger.debug("Skipping old item at %s", time_str)
                continue

            title_div = div.find("div", attrs={"data-cy": "ad-card-title"})
            a_tag = title_div.find("a")
            item_url = a_tag["href"]
            if not item_url.startswith("http"):
                item_url = "https://www.olx.pl" + item_url

            if item_url in existing_urls:
                skipped_count += 1
                continue

            title = a_tag.get_text(strip=True)

            price_div = div.find("p", attrs={"data-testid": "ad-price"})
            price = price_div.get_text(strip=True) if price_div else "Brak ceny"

            image_div = div.find("div", attrs={"data-testid": "image-container"})
            image_url = image_div.find("img")["src"] if image_div else ""

            description = await self._process_description(item_url, summarizer)

            created_at, created_at_pretty = self._parse_times(time_str)

            new_items.append(
                Item(
                    title=title,
                    price=price,
                    location=location,
                    created_at=created_at,
                    created_at_pretty=created_at_pretty,
                    image_url=image_url,
                    item_url=item_url,
                    description=description,
                )
            )

        logger.info("OLX scraper found %s new items, skipped %s existing", len(new_items), skipped_count)
        return new_items

    async def _process_description(self, item_url: str, summarizer: DescriptionSummarizer) -> str:
        if "otodom" in item_url:
            return "Otodom link will be implemented soon"

        try:
            raw_desc = self._get_item_description(item_url)
            summary = await summarizer.summarize(raw_desc)
            return summary or raw_desc[:500]  # Fallback to raw if summariser empty
        except Exception as exc:  # pragma: no cover
            logger.error("Failed to load description for %s: %s", item_url, exc)
            return f"Failed to load description: {exc}"

    @staticmethod
    def _get_item_description(item_url: str) -> str:
        response = requests.get(item_url)
        soup = BeautifulSoup(response.text, "html.parser")
        description_tag = soup.find("div", attrs={"data-cy": "ad_description"})
        return description_tag.get_text(strip=True) if description_tag else ""

    @staticmethod
    def _parse_times(time_str: str):
        parsed_time = datetime.strptime(time_str, "%H:%M").time()
        utc_tz = pytz.UTC
        now_utc = datetime.now(utc_tz)
        datetime_provided_utc = utc_tz.localize(datetime.combine(now_utc.date(), parsed_time))
        poland_tz = pytz.timezone("Europe/Warsaw")
        datetime_provided_pl = datetime_provided_utc.astimezone(poland_tz)
        datetime_naive_pl = datetime_provided_pl.replace(tzinfo=None)
        created_at_pretty = datetime_provided_pl.strftime("%d.%m.%Y - *%H:%M*")
        return datetime_naive_pl, created_at_pretty
