"""LLM-генерация вариантов задач (новая легенда/заголовок) и сообщений чата с наставником.

Ретайтлинг — до 3 попыток, упавшие разделы формата доклеиваются из оригинала; в контекст чата попадают код студента, результат последнего запуска и предупреждение о несоответствии языка.
"""

from app.models import Task
from app.services.llm import LLMError, chat_completion, extract_json


def _retitle_system(theme: str | None) -> str:
    """Системный промпт ретайтлинга: новая легенда при сохранении сути, ответ строго JSON."""
    base = (
        "Ты — составитель задач для алгоритмических собеседований.\n"
        "Переформулируй задачу: придумай НОВУЮ сюжетную легенду (область, имена, антураж), "
        "полностью сохраняя алгоритмическую суть, ограничения и форматы ввода/вывода. "
        "Не меняй числа-ограничения и не выдумывай новые условия.\n"
        "Разделы 'Формат ввода' и 'Формат вывода' скопируй ПОСЛОВНО без изменений — они обязательны в легенде.\n"
        "Примеры НЕ добавляй в легенду — они показываются отдельно.\n"
    )
    if theme:
        base += f"Легенда должна быть в едином стиле/области: {theme}.\n"
    return base + (
        'Ответь СТРОГО одним JSON-объектом без пояснений: '
        '{"title": "<новый заголовок>", "legend": "<новая легенда>"}'
    )


def _extract_format(legend: str) -> str:
    """Разделы формата из оригинальной легенды (гарантия для слабой модели)."""
    idx = legend.find("Формат ввода")
    if idx == -1:
        return ""
    return legend[idx:].strip()


async def generate_variant(task: Task, db=None, theme: str | None = None) -> dict:
    """Генерирует новый {title, legend} задачи; до 3 попыток, при провале всех — LLMError."""
    user_prompt = (
        f"Уровень: {task.level}. Паттерн: {task.pattern}.\n"
        f"Задача:\n# {task.title}\n{task.legend[:4000]}"
    )
    last_err: LLMError | None = None
    for attempt in range(3):
        try:
            reply = await chat_completion(
                [
                    {"role": "system", "content": _retitle_system(theme)},
                    {"role": "user", "content": user_prompt},
                ],
                db=db,
                temperature=0.9 if attempt == 0 else 0.4,
                max_tokens=1500,
            )
            data = extract_json(reply)
            title = str(data.get("title", "")).strip().lstrip("#").strip()
            legend = str(data.get("legend", "")).strip()
            if len(title) < 3 or len(legend) < 40:
                raise LLMError("ИИ вернул пустую или слишком короткую легенду")
            # слабая модель могла уронить разделы формата — доклеиваем из оригинала
            if "Формат ввода" not in legend or "Формат вывода" not in legend:
                fmt = _extract_format(task.legend)
                if fmt:
                    legend = legend.rstrip() + "\n\n" + fmt
            return {"title": title[:250], "legend": legend}
        except LLMError as e:
            last_err = e
    raise last_err or LLMError("ИИ не сгенерировал легенду")


CHAT_SYSTEM_HINT = (
    "Ты — наставник по подготовке к алгоритмическим собеседованиям. Студент решает задачу.\n"
    "Отвечай на русском. НЕ давай готовый код решения. Задавай наводящие вопросы, "
    "подсказывай идею и паттерн намёками, разбивай задачу на подшаги. Отвечай кратко.\n"
    "В контексте может быть результат последнего запуска кода со stderr. Если в stderr видны "
    "ошибки компиляции/интерпретатора (SyntaxError, cannot find symbol, unexpected token, "
    "command not found и т.п.) — сначала объясни причину именно этой ошибки запуска, включая "
    "возможное несоответствие языка кода и выбранного интерпретатора (например: код написан "
    "на Java, а запускается как Python — попроси выбрать правильный язык в редакторе). "
    "Только после этого переходи к разбору логики."
)

CHAT_SYSTEM_EXPLAIN = (
    "Ты — наставник по подготовке к алгоритмическим собеседованиям. Студент просит объяснить.\n"
    "Отвечай на русском: подробно разбирай ошибки в логике, граничные случаи, "
    "алгоритмическую сложность и соответствующий задаче паттерн. Готовый код не пиши, "
    "но можешь показывать короткие фрагменты (до 5 строк) для иллюстрации идеи.\n"
    "В контексте может быть результат последнего запуска кода со stderr. Если в stderr видны "
    "ошибки компиляции/интерпретатора (SyntaxError, cannot find symbol, unexpected token, "
    "command not found и т.п.) — сначала объясни причину именно этой ошибки запуска, включая "
    "возможное несоответствие языка кода и выбранного интерпретатора (например: код написан "
    "на Java, а запускается как Python — попроси выбрать правильный язык в редакторе). "
    "Только после этого переходи к разбору логики."
)

_LANG_MARKERS = {
    "java": ("public class", "System.out", "import java."),
    "cpp": ("#include <"),
    "javascript": ("console.log", "function "),
}


def _language_mismatch_warning(code: str, language: str | None) -> str | None:
    """Эвристика: код похож на другой язык, чем выбранный интерпретатор."""
    if not code or not language:
        return None
    for other, markers in _LANG_MARKERS.items():
        if other == language:
            continue
        if any(m in code for m in markers):
            return (
                f"Внимание: код содержит маркеры языка {other}, но выбран интерпретатор "
                f"{language} — возможно, студент запускает код не в том интерпретаторе."
            )
    return None


def build_chat_messages(
    task: Task,
    history: list[dict],
    code: str | None,
    language: str | None,
    mode: str,
    last_run_summary: str | None,
) -> list[dict]:
    """Собирает сообщения для наставника: системный промпт по режиму, контекст и последние 12 сообщений истории."""
    system = CHAT_SYSTEM_EXPLAIN if mode == "explain" else CHAT_SYSTEM_HINT
    context = [f"Текущая задача: {task.title} (уровень {task.level})\n{task.legend[:2500]}"]
    if code:
        context.append(f"Код студента ({language or 'unknown'}):\n```\n{code[:4000]}\n```")
    warning = _language_mismatch_warning(code, language)
    if warning:
        context.append(warning)
    if last_run_summary:
        context.append(last_run_summary)
    messages = [{"role": "system", "content": system}]
    messages.append({"role": "system", "content": "\n\n".join(context)})
    messages.extend(history[-12:])
    return messages
