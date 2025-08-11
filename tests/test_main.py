import importlib
import os
import types
from unittest import IsolatedAsyncioTestCase
from unittest.mock import AsyncMock, patch


class TestMain(IsolatedAsyncioTestCase):
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

    async def test_worker_main_runs_one_cycle_and_closes(self):
        mod = importlib.import_module("main")
        importlib.reload(mod)

        # Patch monitor to avoid real work
        with patch("main.ItemMonitor") as Mon:
            inst = Mon.return_value
            inst.run_once = AsyncMock()
            inst.close = AsyncMock()

            async def stop(_):
                raise asyncio.CancelledError

            import asyncio

            with patch("main.asyncio.sleep", new=stop):
                with self.assertRaises(asyncio.CancelledError):
                    await mod.worker_main()

            inst.run_once.assert_awaited()
            inst.close.assert_awaited()

    async def test_main_calls_worker_and_closes_client(self):
        mod = importlib.import_module("main")
        importlib.reload(mod)

        with patch("main.worker_main", new=AsyncMock()) as wm:
            with patch("main.close_client", new=AsyncMock()) as cc:
                await mod.main()
                wm.assert_awaited()
                cc.assert_awaited()
