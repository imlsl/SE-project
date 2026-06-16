from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


_ADDON_DIR = Path(__file__).resolve().parent


def _load_dotenv(dotenv_path: Path) -> None:
    """Load simple KEY=VALUE pairs into os.environ without overwriting existing keys."""
    try:
        raw = dotenv_path.read_text(encoding="utf-8")
    except FileNotFoundError:
        return

    for line in raw.splitlines():
        line = line.strip()
        if not line or line.startswith("#"):
            continue
        if "=" not in line:
            continue

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if not key:
            continue
        os.environ.setdefault(key, value)


# Auto-load .env next to this addon, if present.
_load_dotenv(_ADDON_DIR / ".env")


def _apply_proxy_overrides() -> None:
    """Apply optional addon-specific proxy settings from the environment."""
    proxy_mapping = {
        "SCGS_HTTP_PROXY": ("http_proxy", "HTTP_PROXY"),
        "SCGS_HTTPS_PROXY": ("https_proxy", "HTTPS_PROXY"),
    }
    for source_key, target_keys in proxy_mapping.items():
        if source_key not in os.environ:
            continue

        proxy_value = os.environ[source_key].strip()
        for target_key in target_keys:
            if proxy_value:
                os.environ[target_key] = proxy_value
            else:
                os.environ.pop(target_key, None)

    # If an earlier addon version left a localhost proxy behind inside the
    # current Blender process, clear it unless the user explicitly opted in.
    if "SCGS_HTTP_PROXY" not in os.environ:
        for key in ("http_proxy", "HTTP_PROXY"):
            value = os.environ.get(key, "").strip()
            if "localhost:7890" in value or "127.0.0.1:7890" in value:
                os.environ.pop(key, None)
    if "SCGS_HTTPS_PROXY" not in os.environ:
        for key in ("https_proxy", "HTTPS_PROXY"):
            value = os.environ.get(key, "").strip()
            if "localhost:7890" in value or "127.0.0.1:7890" in value:
                os.environ.pop(key, None)


def _active_proxy_hint() -> str:
    for key in ("https_proxy", "HTTPS_PROXY", "http_proxy", "HTTP_PROXY"):
        value = os.environ.get(key, "").strip()
        if not value:
            continue
        if "localhost:7890" in value or "127.0.0.1:7890" in value:
            return (
                f" Detected proxy setting {key}={value}. "
                "If your local proxy is not running, remove that setting or leave "
                "SCGS_HTTP_PROXY/SCGS_HTTPS_PROXY empty in the addon .env file."
            )
        return f" Active proxy: {key}={value}."
    return ""


_apply_proxy_overrides()


def _dashscope_base_url() -> str:
    base_url = (
        os.environ.get("DASHSCOPE_BASE_URL", "").strip()
        or os.environ.get("OPENAI_BASE_URL", "").strip()
        or "https://dashscope.aliyuncs.com/compatible-mode/v1"
    )
    return base_url.rstrip("/")


def _dashscope_model() -> str:
    return (
        os.environ.get("DASHSCOPE_MODEL", "").strip()
        or os.environ.get("OPENAI_MODEL", "").strip()
        or "qwen-max"
    )


def _get_api_key() -> str:
    api_key = (
        os.environ.get("DASHSCOPE_API_KEY", "").strip()
        or os.environ.get("OPENAI_API_KEY", "").strip()
    )
    if not api_key:
        raise RuntimeError(
            "Missing API key: set DASHSCOPE_API_KEY or OPENAI_API_KEY in the environment or the addon's .env file."
        )
    return api_key


def chat_completions_create(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> dict[str, Any]:
    """Call an OpenAI-compatible chat completions endpoint."""
    base_url = _dashscope_base_url()
    url = f"{base_url}/chat/completions"

    payload = {
        "model": model or _dashscope_model(),
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {_get_api_key()}",
    }

    req = Request(url=url, data=data, headers=headers, method="POST")
    try:
        with urlopen(req, timeout=timeout) as resp:
            body = resp.read().decode("utf-8", errors="replace")
    except HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"API request failed HTTP {e.code}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"Network error: {e}.{_active_proxy_hint()}") from e

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Non-JSON response received: {body[:500]}") from e


def chat_completions_content(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> str:
    """Convenience wrapper: returns choices[0].message.content."""
    resp = chat_completions_create(
        messages=messages,
        model=model,
        temperature=temperature,
        max_tokens=max_tokens,
        timeout=timeout,
    )
    try:
        return resp["choices"][0]["message"]["content"]
    except Exception as e:  # noqa: BLE001
        raise RuntimeError(f"Unexpected API response structure: {resp}") from e
