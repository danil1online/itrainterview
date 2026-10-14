import json
import re

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import get_setting


class LLMError(Exception):
    pass


_detected_model: str | None = None


def _headers(api_key: str) -> dict:
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def effective_llm_config(db: Session | None = None) -> tuple[str, str, str]:
    base = settings.llm_base_url
    model = settings.llm_model
    key = settings.llm_api_key
    if db is not None:
        base = get_setting(db, "llm_base_url", base)
        model = get_setting(db, "llm_model", model)
        key = get_setting(db, "llm_api_key", key)
    return base.rstrip("/"), model, key


async def detect_model(base: str, key: str) -> str:
    global _detected_model
    if _detected_model:
        return _detected_model
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/models", headers=_headers(key))
            r.raise_for_status()
            data = r.json()
            models = data.get("data") or data.get("models") or []
            if not models:
                raise LLMError("LLM не вернул список моделей")
            _detected_model = models[0].get("id") or models[0].get("name")
            return _detected_model
    except LLMError:
        raise
    except Exception as e:
        raise LLMError(f"Не удалось получить список моделей: {e}")


async def chat_completion(
    messages: list[dict],
    db: Session | None = None,
    temperature: float = 0.4,
    max_tokens: int = 1200,
    timeout_sec: float | None = None,
) -> str:
    base, model, key = effective_llm_config(db)
    if not model:
        model = await detect_model(base, key)
    payload = {
        "model": model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "stream": False,
    }
    try:
        async with httpx.AsyncClient(timeout=timeout_sec or settings.llm_timeout_sec) as client:
            r = await client.post(
                f"{base}/chat/completions", json=payload, headers=_headers(key)
            )
            r.raise_for_status()
            data = r.json()
            return data["choices"][0]["message"]["content"]
    except httpx.HTTPStatusError as e:
        raise LLMError(f"LLM вернул ошибку {e.response.status_code}: {e.response.text[:300]}")
    except Exception as e:
        raise LLMError(f"Ошибка обращения к LLM: {e}")


def extract_json(text: str) -> dict:
    """Достаёт JSON-объект из ответа модели (может быть обёрнут в ```json ... ```)."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*(\{.*\})\s*```", text, re.DOTALL)
    if fence:
        text = fence.group(1)
    else:
        start, end = text.find("{"), text.rfind("}")
        if start != -1 and end > start:
            text = text[start : end + 1]
    try:
        return json.loads(text)
    except json.JSONDecodeError as e:
        raise LLMError(f"Модель вернула некорректный JSON: {e}")
