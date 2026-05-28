from __future__ import annotations

import json
import os
from pathlib import Path
from typing import Any, Iterable
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


def _dashscope_base_url() -> str:
    return os.environ.get("DASHSCOPE_BASE_URL", "https://dashscope.aliyuncs.com/compatible-mode/v1").rstrip("/")


def _dashscope_model() -> str:
    return os.environ.get("DASHSCOPE_MODEL", "qwen-max")


def _get_api_key() -> str:
    api_key = os.environ.get("DASHSCOPE_API_KEY", "").strip()
    if not api_key:
        raise RuntimeError(
            "缺少 DashScope API Key：请在系统环境变量或插件目录的 .env 中设置 DASHSCOPE_API_KEY"
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
    """Call DashScope OpenAI-compatible chat completions endpoint.

    Returns the parsed JSON response.
    """
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
        raise RuntimeError(f"DashScope 请求失败 HTTP {e.code}: {err_body}") from e
    except URLError as e:
        raise RuntimeError(f"DashScope 网络错误: {e}") from e

    try:
        return json.loads(body)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"DashScope 返回了非 JSON 内容: {body[:500]}") from e


def chat_completions_content(
    *,
    messages: list[dict[str, Any]],
    model: str | None = None,
    temperature: float = 0.4,
    max_tokens: int = 4096,
    timeout: float = 60.0,
) -> str:
    """Convenience wrapper: returns choices[0].message.content"""
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
        raise RuntimeError(f"DashScope 返回结构异常: {resp}") from e
