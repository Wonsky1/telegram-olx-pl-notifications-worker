import importlib
import os
import types
from unittest import IsolatedAsyncioTestCase


class TestSettings(IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        os.environ.setdefault("TOPN_DB_BASE_URL", "http://api")

    async def asyncTearDown(self):
        pass

    async def test_validator_requires_model_name(self):
        import sys

        # Provide stub ChatGroq
        sys.modules["langchain_groq"] = types.SimpleNamespace(
            ChatGroq=type("ChatGroq", (), {"__init__": lambda *a, **k: None})
        )
        # Ensure no GROQ_MODEL_NAME -> constructing Settings should raise
        os.environ.pop("GROQ_MODEL_NAME", None)
        core = importlib.import_module("core.config")
        # Disable reading from .env to simulate truly missing env var
        try:
            core.Settings.model_config["env_file"] = None
        except Exception:
            pass
        try:
            _ = core.Settings()
        except Exception as e:
            self.assertIsInstance(e, ValueError)
        else:
            self.fail("Expected ValueError when GROQ_MODEL_NAME missing")

    async def test_settings_with_model_name(self):
        import sys

        sys.modules["langchain_groq"] = types.SimpleNamespace(
            ChatGroq=type("ChatGroq", (), {"__init__": lambda *a, **k: None})
        )
        os.environ["GROQ_MODEL_NAME"] = "foo"
        core = importlib.import_module("core.config")
        s = core.Settings()
        # GENERATIVE_MODEL should be set (instance of stub class)
        self.assertIsNotNone(s.GENERATIVE_MODEL)
