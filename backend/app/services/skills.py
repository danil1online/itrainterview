"""Агрегация навыков из резюме + решённых задач платформы; рекомендация должности.

Детерминированные правила (без LLM): объяснимо, мгновенно, тестируемо.
"""

from sqlalchemy import select

from app.models import Submission, Task
from app.schemas import ResumeData


def solved_info(db, user) -> tuple[set[str], set[str]]:
    """Паттерны решённых задач и языки (accepted submissions)."""
    subs = db.scalars(select(Submission).where(Submission.user_id == user.id)).all()
    accepted_task_ids = {s.task_id for s in subs if s.status == "accepted"}
    langs = {s.language for s in subs if s.status == "accepted" and s.language}
    patterns: set[str] = set()
    if accepted_task_ids:
        tasks = db.scalars(
            select(Task).where(Task.id.in_(accepted_task_ids), Task.is_active.is_(True))
        ).all()
        patterns = {t.pattern for t in tasks}
    return patterns, langs

# Единый источник стека технологий: {name, category}
TECH_STACK: list[dict] = [
    # языки
    {"name": "Python", "category": "language"},
    {"name": "Java", "category": "language"},
    {"name": "C++", "category": "language"},
    {"name": "C#", "category": "language"},
    {"name": "JavaScript", "category": "language"},
    {"name": "TypeScript", "category": "language"},
    {"name": "Go", "category": "language"},
    {"name": "Kotlin", "category": "language"},
    {"name": "Swift", "category": "language"},
    {"name": "Dart", "category": "language"},
    {"name": "SQL", "category": "language"},
    {"name": "PHP", "category": "language"},
    {"name": "Rust", "category": "language"},
    # фреймворки и библиотеки
    {"name": "Django", "category": "framework"},
    {"name": "FastAPI", "category": "framework"},
    {"name": "Flask", "category": "framework"},
    {"name": "Spring Boot", "category": "framework"},
    {"name": "Hibernate / JPA", "category": "framework"},
    {"name": ".NET", "category": "framework"},
    {"name": "React", "category": "framework"},
    {"name": "Vue.js", "category": "framework"},
    {"name": "Angular", "category": "framework"},
    {"name": "Node.js / Express", "category": "framework"},
    {"name": "Laravel", "category": "framework"},
    {"name": "Flutter", "category": "framework"},
    {"name": "Unity", "category": "framework"},
    {"name": "Unreal Engine", "category": "framework"},
    {"name": "1С:Предприятие", "category": "framework"},
    {"name": "Qt", "category": "framework"},
    {"name": "PyTorch", "category": "framework"},
    {"name": "TensorFlow", "category": "framework"},
    {"name": "Pandas / NumPy", "category": "framework"},
    # базы данных
    {"name": "PostgreSQL", "category": "database"},
    {"name": "MySQL", "category": "database"},
    {"name": "SQLite", "category": "database"},
    {"name": "MongoDB", "category": "database"},
    {"name": "Oracle", "category": "database"},
    {"name": "Redis", "category": "database"},
    {"name": "Elasticsearch", "category": "database"},
    # инструменты
    {"name": "Git", "category": "tool"},
    {"name": "Docker", "category": "tool"},
    {"name": "Linux", "category": "tool"},
    {"name": "CI/CD (Jenkins, GitLab CI)", "category": "tool"},
    {"name": "Postman", "category": "tool"},
    {"name": "JIRA", "category": "tool"},
    {"name": "Android Studio", "category": "tool"},
    {"name": "Xcode", "category": "tool"},
]

PATTERN_RU = {
    "two_pointers": "Два указателя",
    "sliding_window": "Скользящее окно",
    "prefix_sum": "Префиксная сумма",
    "binary_search": "Бинарный поиск",
    "sorting": "Сортировки и «разделяй и властвуй»",
    "dfs": "DFS: графы, компоненты связности, backtracking",
    "bfs": "BFS: кратчайшие пути, обход по уровням",
    "dp": "Динамическое программирование",
    "greedy": "Жадные алгоритмы",
    "heap": "Куча / очередь с приоритетом",
    "trie": "Префиксное дерево (Trie)",
    "math": "Теория чисел: НОД, решето Эратосфена, быстрая степень",
    "linked_list": "Связные списки и алгоритм Флойда",
}

LANG_RU = {
    "python": "Python",
    "java": "Java",
    "cpp": "C++",
    "javascript": "JavaScript / Node.js",
}

# Должность -> ключевые слова (поиск по выбранному стеку и языкам решённых задач)
POSITIONS: list[tuple[str, list[str]]] = [
    ("Программист 1С", ["1с", "1c"]),
    ("Программист встраиваемых систем", ["встраиваем", "arduino", "stm32", "rtos", "прошивк", "firmware"]),
    ("Frontend-разработчик", ["react", "vue", "angular", "typescript", "frontend", "html", "css"]),
    ("Java-разработчик", ["java", "spring", "hibernate", "jpa", "kotlin"]),
    ("Python-разработчик", ["python", "django", "fastapi", "flask", "pytorch", "tensorflow", "pandas"]),
    ("Разработчик C++", ["c++", "qt", "opengl"]),
    ("Backend-разработчик", ["backend", "rest api", "микросервис", "docker", "kubernetes", "redis", "rabbitmq"]),
    ("iOS-разработчик", ["swift", "ios", "uikit", "swiftui", "xcode"]),
    ("SQL-разработчик", ["sql", "pl/sql", "etl", "data warehouse", "хранилище данных", "t-sql"]),
    ("Android-разработчик", ["android", "jetpack", "kotlin"]),
    ("Unity-разработчик", ["unity", "game development", "геймдев"]),
    ("Flutter-разработчик", ["flutter", "dart"]),
    ("Разработчик Node.js", ["node.js", "express", "nestjs"]),
    ("C#/.NET-разработчик", ["c#", ".net", "asp.net"]),
    ("Разработчик на Unreal Engine", ["unreal"]),
    ("PHP-разработчик", ["php", "laravel"]),
]
GENERIC_POSITION = "Инженер-программист"


def _norm(s: str) -> str:
    return s.lower().replace("ё", "е")


def recommend_position(pool: list[str]) -> dict:
    """Детерминированный выбор должности по пулу навыков.

    pool — названия выбранных технологий + языки решённых задач.
    """
    text = [_norm(p) for p in pool]

    def score(keywords: list[str]) -> list[str]:
        hits = []
        for kw in keywords:
            if any(kw in t for t in text):
                hits.append(kw)
        return hits

    best_title, best_hits = GENERIC_POSITION, []
    best_score = 0
    fe_hits = score(dict(POSITIONS)["Frontend-разработчик"])
    be_hits = score(dict(POSITIONS)["Backend-разработчик"])
    for title, keywords in POSITIONS:
        if title in ("Fullstack-разработчик",):
            continue
        hits = score(keywords)
        s = len(hits)
        if s > best_score:
            best_title, best_hits, best_score = title, hits, s
    # Fullstack — только при явном совпадении и frontend- и backend-навыков
    if fe_hits and be_hits:
        fs_score = (len(fe_hits) + len(be_hits)) // 2
        if fs_score > best_score:
            best_title, best_hits, best_score = "Fullstack-разработчик", sorted(set(fe_hits + be_hits)), fs_score
    return {"position": best_title, "reasons": best_hits}


def aggregate_skills(data: ResumeData, solved_patterns: set[str], solved_languages: set[str]) -> dict:
    """Обобщает навыки: резюме (галочки) + решённые задачи платформы."""
    selected = set()
    for item in list(data.projects) + list(data.labs) + list(data.courses) + list(data.hackathons):
        selected.update(item.tech_stack or [])
    if data.lab_membership is not None:
        selected.update(getattr(data.lab_membership, "tech_stack", []) or [])

    categories = {t["name"]: t["category"] for t in TECH_STACK}
    hard = [t for t in selected if categories.get(t) in ("language", "framework", "database")]
    tools = [t for t in selected if categories.get(t) == "tool"]
    # языки, на которых студент реально решал задачи на платформе
    for lang in sorted(solved_languages):
        name = LANG_RU.get(lang)
        if name and name not in hard:
            hard.append(name)

    algorithms = [PATTERN_RU[p] for p in PATTERN_RU if p in solved_patterns]

    pool = list(selected) + [LANG_RU[l] for l in solved_languages if l in LANG_RU]
    position = recommend_position(pool)
    return {
        "hard_skills": sorted(hard),
        "tools": sorted(tools),
        "algorithms": algorithms,
        "position": position,
    }


def resume_completion(data: ResumeData) -> dict:
    """Готовность резюме для скрининга с рекрутером."""
    missing = []
    basic = {
        "Фамилия": data.last_name,
        "Имя": data.first_name,
        "Город": data.city,
        "Телефон": data.phone,
    }
    for label, value in basic.items():
        if not (value or "").strip():
            missing.append(f"Основная информация: {label.lower()}")
    has_experience = bool(
        any((p.name or p.problem).strip() for p in data.projects)
        or any((l.subject or l.work_name).strip() for l in data.labs)
        or any((i.organization or i.city).strip() for i in data.internships)
        or any((c.name or c.month_year).strip() for c in data.courses)
        or any((h.name or h.organizer).strip() for h in data.hackathons)
        or (data.lab_membership is not None and (data.lab_membership.university or "").strip())
    )
    if not has_experience:
        missing.append("Хотя бы одна запись в разделах: проекты, лабораторные работы, практика, курсы или хакатоны")
    return {"ready": not missing, "missing": missing}


def resume_to_text(data: ResumeData, skills: dict) -> str:
    """Структурированный текст резюме для контекста LLM."""
    lines = []
    name = " ".join(x for x in (data.last_name, data.first_name, data.middle_name) if x.strip())
    lines.append(f"Кандидат: {name or 'не указано'}")
    meta = [x for x in (data.city, data.phone, data.citizenship) if x.strip()]
    if meta:
        lines.append("Контакты/основное: " + "; ".join(meta))
    edu = " / ".join(x for x in (data.university, data.faculty, data.department, data.major, data.graduation_year) if x.strip())
    if edu:
        lines.append(f"Образование: {edu}")

    def section(title: str, rows: list[str]):
        if rows:
            lines.append(f"\n{title}:")
            lines.extend(f"- {r}" for r in rows)

    section("Курсовые и дипломные проекты", [
        f"{p.name} — {p.problem}" + (f" [стек: {', '.join(p.tech_stack)}]" if p.tech_stack else "")
        for p in data.projects if (p.name or p.problem).strip()
    ])
    section("Лабораторные и практические работы", [
        f"{l.subject}: {l.work_name}" + (f" — цель: {l.goal}" if l.goal.strip() else "")
        + (f" [стек: {', '.join(l.tech_stack)}]" if l.tech_stack else "")
        for l in data.labs if (l.subject or l.work_name).strip()
    ])
    section("Практика и стажировки", [
        f"{i.organization}" + (f" ({i.city})" if i.city.strip() else "") + (f", {i.period}" if i.period.strip() else "")
        + (f" — цель: {i.goal}" if i.goal.strip() else "")
        for i in data.internships if (i.organization or i.city).strip()
    ])
    section("Курсы дополнительного обучения", [
        f"{c.name}" + (f", {c.month_year}" if c.month_year.strip() else "")
        + (f" [стек: {', '.join(c.tech_stack)}]" if c.tech_stack else "")
        for c in data.courses if (c.name or c.month_year).strip()
    ])
    section("Хакатоны и олимпиады", [
        f"{h.name}" + (f" ({h.organizer})" if h.organizer.strip() else "")
        + (f", {h.location}" if h.location.strip() else "") + (f", {h.month_year}" if h.month_year.strip() else "")
        + (f", роль: {h.role}" if h.role.strip() else "")
        + (f" [стек: {', '.join(h.tech_stack)}]" if h.tech_stack else "")
        for h in data.hackathons if (h.name or h.organizer).strip()
    ])
    lm = data.lab_membership
    if lm is not None and (lm.university or lm.own_project):
        row = f"{lm.university}" + (f", кафедра: {lm.department}" if lm.department.strip() else "")
        if lm.supervisor.strip():
            row += f", руководитель: {lm.supervisor}"
        if lm.own_project.strip():
            row += f"; личный проект: {lm.own_project}"
        others = [p for p in (lm.other_projects or []) if p.strip()]
        if others:
            row += "; проекты коллег: " + ", ".join(others)
        section("Научно-исследовательская лаборатория", [row])

    links = [x for x in (data.github, data.gitverse, data.gitflic) if x.strip()]
    if links:
        lines.append("\nСсылки: " + "; ".join(links))

    lines.append(
        "\nНавыки: "
        + ", ".join(skills["hard_skills"])
        + (f"; инструменты: {', '.join(skills['tools'])}" if skills["tools"] else "")
        + (f"; алгоритмы: {', '.join(skills['algorithms'])}" if skills["algorithms"] else "")
    )
    lines.append(f"Рекомендуемая должность: {skills['position']['position']}")
    return "\n".join(lines)
