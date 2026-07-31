"""Keep backend smoke tests isolated from local credentials and providers."""

import os
import sys
from types import ModuleType

CONFIG_VARS = (
    "SUPABASE_URL",
    "SUPABASE_KEY",
    "SUPABASE_IMAGES_BUCKET",
    "OPENAI_API_KEY",
    "OPENAI_MODEL",
    "OPENAI_QA_MODEL",
    "BFL_API_KEY",
    "BLACK_FOREST_API_KEY",
    "BFL_API_BASE",
    "BFL_MODEL_ENDPOINT",
    "ALLOWED_ORIGINS",
)


class FakeSupabaseClient:
    def table(self, *_args, **_kwargs):
        raise AssertionError("database client must not be used by health checks")


created_supabase_clients = []


def pytest_sessionstart(session):
    for name in CONFIG_VARS:
        os.environ.pop(name, None)

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: False
    sys.modules["dotenv"] = dotenv

    supabase = ModuleType("supabase")
    supabase.Client = FakeSupabaseClient
    supabase.create_client = lambda *args: created_supabase_clients.append(args) or FakeSupabaseClient()
    sys.modules["supabase"] = supabase

    openai = ModuleType("openai")
    openai.OpenAI = lambda *args, **kwargs: object()
    sys.modules["openai"] = openai
