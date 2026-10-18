"""Обязательные технические вопросы собеседования с рекрутёром.

Два вопроса на каждое собеседование (выбор рандомный — при новом собеседовании
вопросы отличаются): по одной из решённых задач и по одной технологии из резюме.
Форма — «почему выбрали X, а не Y». Детекция задавания — по ключевым словам
названия задачи/технологии + «а не» / «вместо» в ответе рекрутёра.
"""

import random

from app.services.skills import PATTERN_RU, TECH_STACK

# Альтернативный подход для каждого паттерна задач
PATTERN_ALTERNATIVES = {
    "two_pointers": "хеш-таблицу (dict)",
    "sliding_window": "перебор всех подмассивов",
    "prefix_sum": "прямой пересчёт сумм в цикле",
    "binary_search": "линейный поиск",
    "sorting": "жадный подход",
    "dfs": "BFS (обход в ширину)",
    "bfs": "DFS (обход в глубину)",
    "dp": "жадный подход",
    "greedy": "динамическое программирование",
    "heap": "сортировку всего массива",
    "trie": "хеш-таблицу префиксов",
    "math": "перебор всех кандидатов",
    "linked_list": "массив (list)",
}

# Альтернативы для популярных технологий из TECH_STACK
TECH_ALTERNATIVES = {
    "Python": "Java",
    "Java": "Python",
    "C++": "Rust",
    "C#": "Java",
    "JavaScript": "TypeScript",
    "TypeScript": "JavaScript",
    "Go": "Python",
    "Kotlin": "Java",
    "Swift": "Kotlin",
    "Dart": "Swift",
    "SQL": "NoSQL (MongoDB)",
    "PHP": "Python",
    "Rust": "C++",
    "Django": "FastAPI",
    "FastAPI": "Django",
    "Flask": "Django",
    "Spring Boot": "Django",
    "Hibernate / JPA": "SQLAlchemy",
    ".NET": "Spring Boot",
    "React": "Vue.js",
    "Vue.js": "React",
    "Angular": "React",
    "Node.js / Express": "Django",
    "Laravel": "Django",
    "Flutter": "React Native",
    "Unity": "Unreal Engine",
    "Unreal Engine": "Unity",
    "PyTorch": "TensorFlow",
    "TensorFlow": "PyTorch",
    "Pandas / NumPy": "Polars",
    # базы данных
    "PostgreSQL": "MySQL",
    "MySQL": "PostgreSQL",
    "SQLite": "PostgreSQL",
    "MongoDB": "PostgreSQL",
    "Oracle": "PostgreSQL",
    "Redis": "Memcached",
    "Elasticsearch": "Solr",
}

# Fallback по категории, если технологии нет в TECH_ALTERNATIVES
CATEGORY_FALLBACK = {
    "language": "другой распространённый язык (например, Java или Python)",
    "framework": "альтернативный фреймворк того же класса",
    "database": "реляционную СУБД вроде PostgreSQL",
    "tool": "альтернативный инструмент той же категории",
}


def _tech_alternative(tech: str) -> str:
    """Альтернатива для технологии: курированная пара, иначе fallback по категории."""
    if tech in TECH_ALTERNATIVES:
        return TECH_ALTERNATIVES[tech]
    cat = next((t["category"] for t in TECH_STACK if t["name"] == tech), None)
    return CATEGORY_FALLBACK.get(cat, "альтернативную технологию")


def _resume_techs(resume_data) -> list[str]:
    """Технологии, отмеченные студентом в резюме (без дублей, порядок заполнения)."""
    selected: list[str] = []
    for item in list(resume_data.projects) + list(resume_data.labs) + list(resume_data.courses) + list(resume_data.hackathons):
        selected.extend(item.tech_stack or [])
    if resume_data.lab_membership is not None:
        selected.extend(getattr(resume_data.lab_membership, "tech_stack", []) or [])
    return list(dict.fromkeys(selected))


def build_questions(solved: list[dict], resume_data, rng: random.Random | None = None) -> dict:
    """Генерирует обязательные вопросы (рандомный выбор задачи и технологии).

    solved — список из skills.solved_tasks; resume_data — ResumeData.
    Возвращает {"task": {"text", "meta"}, "tech": {"text", "meta"}} (ключи могут отсутствовать).
    """
    rng = rng or random.Random()
    result: dict = {}

    task = rng.choice(solved) if solved else None
    if task is not None:
        pattern_ru = PATTERN_RU.get(task["pattern"], task["pattern"])
        alt = PATTERN_ALTERNATIVES.get(task["pattern"], "другой подход")
        result["task"] = {
            "text": f"Почему в задаче «{task['title']}» вы выбрали {pattern_ru}, а не {alt}?",
            "meta": {"kind": "task", "title": task["title"], "slug": task["slug"]},
        }

    categories = {t["name"]: t["category"] for t in TECH_STACK}
    hard = [t for t in _resume_techs(resume_data) if categories.get(t) in ("language", "framework", "database")]
    tools = [t for t in _resume_techs(resume_data) if categories.get(t) == "tool"]
    pool = hard or tools

    if pool:
        tech = rng.choice(pool)
        result["tech"] = {
            "text": f"Почему в своих проектах вы выбрали {tech}, а не {_tech_alternative(tech)}?",
            "meta": {"kind": "tech", "name": tech},
        }
    elif task is not None and len(solved) >= 2:
        # Резюме без технологий (крайний случай): второй вопрос по другой решённой задаче
        other = rng.choice([t for t in solved if t["id"] != task["id"]])
        pattern_ru = PATTERN_RU.get(other["pattern"], other["pattern"])
        alt = PATTERN_ALTERNATIVES.get(other["pattern"], "другой подход")
        result["tech"] = {
            "text": f"Почему в задаче «{other['title']}» вы выбрали {pattern_ru}, а не {alt}?",
            "meta": {"kind": "task", "title": other["title"], "slug": other["slug"]},
        }

    return result


def _norm(s: str) -> str:
    """Нижний регистр + ё→е для нечувствительного сопоставления."""
    return s.lower().replace("ё", "е")


def detect_asked(meta: dict, assistant_text: str) -> bool:
    """Задал ли рекрутёр вопрос: ключевое название (задачи/технологии) + «а не» / «вместо»."""
    if not meta:
        return False
    text = _norm(assistant_text)
    if "а не" not in text and "вместо" not in text:
        return False
    key = meta.get("title") if meta.get("kind") == "task" else meta.get("name", "")
    return bool(key) and _norm(key) in text


def get_or_create_progress(db, user, solved: list[dict], resume_data):
    """Строка прогресса обязательных вопросов; при первом обращении генерирует вопросы."""
    from sqlalchemy import select

    from app.models import RecruiterProgress

    row = db.scalar(select(RecruiterProgress).where(RecruiterProgress.user_id == user.id))
    if row is None:
        qs = build_questions(solved, resume_data)
        row = RecruiterProgress(
            user_id=user.id,
            task_question=qs.get("task", {}).get("text"),
            tech_question=qs.get("tech", {}).get("text"),
            meta={"task": qs.get("task", {}).get("meta"), "tech": qs.get("tech", {}).get("meta")},
        )
        db.add(row)
        db.commit()
        db.refresh(row)
    return row
