import os
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, MagicMock


class TestDescriptionSummarizer(IsolatedAsyncioTestCase):
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
        from tools.processing.description import DescriptionSummarizer, settings

        self.DescriptionSummarizer = DescriptionSummarizer
        self.settings = settings

    async def asyncTearDown(self):
        pass

    async def test_summarize_returns_content(self):
        s = self.DescriptionSummarizer()
        fake_resp = MagicMock(content="summary")
        self.settings.GENERATIVE_MODEL = types.SimpleNamespace(
            ainvoke=AsyncMock(return_value=fake_resp)
        )
        res = await s.summarize("desc")
        self.assertEqual(res, "summary")

    async def test_summarize_handles_exception(self):
        s = self.DescriptionSummarizer()
        self.settings.GENERATIVE_MODEL = types.SimpleNamespace(
            ainvoke=AsyncMock(side_effect=RuntimeError("x"))
        )
        res = await s.summarize("desc")
        self.assertEqual(res, "")
