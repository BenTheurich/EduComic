"""Fixed local provider capabilities and secret readiness checks."""

import os


SUPPORTED_OPENAI_MODELS = frozenset({"gpt-5.1"})
SUPPORTED_BFL_MODELS = frozenset({"flux-2-pro"})


def require_supported_model(model: str, supported: frozenset[str], provider: str) -> str:
    if model not in supported:
        raise ValueError(f"Unsupported {provider} model")
    return model


def configured_secret(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and not value.startswith("<") and not value.startswith("YOUR_"))
