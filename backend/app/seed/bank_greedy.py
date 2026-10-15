"""Банк задач: жадные алгоритмы (junior/middle)."""

from app.seed.bank_common import T

TASKS = [
    {
        "slug": "merge-intervals",
        "title": "Объединение интервалов",
        "pattern": "greedy",
        "level": "middle",
        "legend": """Сервер получил n окон занятости (начало, конец) в произвольном порядке. Объедини пересекающиеся и соприкасающиеся окна ([1,4] и [4,5] -> [1,5]) в минимальный набор непересекающихся интервалов.

Формат ввода
Первая строка — n (1 <= n <= 10^5). Далее n строк: l r (0 <= l < r <= 10^9), в произвольном порядке.

Формат вывода
Объединённые интервалы, по одному «l r» на строку, отсортированные по возрастанию l.""",
        "hints": [
            "Отсортируй интервалы по началу — жадность сработает.",
            "Иди слева направо и расширяй текущий интервал, пока начало следующего <= его концу.",
        ],
        "tests": [
            T("sample", "4\n1 3\n2 6\n8 10\n15 18\n", "1 6\n8 10\n15 18", sample=True),
            T("touching", "2\n1 4\n4 5\n", "1 5"),
            T("nested", "3\n1 10\n2 5\n6 7\n", "1 10"),
            T("unsorted", "3\n8 10\n1 3\n2 6\n", "1 6\n8 10"),
        ],
        "reference_solution": """import sys

data = list(map(int, sys.stdin.read().split()))
n = data[0]
iv = sorted((data[1+2*i], data[2+2*i]) for i in range(n))
res = [iv[0]]
for l, r in iv[1:]:
    if l <= res[-1][1]:
        if r > res[-1][1]: res[-1] = (res[-1][0], r)
    else:
        res.append((l, r))
print('\\n'.join(f'{l} {r}' for l, r in res))
""",
    },
    {
        "slug": "jump-game",
        "title": "Прыжки по массиву",
        "pattern": "greedy",
        "level": "junior",
        "legend": """Стоишь на первой клетке ряда; в клетке i написано число a[i] — максимум шагов вперёд отсюда. Можно ли добраться до последней клетки?

Формат ввода
Первая строка — n (1 <= n <= 10^5). Вторая — n чисел (0 <= a[i] <= 10^5).

Формат вывода
Yes или No.""",
        "hints": [
            "Не нужен полный перебор — жадно поддерживай самую далёкую достижимую позицию.",
            "Если дошёл до i, а reach < i — дальше хода нет.",
        ],
        "tests": [
            T("sample", "5\n2 3 1 1 4\n", "Yes", sample=True),
            T("stuck", "5\n3 2 1 0 4\n", "No"),
            T("single", "1\n0\n", "Yes"),
            T("zero_middle", "4\n1 0 1 0\n", "No"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); a = list(map(int, data[1:1+n]))
reach = 0; ok = True
for i in range(n):
    if i > reach: ok = False; break
    reach = max(reach, i + a[i])
print('Yes' if ok else 'No')
""",
    },
    {
        "slug": "best-time-stock",
        "title": "Лучшая сделка с акциями",
        "pattern": "greedy",
        "level": "junior",
        "legend": """Дан ряд цены акции по дням. Нужно купить один раз и продать один раз позже (в другой день), чтобы прибыль была максимальной. Продавать в убыток невыгодно — можно не торговать вовсе.

Формат ввода
Первая строка — n (2 <= n <= 10^5). Вторая — n цен (0 <= p <= 10^9).

Формат вывода
Максимальная прибыль (или 0, если выгоды нет).""",
        "hints": [
            "Иди по дням и поддерживай минимальную цену покупки до текущего момента.",
            "Ответ — максимум от (текущая цена - минимум до неё).",
        ],
        "tests": [
            T("sample", "6\n7 1 5 3 6 4\n", "5", sample=True),
            T("always_falling", "6\n7 6 4 3 1 0\n", "0"),
            T("big_jump", "2\n1 100000\n", "99999"),
            T("middle", "5\n2 4 1 3 5\n", "4"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); p = list(map(int, data[1:1+n]))
min_price = p[0]; best = 0
for x in p[1:]:
    best = max(best, x - min_price)
    min_price = min(min_price, x)
print(best)
""",
    },
]
