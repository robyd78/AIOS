from __future__ import annotations

import os
from typing import Any, Dict, List, Optional

import httpx

from .errors import ServiceUnavailableError

OLLAMA_URL = os.getenv("OLLAMA_URL", "http://127.0.0.1:11434")
DEFAULT_MODEL = os.getenv("OLLAMA_MODEL", "phi3:mini")


async def _try_generate(
    client: httpx.AsyncClient,
    model: str,
    messages: List[Dict[str, Any]],
    temperature: Optional[float] = None,
) -> str:
    payload: Dict[str, Any] = {"model": model, "messages": messages, "stream": False}
    if temperature is not None:
        payload["options"] = {"temperature": temperature}
    response = await client.post(
        f"{OLLAMA_URL}/api/chat",
        json=payload,
        timeout=60.0,
    )
    if response.status_code == 200:
        data = response.json()
        message = data.get("message", {})
        content = (
            message.get("content")
            or data.get("content")
            or data.get("text")
            or data.get("response")
        )
        if isinstance(content, str):
            return content.strip()
        raise ServiceUnavailableError("Ollama response missing text content")

    raise ServiceUnavailableError(
        f"Ollama {model} HTTP {response.status_code}: {response.text[:200]}"
    )


def _build_fallbacks(chosen: str) -> List[str]:
    fallbacks = [chosen]
    if "llama3:8b" in chosen:
        fallbacks += ["qwen2.5:3b-instruct", "phi3:mini"]
    elif "qwen2.5:3b-instruct" in chosen:
        fallbacks += ["phi3:mini"]
    elif chosen != DEFAULT_MODEL:
        fallbacks.append(DEFAULT_MODEL)
    return fallbacks


async def generate(
    messages: List[Dict[str, Any]],
    model: Optional[str] = None,
    temperature: Optional[float] = None,
) -> str:
    if not messages:
        raise ServiceUnavailableError("No messages provided for generation")

    fallbacks = _build_fallbacks(model or DEFAULT_MODEL)
    async with httpx.AsyncClient() as client:
        last_err: Optional[Exception] = None
        for target_model in fallbacks:
            try:
                return await _try_generate(client, target_model, messages, temperature)
            except Exception as exc:
                last_err = exc
        raise ServiceUnavailableError(str(last_err) if last_err else "LLM unavailable")
