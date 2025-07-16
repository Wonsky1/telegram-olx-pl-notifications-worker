"""Abstract base class for all scrapers.

Allows us to plug additional marketplaces in the future simply by
subclassing `BaseScraper` and implementing the abstract methods.
"""

from __future__ import annotations

import abc
from typing import List, Set

from tools.models import Item
from tools.processing.description import DescriptionSummarizer  # noqa: F401 pylint: disable=cyclic-import


class BaseScraper(abc.ABC):
    """Interface that every marketplace‐specific scraper must implement."""

    @abc.abstractmethod
    async def fetch_new_items(
        self,
        url: str,
        existing_urls: Set[str],
        summarizer: "DescriptionSummarizer",
    ) -> List[Item]:
        """Return a list of *new* `Item` objects collected from *url*.

        Args:
            url: Marketplace search / listing URL.
            existing_urls: A set of already processed item URLs (deduplication).
            summarizer: Helper used to summarise raw item descriptions.
        """

    async def close(self):  # pragma: no cover
        """Override if the scraper keeps any open connections / sessions."""
        return None
