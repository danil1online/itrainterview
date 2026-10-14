"""Банк задач «Вайб-Кодинг»: 4 типа по 2 задачи. Идемпотентен по slug.

hidden_tests — assert-кейсы, дописываемые после кода студента (типы bugfix/refactor/contract).
Для типа tests hidden_tests не используются; вместо них mutants — мутации эталона,
которые тесты студента обязаны ловить.
"""

MARKER = "# === ВАШИ ТЕСТЫ НИЖЕ"

_RULES_BUGFIX = (
    "**Как работать.** 1) Запустите тесты и посмотрите, какой кейс падает. "
    "2) Скопируйте в чат **только** текст ошибки и спорный фрагмент функции — не весь файл. "
    "3) Спросите модель, в чём причина и как её исправить точечно. "
    "4) Внимательно ревьюьте ответ: Qwen 3B часто теряет импорты и крайние случаи."
)

_RULES_TESTS = (
    "**Как работать.** Ниже маркера напишите (с помощью модели) функции `test_*` с assert'ами. "
    "Модель обожает генерировать «тривиальные» тесты — система это видит: ваши тесты прогоняются "
    "против скрытых мутаций кода, и вы должны поймать их достаточное количество. "
    "Требуйте от модели именно **граничные** случаи: пустое значение, None, минимум/максимум длины."
)

_RULES_REFACTOR = (
    "**Как работать.** Код работает, но его больно читать. Ваша цель — переписать его силами модели "
    "так, чтобы максимальная вложенность `if/for/while` стала не больше 2 (guard clauses / выход на "
    "помощника-функцию). Формулируйте критерии явно: «перепиши с ранними возвратами, сохранив логику». "
    "После каждого ответа модели — прогон тестов: рефакторинг не должен менять поведение."
)

_RULES_CONTRACT = (
    "**Как работать.** Тела функции нет — есть только сигнатура и docstring-контракт. "
    "Составьте промпт так, чтобы модель выдала рабочий код с первого-второго раза: укажите "
    "тип возвращаемого значения, поведение на краях, формат («верни только код без пояснений»). "
    "Плохой промпт = синтаксическая ошибка или неверная логика — уточняйте формулировки."
)


VIBE_TASKS: list[dict] = [
    # ------------------------------------------------------------------ bugfix
    {
        "slug": "vibe-discount-null",
        "task_type": "bugfix",
        "title": "Скидка в корзине ломается на None",
        "description_md": (
            "Функция `apply_discount` считает итог корзины со скидкой. На пустом списке она ещё "
            "справляется, но если передать `items=None` (товары не загрузились) или percent вне "
            "диапазона 0..100 — результат странный или краш.\n\n" + _RULES_BUGFIX +
            "\n\n**Подсказка метода:** скормите модели падающий кейс и текст ошибки целиком, "
            "но не весь файл — только функцию."
        ),
        "initial_code": (
            "def apply_discount(items, percent):\n"
            '    """Итоговая сумма корзины со скидкой percent%.\n'
            "    items — список цен либо None; пустой список/None -> 0.0.\n"
            "    percent вне 0..100 ограничивается этим диапазоном.\"\"\"\n"
            "    total = 0\n"
            "    for price in items:\n"
            "        total += price\n"
            "    return round(total * (100 - percent) / 100, 2)\n"
        ),
        "hidden_tests": [
            {"name": "None вместо товаров", "code": "assert apply_discount(None, 10) == 0.0"},
            {"name": "пустая корзина", "code": "assert apply_discount([], 50) == 0.0"},
            {"name": "без скидки", "code": "assert apply_discount([100], 0) == 100"},
            {"name": "половинная скидка", "code": "assert apply_discount([10.5, 20.5], 50) == 15.5"},
            {"name": "percent больше 100", "code": "assert apply_discount([100], 150) == 0.0"},
            {"name": "отрицательный percent", "code": "assert apply_discount([80], -10) == 80"},
        ],
        "reference_solution": (
            "def apply_discount(items, percent):\n"
            '    """Итоговая сумма корзины со скидкой percent%.\"\"\"\n'
            "    if not items:\n"
            "        return 0.0\n"
            "    percent = max(0, min(100, percent))\n"
            "    total = sum(items)\n"
            "    return round(total * (100 - percent) / 100, 2)\n"
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
    {
        "slug": "vibe-top-products",
        "task_type": "bugfix",
        "title": "Топ-N товаров: выход за границу списка",
        "description_md": (
            "`top_products` возвращает n наибольших цен по убыванию, но падает, если `n` больше "
            "числа товаров, а `prices=None` вообще не обработан. Добейтесь от модели корректного "
            "поведения: выход за границы — это не исключение, а ограничение (clamp).\n\n" + _RULES_BUGFIX
        ),
        "initial_code": (
            "def top_products(prices, n):\n"
            '    """Список из n наибольших цен по убыванию.\n'
            "    prices может быть None -> [].\n"
            "    Если n больше длины списка или отрицательное — берётся доступное количество.\"\"\"\n"
            "    result = []\n"
            "    pool = sorted(prices)\n"
            "    for _ in range(n):\n"
            "        result.append(pool.pop())\n"
            "    return result\n"
        ),
        "hidden_tests": [
            {"name": "базовый случай", "code": "assert top_products([3, 1, 2], 2) == [3, 2]"},
            {"name": "n больше списка", "code": "assert top_products([5], 10) == [5]"},
            {"name": "None вместо цен", "code": "assert top_products(None, 3) == []"},
            {"name": "отрицательный n", "code": "assert top_products([1, 2], -1) == []"},
            {"name": "пустой список", "code": "assert top_products([], 2) == []"},
        ],
        "reference_solution": (
            "def top_products(prices, n):\n"
            '    """Список из n наибольших цен по убыванию.\"\"\"\n'
            "    if not prices:\n"
            "        return []\n"
            "    pool = sorted(prices, reverse=True)\n"
            "    n = max(0, min(n, len(pool)))\n"
            "    return pool[:n]\n"
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
    # ------------------------------------------------------------------ tests
    {
        "slug": "vibe-password-tests",
        "task_type": "tests",
        "title": "Юнит-тесты для валидатора паролей",
        "description_md": (
            "Дан готовый `validate_password` (длина 8..64, верхняя и нижняя буквы, цифра, "
            "спецсимвол `!@#$%^&*`). Напишите **не менее 3** функций `test_*` с assert'ами ниже "
            "маркера. Скрытая проверка: ваши тесты прогоняются против эталона (должны пройти) "
            "и против мутаций кода — нужно поймать минимум 2 из 4.\n\n" + _RULES_TESTS +
            "\n\n**Идеи граничных случаев:** пароль короче 8 символов; только нижний регистр; "
            "`None`; спецсимвол `^` как единственный спецсимвол."
        ),
        "initial_code": (
            "def validate_password(pwd):\n"
            '    """True, если пароль валиден: длина 8..64, есть заглавная и строчная буквы,\n'
            "    есть цифра, есть спецсимвол из !@#$%^&*.\"\"\"\n"
            "    if pwd is None or not isinstance(pwd, str):\n"
            "        return False\n"
            "    if len(pwd) < 8 or len(pwd) > 64:\n"
            "        return False\n"
            "    if not any(c.isupper() for c in pwd):\n"
            "        return False\n"
            "    if not any(c.islower() for c in pwd):\n"
            "        return False\n"
            "    if not any(c.isdigit() for c in pwd):\n"
            "        return False\n"
            '    if not any(c in "!@#$%^&*" for c in pwd):\n'
            "        return False\n"
            "    return True\n"
            "\n\n" + MARKER + " (функции test_*, внутри assert) ===\n"
        ),
        "hidden_tests": [],
        "reference_solution": "",
        "mutants": [
            {
                "name": "минимальная длина 6",
                "code": (
                    "def validate_password(pwd):\n"
                    "    if pwd is None or not isinstance(pwd, str):\n"
                    "        return False\n"
                    "    if len(pwd) < 6 or len(pwd) > 64:\n"
                    "        return False\n"
                    "    if not any(c.isupper() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.islower() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.isdigit() for c in pwd):\n"
                    "        return False\n"
                    '    if not any(c in "!@#$%^&*" for c in pwd):\n'
                    "        return False\n"
                    "    return True\n"
                ),
            },
            {
                "name": "забыли проверку верхнего регистра",
                "code": (
                    "def validate_password(pwd):\n"
                    "    if pwd is None or not isinstance(pwd, str):\n"
                    "        return False\n"
                    "    if len(pwd) < 8 or len(pwd) > 64:\n"
                    "        return False\n"
                    "    if not any(c.islower() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.isdigit() for c in pwd):\n"
                    "        return False\n"
                    '    if not any(c in "!@#$%^&*" for c in pwd):\n'
                    "        return False\n"
                    "    return True\n"
                ),
            },
            {
                "name": "нет защиты от None",
                "code": (
                    "def validate_password(pwd):\n"
                    "    if len(pwd) < 8 or len(pwd) > 64:\n"
                    "        return False\n"
                    "    if not any(c.isupper() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.islower() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.isdigit() for c in pwd):\n"
                    "        return False\n"
                    '    if not any(c in "!@#$%^&*" for c in pwd):\n'
                    "        return False\n"
                    "    return True\n"
                ),
            },
            {
                "name": "спецсимвол ^ выпал из набора",
                "code": (
                    "def validate_password(pwd):\n"
                    "    if pwd is None or not isinstance(pwd, str):\n"
                    "        return False\n"
                    "    if len(pwd) < 8 or len(pwd) > 64:\n"
                    "        return False\n"
                    "    if not any(c.isupper() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.islower() for c in pwd):\n"
                    "        return False\n"
                    "    if not any(c.isdigit() for c in pwd):\n"
                    "        return False\n"
                    '    if not any(c in "!@#$&*" for c in pwd):\n'
                    "        return False\n"
                    "    return True\n"
                ),
            },
        ],
        "min_mutants_caught": 2,
    },
    {
        "slug": "vibe-config-parser-tests",
        "task_type": "tests",
        "title": "Юнит-тесты для парсера конфига",
        "description_md": (
            "`parse_config` читает строки вида `ключ=значение`: пустые строки и комментарии "
            "(`#`) пропускает, пробелы вокруг `=` срезает, строки без `=` игнорирует. "
            "Напишите **не менее 3** тестов ниже маркера; поймайте минимум 2 из 3 мутаций.\n\n" + _RULES_TESTS +
            "\n\n**Идеи:** комментарий не должен попасть в dict; пробелы ` a = 1 ` срезаны; "
            "мусорная строка без `=` пропущена; пустой текст -> `{}`."
        ),
        "initial_code": (
            "def parse_config(text):\n"
            '    """Парсит строки \'ключ=значение\' в dict.\n'
            "    Пустые строки, комментарии ('#' в начале) и строки без '=' пропускаются;\n"
            "    пробелы вокруг '=' срезаются.\"\"\"\n"
            "    result = {}\n"
            "    for line in text.splitlines():\n"
            "        line = line.strip()\n"
            '        if not line or line.startswith("#"):\n'
            "            continue\n"
            '        if "=" not in line:\n'
            "            continue\n"
            '        key, _, value = line.partition("=")\n'
            "        result[key.strip()] = value.strip()\n"
            "    return result\n"
            "\n\n" + MARKER + " (функции test_*, внутри assert) ===\n"
        ),
        "hidden_tests": [],
        "reference_solution": "",
        "mutants": [
            {
                "name": "значение не срезается от пробелов",
                "code": (
                    "def parse_config(text):\n"
                    "    result = {}\n"
                    "    for line in text.splitlines():\n"
                    "        line = line.strip()\n"
                    '        if not line or line.startswith("#"):\n'
                    "            continue\n"
                    '        if "=" not in line:\n'
                    "            continue\n"
                    '        key, _, value = line.partition("=")\n'
                    "        result[key.strip()] = value\n"
                    "    return result\n"
                ),
            },
            {
                "name": "комментарии не пропускаются",
                "code": (
                    "def parse_config(text):\n"
                    "    result = {}\n"
                    "    for line in text.splitlines():\n"
                    "        line = line.strip()\n"
                    "        if not line:\n"
                    "            continue\n"
                    '        if "=" not in line:\n'
                    "            continue\n"
                    '        key, _, value = line.partition("=")\n'
                    "        result[key.strip()] = value.strip()\n"
                    "    return result\n"
                ),
            },
            {
                "name": "строки без '=' попадают в dict",
                "code": (
                    "def parse_config(text):\n"
                    "    result = {}\n"
                    "    for line in text.splitlines():\n"
                    "        line = line.strip()\n"
                    '        if not line or line.startswith("#"):\n'
                    "            continue\n"
                    '        key, _, value = line.partition("=")\n'
                    "        result[key.strip()] = value.strip()\n"
                    "    return result\n"
                ),
            },
        ],
        "min_mutants_caught": 2,
    },
    # ------------------------------------------------------------------ refactor
    {
        "slug": "vibe-refactor-guard",
        "task_type": "refactor",
        "title": "Оценки: лесенка if-else → guard clauses",
        "description_md": (
            "`grade_label` — вложенные if/else глубиной 5. Перепишите с **ранними возвратами** "
            "(guard clauses): максимальная вложенность `if/for/while` ≤ 2. Поведение менять нельзя — "
            "тесты golden.\n\n" + _RULES_REFACTOR
        ),
        "initial_code": (
            "def grade_label(score):\n"
            '    """Метка оценки: отлично>=90, хорошо>=75, удовл.>=60, иначе неудовл.;\n'
            '    None / не-число / вне 0..100 -> "ошибка".\"\"\"\n'
            "    if score is not None:\n"
            "        if isinstance(score, (int, float)):\n"
            "            if score < 0 or score > 100:\n"
            '                return "ошибка"\n'
            "            else:\n"
            "                if score >= 90:\n"
            '                    return "отлично"\n'
            "                else:\n"
            "                    if score >= 75:\n"
            '                        return "хорошо"\n'
            "                    else:\n"
            "                        if score >= 60:\n"
            '                            return "удовлетворительно"\n'
            "                        else:\n"
            '                            return "неудовлетворительно"\n'
            "        else:\n"
            '            return "ошибка"\n'
            "    else:\n"
            '        return "ошибка"\n'
        ),
        "hidden_tests": [
            {"name": "отлично", "code": 'assert grade_label(95) == "отлично"'},
            {"name": "хорошо", "code": 'assert grade_label(80) == "хорошо"'},
            {"name": "удовлетворительно", "code": 'assert grade_label(65) == "удовлетворительно"'},
            {"name": "неудовлетворительно", "code": 'assert grade_label(20) == "неудовлетворительно"'},
            {"name": "граница 90", "code": 'assert grade_label(90) == "отлично"'},
            {"name": "отрицательная", "code": 'assert grade_label(-5) == "ошибка"'},
            {"name": "больше 100", "code": 'assert grade_label(105) == "ошибка"'},
            {"name": "None", "code": 'assert grade_label(None) == "ошибка"'},
            {"name": "строка", "code": 'assert grade_label("x") == "ошибка"'},
        ],
        "reference_solution": (
            "def grade_label(score):\n"
            '    """Метка оценки с ранними возвратами.\"\"\"\n'
            "    if score is None or not isinstance(score, (int, float)):\n"
            '        return "ошибка"\n'
            "    if score < 0 or score > 100:\n"
            '        return "ошибка"\n'
            "    if score >= 90:\n"
            '        return "отлично"\n'
            "    if score >= 75:\n"
            '        return "хорошо"\n'
            "    if score >= 60:\n"
            '        return "удовлетворительно"\n'
            '    return "неудовлетворительно"\n'
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
    {
        "slug": "vibe-refactor-order-stats",
        "task_type": "refactor",
        "title": "Статистика заказов: разбить на две функции",
        "description_md": (
            "`order_stats` считает сумму и число валидных позиций, но внутри — вложенность 6. "
            "Разбейте на `is_valid_order(order)` + `order_stats(orders)` (или иной вариант), "
            "вложенность ≤ 2, поведение прежнее.\n\n" + _RULES_REFACTOR
        ),
        "initial_code": (
            "def order_stats(orders):\n"
            '    """(сумма, число позиций) по списку dict {price, qty}; невалидные пропускаются:\n'
            "    None-элементы, отсутствующие ключи, price не-число, qty не-int, price<0, qty<=0.\"\"\"\n"
            "    total = 0\n"
            "    count = 0\n"
            "    if orders is not None:\n"
            "        for o in orders:\n"
            "            if o is not None:\n"
            '                if "price" in o and "qty" in o:\n'
            '                    p = o["price"]\n'
            '                    q = o["qty"]\n'
            "                    if isinstance(p, (int, float)) and isinstance(q, int):\n"
            "                        if p >= 0 and q > 0:\n"
            "                            total += p * q\n"
            "                            count += 1\n"
            "    return (total, count)\n"
        ),
        "hidden_tests": [
            {"name": "одна позиция", "code": 'assert order_stats([{"price": 2, "qty": 3}]) == (6, 1)'},
            {"name": "None вместо списка", "code": "assert order_stats(None) == (0, 0)"},
            {"name": "None-элемент рядом с валидным", "code": 'assert order_stats([None, {"price": 1.5, "qty": 2}]) == (3.0, 1)'},
            {"name": "отрицательная цена", "code": 'assert order_stats([{"price": -1, "qty": 2}]) == (0, 0)'},
            {"name": "нулевое количество", "code": 'assert order_stats([{"price": 5, "qty": 0}]) == (0, 0)'},
            {"name": "нет ключа qty", "code": 'assert order_stats([{"price": 5}]) == (0, 0)'},
            {"name": "цена-строка", "code": 'assert order_stats([{"price": "x", "qty": 2}]) == (0, 0)'},
        ],
        "reference_solution": (
            "def is_valid_order(o):\n"
            '    """True, если o — dict с валидными price/qty.\"\"\"\n'
            "    if not isinstance(o, dict):\n"
            "        return False\n"
            '    if "price" not in o or "qty" not in o:\n'
            "        return False\n"
            '    p, q = o["price"], o["qty"]\n'
            "    if not isinstance(p, (int, float)) or not isinstance(q, int):\n"
            "        return False\n"
            "    return p >= 0 and q > 0\n"
            "\n\n"
            "def order_stats(orders):\n"
            '    """(сумма, число позиций) по списку dict {price, qty}.\"\"\"\n'
            "    if orders is None:\n"
            "        return (0, 0)\n"
            "    total = 0\n"
            "    count = 0\n"
            "    for o in orders:\n"
            "        if is_valid_order(o):\n"
            '            total += o["price"] * o["qty"]\n'
            "            count += 1\n"
            "    return (total, count)\n"
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
    # ------------------------------------------------------------------ contract
    {
        "slug": "vibe-format-date",
        "task_type": "contract",
        "title": "Форматирование даты по контракту",
        "description_md": (
            "Тела функции нет — только контракт в docstring. Получите от модели реализацию, "
            "проходящую скрытые тесты: ведущие нули, длина месяца, **высокосный год** "
            "(деление на 4/100/400).\n\n" + _RULES_CONTRACT
        ),
        "initial_code": (
            "def format_date(day, month, year):\n"
            '    """Строка \'ДД.ММ.ГГГГ\' с ведущими нулями.\n'
            "\n"
            "    Некорректная дата -> None:\n"
            "    - month вне 1..12 или day < 1;\n"
            "    - дней больше, чем в месяце: 31 в 1,3,5,7,8,10,12; иначе 30;\n"
            "      февраль — 29 в высокосный год (делится на 4, но не на 100,\n"
            "      если только не на 400), иначе 28.\n"
            '    Аргументы — целые числа.\n'
            '    """\n'
            "    pass\n"
        ),
        "hidden_tests": [
            {"name": "весенняя дата", "code": 'assert format_date(5, 3, 2026) == "05.03.2026"'},
            {"name": "31 апреля не бывает", "code": "assert format_date(31, 4, 2026) is None"},
            {"name": "высокосный 2024", "code": 'assert format_date(29, 2, 2024) == "29.02.2024"'},
            {"name": "не высокосный 2023", "code": "assert format_date(29, 2, 2023) is None"},
            {"name": "исключение на 400", "code": 'assert format_date(29, 2, 2000) == "29.02.2000"'},
            {"name": "исключение на 100", "code": "assert format_date(29, 2, 1900) is None"},
            {"name": "день ноль", "code": "assert format_date(0, 1, 2026) is None"},
            {"name": "конец года", "code": 'assert format_date(31, 12, 2026) == "31.12.2026"'},
        ],
        "reference_solution": (
            "def format_date(day, month, year):\n"
            "    if not isinstance(day, int) or not isinstance(month, int) or not isinstance(year, int):\n"
            "        return None\n"
            "    if month < 1 or month > 12 or day < 1:\n"
            "        return None\n"
            "    long_months = {1, 3, 5, 7, 8, 10, 12}\n"
            "    if month == 2:\n"
            "        leap = year % 4 == 0 and (year % 100 != 0 or year % 400 == 0)\n"
            "        max_day = 29 if leap else 28\n"
            "    elif month in long_months:\n"
            "        max_day = 31\n"
            "    else:\n"
            "        max_day = 30\n"
            "    if day > max_day:\n"
            "        return None\n"
            '    return "%02d.%02d.%04d" % (day, month, year)\n'
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
    {
        "slug": "vibe-filter-by-role",
        "task_type": "contract",
        "title": "Фильтр пользователей по роли",
        "description_md": (
            "Реализуйте `filter_by_role` строго по контракту: мусор в списке (`None`, не-словари, "
            "отсутствующий/не-строковый `name`) пропускается, результат отсортирован.\n\n" + _RULES_CONTRACT
        ),
        "initial_code": (
            "def filter_by_role(users, role):\n"
            '    """Отсортированный по алфавиту список имён пользователей с указанной ролью.\n'
            "\n"
            "    users — список dict с ключами name/role; могут встречаться None и мусор.\n"
            "    Пропускаются: не-словари, словари без 'name', записи с не-строковым name,\n"
            "    записи с role != переданной. users=None или пустой список -> [].\n"
            '    """\n'
            "    pass\n"
        ),
        "hidden_tests": [
            {
                "name": "фильтр и сортировка",
                "code": (
                    'assert filter_by_role([{"name": "В", "role": "dev"}, '
                    '{"name": "А", "role": "dev"}, {"name": "Б", "role": "qa"}], "dev") == ["А", "В"]'
                ),
            },
            {
                "name": "None-элементы пропускаются",
                "code": 'assert filter_by_role([None, {"name": "X", "role": "dev"}], "dev") == ["X"]',
            },
            {
                "name": "без name и name-не-строка",
                "code": 'assert filter_by_role([{"role": "dev"}, {"name": 5, "role": "dev"}], "dev") == []',
            },
            {"name": "нет совпадений", "code": 'assert filter_by_role([{"name": "A", "role": "qa"}], "dev") == []'},
            {"name": "users=None", "code": 'assert filter_by_role(None, "dev") == []'},
        ],
        "reference_solution": (
            "def filter_by_role(users, role):\n"
            "    if not users:\n"
            "        return []\n"
            "    names = []\n"
            "    for u in users:\n"
            "        if not isinstance(u, dict):\n"
            "            continue\n"
            '        if u.get("role") != role:\n'
            "            continue\n"
            '        name = u.get("name")\n'
            "        if isinstance(name, str):\n"
            "            names.append(name)\n"
            "    return sorted(names)\n"
        ),
        "mutants": [],
        "min_mutants_caught": 0,
    },
]
