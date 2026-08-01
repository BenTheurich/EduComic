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
    "BFL_MODEL_ENDPOINT",
    "ALLOWED_ORIGINS",
    "DATABASE_URL",
    "EDUCOMIC_DATA_DIR",
)


def pytest_sessionstart(session):
    for name in CONFIG_VARS:
        os.environ.pop(name, None)

    dotenv = ModuleType("dotenv")
    dotenv.load_dotenv = lambda *args, **kwargs: False
    sys.modules["dotenv"] = dotenv

    openai = ModuleType("openai")
    openai.OpenAI = lambda *args, **kwargs: object()
    sys.modules["openai"] = openai
