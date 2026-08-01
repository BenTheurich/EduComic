"""Fixed local provider capabilities and secret readiness checks."""

import os


DEFAULT_OPENAI_MODEL = "gpt-5.6-terra"
DEFAULT_BFL_MODEL = "flux-2-pro"
CURRENT_OPENAI_MODELS = frozenset({"gpt-5.6-sol", DEFAULT_OPENAI_MODEL, "gpt-5.6-luna"})
SUPPORTED_OPENAI_MODELS = CURRENT_OPENAI_MODELS | {"gpt-5.1"}
SUPPORTED_BFL_MODELS = frozenset({DEFAULT_BFL_MODEL, "flux-2-flex"})


def require_supported_model(model: str, supported: frozenset[str], provider: str) -> str:
    if model not in supported:
        raise ValueError(f"Unsupported {provider} model")
    return model


def configured_secret(name: str) -> bool:
    value = os.getenv(name, "").strip()
    return bool(value and not value.startswith("<") and not value.startswith("YOUR_"))
