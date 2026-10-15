"""Банк задач: бинарный поиск и сортировки (junior/middle)."""

from app.seed.bank_common import T

TASKS = [
    {
        "slug": "search-rotated-array",
        "title": "Поиск в повёрнутом массиве",
        "pattern": "binary_search",
        "level": "middle",
        "legend": """Отсортированный по возрастанию массив уникальных номеров заказов «прокрутили» на неизвестное число позиций. Найди индекс заданного номера за O(log N).

Формат ввода
Первая строка — n и target (1 <= n <= 10^5). Вторая — n различных чисел — повёрнутый отсортированный массив.

Формат вывода
Индекс target (с 0) или -1.""",
        "hints": [
            "Это бинарный поиск: одна из половин [l..r] гарантированно отсортирована.",
            "Сравни mid с левым краем — поймёшь, какая половина «чистая», и решишь, где искать.",
        ],
        "tests": [
            T("sample", "7 0\n4 5 6 7 0 1 2\n", "4", sample=True),
            T("absent", "7 3\n4 5 6 7 0 1 2\n", "-1"),
            T("single", "1 5\n5\n", "0"),
            T("no_rotation", "5 1\n1 2 3 4 5\n", "0"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n, t = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))
l, r = 0, n - 1
ans = -1
while l <= r:
    m = (l + r) // 2
    if a[m] == t:
        ans = m; break
    if a[l] <= a[m]:
        if a[l] <= t < a[m]: r = m - 1
        else: l = m + 1
    else:
        if a[m] < t <= a[r]: l = m + 1
        else: r = m - 1
print(ans)
""",
    },
    {
        "slug": "first-last-position",
        "title": "Первое и последнее вхождение",
        "pattern": "binary_search",
        "level": "middle",
        "legend": """В журнале регистрации (отсортированном по ID) один пациент мог записаться несколько раз. За O(log N) найди диапазон строк с заданным ID.

Формат ввода
Первая строка — n и target (1 <= n <= 10^5). Вторая — n чисел по возрастанию (есть повторы).

Формат вывода
Индексы первого и последнего вхождения (с 0) через пробел; если нет — «-1 -1».""",
        "hints": [
            "Два бинарных поиска: левая граница и правая граница.",
            "Левая граница: если a[mid] >= target — r = mid, иначе l = mid + 1.",
        ],
        "tests": [
            T("sample", "9 8\n5 7 7 8 8 8 8 10 12\n", "3 6", sample=True),
            T("absent", "6 4\n1 2 3 6 7 9\n", "-1 -1"),
            T("all_same", "5 3\n3 3 3 3 3\n", "0 4"),
            T("single", "1 7\n7\n", "0 0"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n, t = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))

def lower(x):
    l, r = 0, n
    while l < r:
        m = (l + r) // 2
        if a[m] < x: l = m + 1
        else: r = m
    return l

lo = lower(t)
if lo == n or a[lo] != t:
    print(-1, -1)
else:
    print(lo, lower(t + 1) - 1)
""",
    },
    {
        "slug": "peak-mountain-index",
        "title": "Вершина горного массива",
        "pattern": "binary_search",
        "level": "junior",
        "legend": """Профиль высот трассы — «горный массив»: сначала строго вверх, потом строго вниз. Найди индекс самой высокой точки за O(log N).

Формат ввода
Первая строка — n (3 <= n <= 10^5). Вторая — n чисел: ровно один пик, соседние элементы различны.

Формат вывода
Индекс пика (с 0).""",
        "hints": [
            "Если a[mid] < a[mid+1] — ты на подъёме, пик справа; иначе ты на пике или спуске.",
            "Бинарный поиск по условию a[m] < a[m+1].",
        ],
        "tests": [
            T("sample", "5\n1 3 5 4 2\n", "2", sample=True),
            T("small", "3\n0 1 0\n", "1"),
            T("late_peak", "6\n1 2 3 4 9 8\n", "4"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); a = list(map(int, data[1:1+n]))
l, r = 0, n - 1
while l < r:
    m = (l + r) // 2
    if a[m] < a[m + 1]: l = m + 1
    else: r = m
print(l)
""",
    },
    {
        "slug": "sqrt-floor",
        "title": "Целочисленный квадратный корень",
        "pattern": "binary_search",
        "level": "junior",
        "legend": """Для разметки квадратного участка нужен целый размер стороны — наибольшее целое x0, такое что x0^2 <= площадь. Библиотеку math не использовать!

Формат ввода
Одно число x (0 <= x <= 2*10^9).

Формат вывода
Наибольшее целое x0 с x0^2 <= x.""",
        "hints": [
            "Бинарный поиск по диапазону возможных ответов [0..x].",
            "mid*mid может не влезать в 32 бита — берите 64-битный тип.",
        ],
        "tests": [
            T("sample", "16\n", "4", sample=True),
            T("not_square", "8\n", "2"),
            T("zero", "0\n", "0"),
            T("large", "1000000000\n", "31622"),
        ],
        "reference_solution": """import sys

x = int(sys.stdin.read().strip())
l, r = 0, x + 1
while l < r:
    m = (l + r) // 2
    if m * m <= x: l = m + 1
    else: r = m
print(l - 1)
""",
    },
    {
        "slug": "kth-largest",
        "title": "K-й по величине элемент",
        "pattern": "sorting",
        "level": "middle",
        "legend": """Аудиторам нужен k-й по величине объём транзакций из неупорядоченной выгрузки. Полная сортировка слишком дорога — решите за O(N) в среднем (quickselect) или O(N log K).

Формат ввода
Первая строка — n и k (1 <= k <= n <= 10^6). Вторая — n чисел (-10^9 <= a[i] <= 10^9).

Формат вывода
K-й по величине элемент (1 = максимум); повторы считаются отдельно.""",
        "hints": [
            "k-й по величине = (n-k)-й по возрастанию.",
            "Quickselect с разбиением как в Quick Sort, или min-куча размера k.",
        ],
        "tests": [
            T("sample", "6 2\n3 2 1 5 6 4\n", "5", sample=True),
            T("k_is_n", "4 4\n7 1 9 3\n", "1"),
            T("duplicates", "5 2\n2 2 2 1 3\n", "2"),
            T("single", "1 1\n42\n", "42"),
        ],
        "reference_solution": """import sys, random

data = sys.stdin.read().split()
n, k = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))
target = n - k
lo, hi = 0, n - 1
while lo < hi:
    pivot = a[random.randint(lo, hi)]
    i, j, g = lo, lo, hi
    while j <= g:
        if a[j] < pivot: a[i], a[j] = a[j], a[i]; i += 1; j += 1
        elif a[j] > pivot: a[j], a[g] = a[g], a[j]; g -= 1
        else: j += 1
    if target < i: hi = i - 1
    elif target > g: lo = g + 1
    else: break
print(a[target])
""",
    },
    {
        "slug": "merge-sorted-arrays",
        "title": "Слияние двух отсортированных массивов",
        "pattern": "sorting",
        "level": "junior",
        "legend": """Две смены сдали каждая свой отсортированный список заявок. Объедини их в один отсортированный список за O(N+M), не сортируя результат.

Формат ввода
Первая строка — n и m (1 <= n, m <= 10^5). Вторая — n чисел по возрастанию. Третья — m чисел по возрастанию.

Формат вывода
n + m чисел через пробел — объединённый отсортированный массив.""",
        "hints": [
            "Это шаг merge из Merge Sort: два указателя, бери меньший из текущих.",
        ],
        "tests": [
            T("sample", "3 3\n1 3 5\n2 4 6\n", "1 2 3 4 5 6", sample=True),
            T("negatives", "2 2\n-5 0\n-10 -1\n", "-10 -5 -1 0"),
            T("equal_values", "2 2\n1 1\n1 1\n", "1 1 1 1"),
            T("disjoint", "3 2\n10 20 30\n1 2\n", "1 2 10 20 30"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n])); b = list(map(int, data[2+n:2+n+m]))
i = j = 0; res = []
while i < n and j < m:
    if a[i] <= b[j]: res.append(a[i]); i += 1
    else: res.append(b[j]); j += 1
res.extend(a[i:]); res.extend(b[j:])
print(' '.join(map(str, res)))
""",
    },
]
