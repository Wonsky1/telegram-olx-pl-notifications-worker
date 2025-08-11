import os
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import patch


class TestClientsInit(IsolatedAsyncioTestCase):
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

    async def asyncTearDown(self):
        pass

    async def test_get_and_close_client(self):
        import importlib

        with patch("httpx.AsyncClient", autospec=True) as ac:
            # Re-import to ensure fresh module state
            mod = importlib.import_module("clients")
            importlib.reload(mod)

            client = mod.get_client()
            ac.assert_called()
            self.assertIsNotNone(client)

            await mod.close_client()
            # Ensure aclose called on created client
            client.aclose.assert_awaited()

    async def test_topn_db_client_is_instantiated(self):
        import importlib

        with patch("httpx.AsyncClient", autospec=True) as ac:
            mod = importlib.import_module("clients")
            importlib.reload(mod)
            # topn_db_client should be present
            self.assertTrue(hasattr(mod, "topn_db_client"))
            # get_client called during creation
            ac.assert_called()
