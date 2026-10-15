"""Движок вайб-кодинга: сборка кода со скрытыми тестами, прогоны, мутанты, AST-метрики.

Общий механизм: к коду студента дописывается python-драйвер, который печатает строки
    T<индекс> PASS <имя>   /   T<индекс> FAIL <имя>: <причина>
Ожидаемый вывод скрытых тестов студенту не отдаётся — только статусы и текст assert'а.
"""

import ast
import re
from dataclasses import asdict, dataclass

from app.services.sandbox import get_sandbox

MARKER = "# === ВАШИ ТЕСТЫ НИЖЕ"  # тип tests: всё после маркера — тесты студента (test_*)
MIN_STUDENT_TESTS = 3
MAX_NESTING = 2
PROMPT_MIN_LEN = 40

SIGNAL_WORDS = [
    "тип", "пример", "формат", "ограничен", "docstring", "верни только код",
    "функция", "аргумент", "тест", "случа", "импорт", "ошибк", "вывод",
    "краш", "edge", "валид", "проверь", "сигнатур", "возвращ",
]

_T_LINE = re.compile(r"^T(\d+) (PASS|FAIL)(?:\s(.*))?$")


@dataclass
class CaseResult:
    name: str
    passed: bool
    detail: str = ""


# ---------------------------------------------------------------- drivers

def _assert_driver(cases: list[dict]) -> str:
    """Генерирует python-драйвер: прогоняет скрытые кейсы и печатает строки T<i> PASS/FAIL."""
    lines = [
        "",
        "# ==== скрытые тесты (система) ====",
        "def __run_case(__i, __name, __fn):",
        "    try:",
        "        __fn()",
        '        print("T" + str(__i) + " PASS " + __name)',
        "    except AssertionError as __e:",
        # голый assert без сообщения даёт пустой str(e) — показываем упавшую строку из traceback
        "        __msg = str(__e)",
        "        if not __msg:",
        "            import traceback as _tb",
        "            __lines = [l.strip() for l in _tb.format_exc().splitlines() if l.strip()]",
        # пропускаем хвост: 'AssertionError' и строки из '^' (Python 3.11+), ищем исходную строку
        "            __k = len(__lines) - 1",
        "            while __k >= 0 and (__lines[__k].startswith('AssertionError') or set(__lines[__k]) <= {'^'}):",
        "                __k -= 1",
        "            __msg = __lines[__k] if __k >= 0 else 'assert failed'",
        '        print("T" + str(__i) + " FAIL " + __name + ": assert failed: " + __msg)',
        "    except Exception as __e:",
        '        print("T" + str(__i) + " FAIL " + __name + ": " + type(__e).__name__ + ": " + str(__e))',
    ]
    for i, case in enumerate(cases):
        body = (case.get("code") or "").strip("\n")
        lines.append("")
        lines.append("def __case_" + str(i) + "():")
        if body:
            for ln in body.splitlines():
                lines.append("    " + ln)
        else:
            lines.append("    pass")
        name = (case.get("name") or ("test" + str(i))).replace('"', "'")
        lines.append('__run_case(' + str(i) + ', "' + name + '", __case_' + str(i) + ')')
    return "\n".join(lines) + "\n"


_DISCOVERY_DRIVER = """
# ==== discovery driver (система) ====
import inspect as _inspect
__cases = sorted(
    [(k, v) for k, v in list(globals().items()) if k.startswith("test_") and callable(v)],
    key=lambda kv: kv[0],
)
if not __cases:
    print("NO TESTS FOUND")
for __i, (__name, __fn) in enumerate(__cases):
    try:
        __fn()
        print("T" + str(__i) + " PASS " + __name)
    except AssertionError as __e:
        __msg = str(__e)
        if not __msg:
            import traceback as _tb
            __lines = [l.strip() for l in _tb.format_exc().splitlines() if l.strip()]
            # пропускаем хвост: 'AssertionError' и строки из '^' (Python 3.11+), ищем исходную строку
            __k = len(__lines) - 1
            while __k >= 0 and (__lines[__k].startswith('AssertionError') or set(__lines[__k]) <= {'^'}):
                __k -= 1
            __msg = __lines[__k] if __k >= 0 else 'assert failed'
        print("T" + str(__i) + " FAIL " + __name + ": assert failed: " + __msg)
    except Exception as __e:
        print("T" + str(__i) + " FAIL " + __name + ": " + type(__e).__name__ + ": " + str(__e))
"""


def _parse_t_lines(stdout: str, names: list[str] | None = None) -> tuple[list[CaseResult], dict[int, str]]:
    """Разбирает T-строки stdout в CaseResult; names=None — discovery-режим (имя берётся из строки)."""
    found: dict[int, tuple[bool, str]] = {}
    discovered: dict[int, str] = {}
    for raw in stdout.splitlines():
        m = _T_LINE.match(raw.strip())
        if not m:
            continue
        idx = int(m.group(1))
        passed = m.group(2) == "PASS"
        rest = (m.group(3) or "").strip()
        if names is None:
            # в discovery-режиме имя — первая строка до двоеточия причины FAIL
            label = rest.split(":")[0].strip() if not passed else rest
            discovered[idx] = label
            found[idx] = (passed, "" if passed else rest)
        else:
            detail = rest
            case_name = names[idx] if idx < len(names) else ""
            if not passed and case_name and detail.startswith(case_name + ":"):
                detail = detail[len(case_name) + 1 :].strip()
            found[idx] = (passed, "" if passed else detail)
    results: list[CaseResult] = []
    if names is None:
        for idx in sorted(found):
            ok, detail = found[idx]
            results.append(CaseResult(discovered.get(idx, "test_" + str(idx)), ok, detail))
    else:
        for i, name in enumerate(names):
            if i in found:
                ok, detail = found[i]
                results.append(CaseResult(name, ok, detail))
            else:
                results.append(CaseResult(name, False, "программа завершилась до этого теста"))
    return results, found


def _run_composed(code: str) -> dict:
    """Прогон собранного скрипта в песочнице (только python)."""
    return get_sandbox().run_script("python", code)


# ---------------------------------------------------------------- типы 1 и 4

def run_assert_cases(code: str, cases: list[dict]) -> tuple[str, list[CaseResult]]:
    """Прогон скрытых assert-кейсов после кода студента. Возвращает (status, results)."""
    if not cases:
        return "ok", []
    res = _run_composed(code + "\n\n" + _assert_driver(cases))
    names = [c.get("name", "test" + str(i)) for i, c in enumerate(cases)]
    results, _ = _parse_t_lines(res["stdout"], names)
    return res["status"], results


# ---------------------------------------------------------------- тип 2 (мутанты)

def run_mutation(student_code: str, reference_code: str, mutants: list[dict]) -> dict:
    """Тесты студента проверяются на эталоне (должны пройти) и на мутантах (должны ловиться)."""
    out = {
        "ok": False,
        "tests_found": 0,
        "orig_ok": False,
        "orig_results": [],
        "mutants": [],
        "caught_count": 0,
        "note": "",
    }
    if MARKER not in student_code:
        out["note"] = "Не найден маркер «" + MARKER + "» — не удалось отделить ваши тесты."
        return out

    # Проверяем тесты на ЭТАЛОНЕ (функция выше маркера у студента могла быть изменена):
    # на корректном коде все тесты обязаны пройти.
    ref_func = reference_code.split(MARKER, 1)[0].rstrip()
    tests_part = MARKER + student_code.split(MARKER, 1)[1]
    status, results = _run_discovery(ref_func + "\n\n" + tests_part)
    out["tests_found"] = len(results)
    out["orig_results"] = [asdict(r) for r in results]
    if not results:
        out["note"] = "Функции test_* не найдены — добавьте тесты ниже маркера."
        return out
    failed = [r.name for r in results if not r.passed]
    if failed:
        out["note"] = "Ваши тесты падают на корректном коде: " + ", ".join(failed[:5])
        return out
    if len(results) < MIN_STUDENT_TESTS:
        out["note"] = (
            f"Нужно минимум {MIN_STUDENT_TESTS} теста, найдено {len(results)}."
        )
        return out
    out["orig_ok"] = True

    for mut in mutants or []:
        composed = (mut.get("code") or "") + "\n\n" + tests_part + _DISCOVERY_DRIVER
        mres = _run_composed(composed)
        if mres["status"] != "ok":
            # Мутант упал или завис — программа не отработала чисто, это и есть поимка
            caught = True
            note = "мутант не завершился (краш/таймаут)"
        else:
            m_results, _ = _parse_t_lines(mres["stdout"], None)
            caught = any(not r.passed for r in m_results) or "NO TESTS FOUND" in mres["stdout"]
            note = ""
        out["mutants"].append(
            {"name": mut.get("name", "mutant"), "caught": caught, "note": note}
        )
    out["caught_count"] = sum(1 for m in out["mutants"] if m["caught"])
    out["ok"] = True
    return out


def _run_discovery(code: str) -> tuple[str, list[CaseResult]]:
    """Прогон test_* функций студента через discovery-драйвер."""
    res = _run_composed(code + _DISCOVERY_DRIVER)
    results, _ = _parse_t_lines(res["stdout"], None)
    return res["status"], results


# ---------------------------------------------------------------- тип 3 (AST)

_DECISION_NODES = (ast.If, ast.For, ast.While)


def max_nesting(code: str) -> int | None:
    """Максимальная глубина вложенных if/for/while внутри функций. None при синтаксической ошибке."""
    try:
        tree = ast.parse(code)
    except SyntaxError:
        return None
    best = 0

    def walk(node, depth: int) -> None:
        """Обход AST-узлов с учётом максимальной глубины if/for/while."""
        nonlocal best
        for child in ast.iter_child_nodes(node):
            if isinstance(child, _DECISION_NODES):
                best = max(best, depth + 1)
                walk(child, depth + 1)
            else:
                walk(child, depth)

    for node in tree.body:
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            walk(node, 0)
    return best


# ---------------------------------------------------------------- скоринг

def evaluate(
    task_type: str,
    code: str,
    initial_code: str,
    reference_code: str,
    prompts: list[str],
    status: str,
    results: list[CaseResult],
    mutation: dict | None = None,
    min_mutants_caught: int = 1,
) -> dict:
    """Детерминированный скоринг. passed = зелёные тесты; баллы показываем всегда."""
    breakdown: dict = {}

    # 50 — тесты
    tests_ok = bool(results) and status == "ok" and all(r.passed for r in results)
    if task_type == "tests":
        tests_ok = bool(mutation and mutation.get("orig_ok")) and (
            mutation["caught_count"] >= min_mutants_caught
        )
    if task_type == "refactor":
        nesting = max_nesting(code)
        ast_ok = nesting is not None and nesting <= MAX_NESTING
        tests_ok = tests_ok and ast_ok
        breakdown["вложенность_if_for_while"] = nesting if nesting is not None else "синтаксическая ошибка"
    breakdown["тесты"] = 50 if tests_ok else 0

    # 20 — итерации (число промптов)
    p = len(prompts)
    it_pts = 20 if p <= 3 else 15 if p <= 6 else 10 if p <= 10 else 5
    breakdown["итерации_диалога"] = it_pts
    breakdown["число_промптов"] = p

    # 15 — качество промптов
    if p:
        good = sum(
            1
            for t in prompts
            if len(t.strip()) >= PROMPT_MIN_LEN
            and any(w in t.lower() for w in SIGNAL_WORDS)
        )
        q_pts = round(15 * good / p)
    else:
        q_pts = 0
    breakdown["качество_промптов"] = q_pts

    # 15 — гигиена diff
    hy = 15
    if "```" in code:
        hy -= 5
    ref_len = max(len(reference_code or ""), len(initial_code or ""), 1)
    if len(code) > 2.2 * ref_len:
        hy -= 5
    if task_type == "tests" and MARKER not in code:
        hy -= 5
    breakdown["гигиена_кода"] = max(hy, 0)

    total = min((50 if tests_ok else 0) + it_pts + q_pts + max(hy, 0), 100)
    return {"passed": tests_ok, "score": total, "breakdown": breakdown}
