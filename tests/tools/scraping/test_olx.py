import os
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock, patch

OLX_LISTING_HTML = """
<html><body>
  <div data-testid="l-card">
    <p data-testid="location-date">Warszawa - Dzisiaj o 12:34</p>
    <div data-cy="ad-card-title"><a href="/oferta/1">Nice flat</a></div>
    <p data-testid="ad-price">1 500 zł</p>
    <div data-testid="image-container"><img src="http://img/1.jpg"/></div>
  </div>
  <div data-testid="l-card">
    <p data-testid="location-date">Warszawa - Dzisiaj o 01:00</p>
    <div data-cy="ad-card-title"><a href="/oferta/2">Old flat</a></div>
  </div>
</body></html>
"""

DETAIL_HTML = """
<html><body>
  <div data-cy="ad_description">Some long description</div>
  <img data-testid="swiper-image-1" srcset="http://a.jpg 200w, http://b.jpg 800w"/>
</body></html>
"""


class TestOLXScraper(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ.setdefault("TOPN_DB_BASE_URL", "http://api")
        os.environ.setdefault("GROQ_MODEL_NAME", "dummy")
        import sys

        sys.modules.setdefault(
            "langchain_groq",
            types.SimpleNamespace(
                ChatGroq=type("ChatGroq", (), {"__init__": lambda *a, **k: None})
            ),
        )

        from tools.scraping.olx import OLXScraper

        self.OLXScraper = OLXScraper

    async def asyncTearDown(self):
        pass

    async def test_fetch_new_items_filters_and_builds_items(self):
        # Mock httpx responses for list and details
        list_resp = MagicMock(status_code=200, text=OLX_LISTING_HTML)
        detail_resp = MagicMock(status_code=200, text=DETAIL_HTML)

        with patch(
            "httpx.AsyncClient.get", new=AsyncMock(side_effect=[list_resp, detail_resp])
        ):
            # Only the first card should be considered "recent"
            with patch(
                "tools.utils.time_helpers.TimeUtils.within_last_minutes",
                side_effect=[True, False],
            ):
                scr = self.OLXScraper()
                summarizer = types.SimpleNamespace(
                    summarize=AsyncMock(return_value="sum")
                )
                items = await scr.fetch_new_items(
                    "http://olx", existing_urls=set(), summarizer=summarizer
                )

        self.assertEqual(len(items), 1)
        it = items[0]
        self.assertEqual(it.title, "Nice flat")
        self.assertEqual(it.description, "sum")
        self.assertTrue(it.item_url.startswith("https://www.olx.pl"))

    async def test_fetch_item_details_otodom_shortcut(self):
        scr = self.OLXScraper()
        desc, img = await scr._fetch_item_details(
            "http://otodom.pl/123",
            summarizer=types.SimpleNamespace(summarize=AsyncMock()),
        )
        self.assertIn("Otodom", desc)
        self.assertEqual(img, "")

    async def test_extract_helpers(self):
        from bs4 import BeautifulSoup

        scr = self.OLXScraper()
        soup = BeautifulSoup(DETAIL_HTML, "html.parser")
        img = scr._extract_highres_image(soup)
        self.assertEqual(img, "http://b.jpg")
        desc = scr._extract_description(soup)
        self.assertIn("Some long description", desc)

    async def test_parse_times(self):
        scr = self.OLXScraper()
        dt, pretty = scr._parse_times("12:00")
        self.assertIsNotNone(dt)
        self.assertIsInstance(pretty, str)
