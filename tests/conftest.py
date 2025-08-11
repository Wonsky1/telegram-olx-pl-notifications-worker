import os
import sys
import types

# Ensure necessary env vars for config
os.environ.setdefault("TOPN_DB_BASE_URL", "http://api")
# Provide a default model name so Settings() validator succeeds
os.environ.setdefault("GROQ_MODEL_NAME", "dummy-model")

# Stub langchain_groq to avoid requiring actual package/runtime
if "langchain_groq" not in sys.modules:
    sys.modules["langchain_groq"] = types.SimpleNamespace(
        ChatGroq=type("ChatGroq", (), {"__init__": lambda *a, **k: None})
    )
