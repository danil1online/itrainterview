from sqlalchemy.orm import Session

from app.core.config import settings
from app.models import Submission, Task, User, get_setting
from app.services.llm import LLMError, chat_completion
from app.services.sandbox import RunOutcome, get_sandbox


def _int_setting(db: Session, key: str, default: int) -> int:
    try:
        return int(get_setting(db, key, str(default)))
    except ValueError:
        return default


def sandbox_limits(db: Session) -> tuple[int, int]:
    timeout = _int_setting(db, "sandbox_timeout_sec", settings.sandbox_timeout_sec)
    memory = _int_setting(db, "sandbox_memory_mb", settings.sandbox_memory_mb)
    return max(1, min(timeout, 60)), max(64, min(memory, 2048))


def run_tests(db: Session, language: str, code: str, tests: list[dict]) -> RunOutcome:
    timeout, memory = sandbox_limits(db)
    return get_sandbox().run(language, code, tests, timeout_sec=timeout, memory_mb=memory)


def outcome_to_dict(outcome: RunOutcome) -> dict:
    return {
        "status": outcome.status,
        "passed_count": sum(1 for r in outcome.results if r.passed),
        "total_count": len(outcome.results),
        "time_ms": outcome.time_ms,
        "results": [
            {
                "name": r.name,
                "passed": r.passed,
                "status": r.status,
                "expected_stdout": "",  # ожидаемый вывод скрытых тестов не отдаём студенту
                "got_stdout": r.got_stdout,
                "stderr": r.stderr,
                "time_ms": r.time_ms,
            }
            for r in outcome.results
        ],
    }


def create_submission(
    db: Session, user: User, task: Task, language: str, code: str, outcome: RunOutcome
) -> Submission:
    sub = Submission(
        user_id=user.id,
        task_id=task.id,
        language=language,
        code=code,
        status=outcome.status,
        passed_count=sum(1 for r in outcome.results if r.passed),
        total_count=len(outcome.results),
        results=outcome_to_dict(outcome)["results"],
        time_ms=outcome.time_ms,
    )
    db.add(sub)
    db.commit()
    db.refresh(sub)
    return sub


FEEDBACK_SYSTEM = (
    "Ты — опытный IT-интервьюер и наставник. Студент решает алгоритмическую задачу "
    "для подготовки к собеседованию.\n"
    "Тебе даны: легенда задачи, код студента и результаты тестов.\n"
    "Объясни ПРИЧИНЫ ошибок: где нарушена логика, какие граничные случаи не обработаны, "
    "какая алгоритмическая сложность получается и какая ожидается.\n"
    "НЕ пиши готовое решение целиком. Дай направление: какой паттерн применить и что "
    "исправлять шаг за шагом.\n"
    "Отвечай на русском, кратко, по пунктам."
)


async def generate_submission_feedback(
    db: Session, sub: Submission, task: Task
) -> str | None:
    failed = [r for r in sub.results if not r.get("passed")]
    prompt = (
        f"Задача: {task.title} (паттерн: {task.pattern}, уровень: {task.level})\n"
        f"{task.legend[:2000]}\n\n"
        f"Язык: {sub.language}\nКод студента:\n```\n{sub.code[:4000]}\n```\n\n"
        f"Результат: {sub.passed_count} из {sub.total_count} тестов пройдено.\n"
        "Проваленные тесты:\n"
        + "\n".join(
            f"- {r.get('name')}: {r.get('status')}; вывод: {(r.get('got_stdout') or '')[:400]!r}; "
            f"stderr: {(r.get('stderr') or '')[:200]!r}"
            for r in failed[:5]
        )[:3000]
        + "\n\nОбъясни ошибки и дай наводящие подсказки без готового решения."
    )
    try:
        reply = await chat_completion(
            [
                {"role": "system", "content": FEEDBACK_SYSTEM},
                {"role": "user", "content": prompt},
            ],
            db=db,
            temperature=0.3,
            max_tokens=900,
        )
    except LLMError as e:
        return f"[ИИ-помощник недоступен: {e}]"
    sub.ai_feedback = reply
    db.commit()
    return reply
