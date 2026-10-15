"""Клиент OpenAI-совместимого API (httpx): chat completions, автоопределение модели, разбор JSON из ответа.

Конфигурация — env + настройки БД; при пустой модели определяется через GET /models и кэшируется глобально.
"""

import json
import re
import time

import httpx
from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import get_setting


class LLMError(Exception):
    pass


# Кэш автоопределённой модели: (имя, время определения); TTL — час, чтобы подхватить смену модели на сервере.
_detected_model: tuple[str, float] | None = None
_MODEL_CACHE_TTL_SEC = 3600.0


def _headers(api_key: str) -> dict:
    """Заголовки запроса; Authorization подставляется только при непустом api_key."""
    h = {"Content-Type": "application/json"}
    if api_key:
        h["Authorization"] = f"Bearer {api_key}"
    return h


def effective_llm_config(db: Session | None = None) -> tuple[str, str, str]:
    """(base_url, model, api_key): env-настройки, при переданной db — с переопределением из БД. base без завершающего '/'."""
    base = settings.llm_base_url
    model = settings.llm_model
    key = settings.llm_api_key
    if db is not None:
        base = get_setting(db, "llm_base_url", base)
        model = get_setting(db, "llm_model", model)
        key = get_setting(db, "llm_api_key", key)
    return base.rstrip("/"), model, key


async def detect_model(base: str, key: str) -> str:
    """Определяет первую модель из GET /models; кэш с TTL _MODEL_CACHE_TTL_SEC; при неудаче — LLMError."""
    global _detected_model
    if _detected_model and time.monotonic() - _detected_model[1] < _MODEL_CACHE_TTL_SEC:
        return _detected_model[0]
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{base}/models", headers=_headers(key))
            r.raise_for_status()
            data = r.json()
            models = data.get("data") or data.get("models") or []
            if not models:
                raise LLMError("LLM не вернул список моделей")
            model = models[0].get("id") or models[0].get("name")
            if not model:
                raise LLMError("LLM не вернул идентификатор модели")
            _detected_model = (model, time.monotonic())
            return model
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
    """POST /chat/completions, возвращает content ответа; любые ошибки оборачиваются в LLMError. Пустая модель — автоопределение."""
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
