from app.seed.bank_common import T

TASKS = [
    {
        "slug": "climbing-stairs",
        "title": "Лестница",
        "pattern": "dp",
        "level": "junior",
        "legend": """Лестница из n ступенек. За шаг можно подняться на 1 или на 2 ступеньки. Сколькими различными способами добраться до вершины?

Формат ввода
Одно число n (1 <= n <= 45).

Формат вывода
Число способов.""",
        "hints": [
            "f(n) зависит от f(n-1) и f(n-2): последний шаг — одна ступенька или две.",
            "Базовые случаи f(1)=1, f(2)=2; считай снизу вверх без хранения всего массива.",
        ],
        "tests": [
            T("sample", "5\n", "8", sample=True),
            T("one", "1\n", "1"),
            T("two", "2\n", "2"),
            T("ten", "10\n", "89"),
        ],
        "reference_solution": """import sys

n = int(sys.stdin.read().strip())
a, b = 1, 2
for _ in range(n - 1):
    a, b = b, a + b
print(a)
""",
    },
    {
        "slug": "knapsack-01",
        "title": "Рюкзак 0/1",
        "pattern": "dp",
        "level": "middle",
        "legend": """Рюкзак грузоподъёмности W и n предметов (вес, ценность). Брать предмет можно только целиком. Какая максимальная суммарная ценность поместится?

Формат ввода
Первая строка — n и W (1 <= n <= 100, 0 <= W <= 10^4). Далее n строк: вес и ценность (1 <= вес <= 10^4, 1 <= ценность <= 10^5).

Формат вывода
Максимальная суммарная ценность.""",
        "hints": [
            "dp[w] — максимум ценности при вместимости w.",
            "Переход dp[w] = max(dp[w], dp[w-wt] + val); обходи w СПРАВА НАЛЕВО, чтобы не взять предмет дважды.",
        ],
        "tests": [
            T("sample", "3 50\n10 60\n20 100\n30 120\n", "220", sample=True),
            T("zero_capacity", "2 0\n1 5\n2 6\n", "0"),
            T("single_fits", "1 10\n10 100\n", "100"),
            T("nothing_fits", "2 5\n6 10\n7 12\n", "0"),
        ],
        "reference_solution": """import sys

data = list(map(int, sys.stdin.read().split()))
n, W = data[0], data[1]
items = [(data[2+2*i], data[3+2*i]) for i in range(n)]
dp = [0] * (W + 1)
for wt, val in items:
    for w in range(W, wt - 1, -1):
        dp[w] = max(dp[w], dp[w - wt] + val)
print(dp[W])
""",
    },
    {
        "slug": "min-path-grid",
        "title": "Минимальный путь в матрице",
        "pattern": "dp",
        "level": "middle",
        "legend": """По матрице стоимостей идут из левого верхнего угла в правый нижний, двигаясь только вправо или вниз. Найди минимальную суммарную стоимость пути.

Формат ввода
Первая строка — n и m (1 <= n, m <= 300). Далее n строк по m целых чисел (-10^3 <= c <= 10^3).

Формат вывода
Минимальная сумма пути (включая старт и финиш).""",
        "hints": [
            "dp[i][j] = c[i][j] + min(dp[i-1][j], dp[i][j-1]).",
            "Первая строка и первый столбец — частные случаи (только один предшественник).",
        ],
        "tests": [
            T("sample", "3 3\n1 3 1\n1 5 1\n4 2 1\n", "7", sample=True),
            T("single", "1 1\n5\n", "5"),
            T("row", "1 4\n1 2 3 4\n", "10"),
            T("negatives", "2 2\n-1 2\n3 -2\n", "-1"),
        ],
        "reference_solution": """import sys

data = list(map(int, sys.stdin.read().split()))
n, m = data[0], data[1]
c = [data[2+i*m:2+(i+1)*m] for i in range(n)]
dp = [[0]*m for _ in range(n)]
dp[0][0] = c[0][0]
for j in range(1, m): dp[0][j] = dp[0][j-1] + c[0][j]
for i in range(1, n): dp[i][0] = dp[i-1][0] + c[i][0]
for i in range(1, n):
    for j in range(1, m):
        dp[i][j] = c[i][j] + min(dp[i-1][j], dp[i][j-1])
print(dp[n-1][m-1])
""",
    },
    {
        "slug": "edit-distance",
        "title": "Расстояние редактирования",
        "pattern": "dp",
        "level": "senior",
        "legend": """Слово A нужно превратить в слово B минимальным числом операций: вставка символа, удаление символа, замена символа. Найди это число (расстояние Левенштейна).

Формат ввода
Две строки — слова A и B из строчных латинских букв (длина 1..500).

Формат вывода
Минимальное число операций.""",
        "hints": [
            "dp[i][j] — расстояние между префиксами A[:i] и B[:j].",
            "Если символы равны — dp[i][j] = dp[i-1][j-1]; иначе 1 + min(вставка, удаление, замена).",
            "Базовые случаи: dp[i][0] = i, dp[0][j] = j.",
        ],
        "tests": [
            T("sample", "kitten\nsitting\n", "3", sample=True),
            T("horse_ros", "horse\nros\n", "3"),
            T("equal", "abc\nabc\n", "0"),
            T("intention", "intention\nexecution\n", "5"),
        ],
        "reference_solution": """import sys

a, b = sys.stdin.read().split()[:2]
n, m = len(a), len(b)
dp = list(range(m + 1))
for i in range(1, n + 1):
    prev, dp[0] = dp[0], i
    for j in range(1, m + 1):
        cur = dp[j]
        if a[i-1] == b[j-1]: dp[j] = prev
        else: dp[j] = 1 + min(prev, dp[j], dp[j-1])
        prev = cur
print(dp[m])
""",
    },
    {
        "slug": "longest-common-subsequence",
        "title": "Наибольшая общая подпоследовательность",
        "pattern": "dp",
        "level": "middle",
        "legend": """Два текста сравнивают по «отпечаткам»: найдите длину наибольшей общей подпоследовательности (символы идут в одном порядке, но не обязательно подряд).

Формат ввода
Две строки — слова из строчных латинских букв (длина 1..500).

Формат вывода
Длина НОП.""",
        "hints": [
            "dp[i][j] — длина НОП префиксов A[:i], B[:j].",
            "Символы равны: dp = dp[i-1][j-1] + 1; иначе max(dp[i-1][j], dp[i][j-1]).",
        ],
        "tests": [
            T("sample", "abcde\nace\n", "3", sample=True),
            T("disjoint", "abc\nxyz\n", "0"),
            T("classic", "aggtab\ngxtxayb\n", "4"),
            T("identical", "aaaa\naaaa\n", "4"),
        ],
        "reference_solution": """import sys

a, b = sys.stdin.read().split()[:2]
m = len(b)
dp = [0] * (m + 1)
for ca in a:
    prev = 0
    for j, cb in enumerate(b, 1):
        cur = dp[j]
        if ca == cb: dp[j] = prev + 1
        else: dp[j] = max(dp[j], dp[j-1])
        prev = cur
print(dp[m])
""",
    },
    {
        "slug": "coin-change",
        "title": "Размен монетами",
        "pattern": "dp",
        "level": "middle",
        "legend": """Автомат выдаёт сумму k минимальным числом монет из имеющихся номиналов (монеты одного номинала можно использовать многократно). Если размен невозможен — так и скажи.

Формат ввода
Первая строка — n и k (1 <= n <= 20, 0 <= k <= 10^4). Вторая — n номиналов (1 <= c <= 10^4).

Формат вывода
Минимальное число монет или -1.""",
        "hints": [
            "dp[s] — минимум монет для суммы s.",
            "dp[s] = min(dp[s - c] + 1) по всем номиналам c <= s; dp[0] = 0, остальное +бесконечность.",
        ],
        "tests": [
            T("sample", "3 11\n1 2 5\n", "3", sample=True),
            T("impossible", "1 3\n2\n", "-1"),
            T("zero_amount", "4 0\n1 2 5 7\n", "0"),
            T("divisible", "2 27\n3 9\n", "3"),
        ],
        "reference_solution": """import sys

data = list(map(int, sys.stdin.read().split()))
n, k = data[0], data[1]
coins = data[2:2+n]
INF = 10**9
dp = [INF] * (k + 1)
dp[0] = 0
for s in range(1, k + 1):
    for c in coins:
        if c <= s and dp[s - c] + 1 < dp[s]:
            dp[s] = dp[s - c] + 1
print(dp[k] if dp[k] < INF else -1)
""",
    },
]
