from app.seed.bank_common import T

TASKS = [
    {
        "slug": "merge-k-sorted",
        "title": "Слияние K отсортированных списков",
        "pattern": "heap",
        "level": "senior",
        "legend": """Микросервисы присылают каждый свой отсортированный по возрастанию чанк логов. Собери все записи в один отсортированный поток за O(N log K).

Формат ввода
Первая строка — k (1 <= k <= 100). Далее k строк: сначала m_i, затем m_i чисел по возрастанию (m_i >= 0, суммарно не более 10^6 элементов).

Формат вывода
Все числа в одну строку через пробел — объединённый отсортированный поток.""",
        "hints": [
            "Храните в min-куче текущий «голова» каждого списка (значение, номер списка).",
            "Достал минимум — выводи, сдвигай указатель этого списка и клади следующего кандидата в кучу.",
        ],
        "tests": [
            T("sample", "3\n4 1 3 5 7\n3 2 4 6\n2 0 8\n", "0 1 2 3 4 5 6 7 8", sample=True),
            T("with_empty", "2\n3 1 2 3\n0\n", "1 2 3"),
            T("single_list", "1\n4 5 5 6 9\n", "5 5 6 9"),
            T("duplicates_across", "2\n2 1 1\n3 1 2 2\n", "1 1 1 2 2"),
        ],
        "reference_solution": """import sys, heapq

data = list(map(int, sys.stdin.read().split()))
k = data[0]
pos = 1
lists = []
for _ in range(k):
    m = data[pos]; pos += 1
    lists.append(data[pos:pos+m]); pos += m
h = [(lst[0], i, 0) for i, lst in enumerate(lists) if lst]
heapq.heapify(h)
res = []
while h:
    v, i, j = heapq.heappop(h)
    res.append(v)
    if j + 1 < len(lists[i]):
        heapq.heappush(h, (lists[i][j+1], i, j+1))
print(' '.join(map(str, res)))
""",
    },
    {
        "slug": "top-k-frequent",
        "title": "Топ-K самых частых элементов",
        "pattern": "heap",
        "level": "middle",
        "legend": """Аналитика трафика: по потоку запросов нужно назвать k самых частых элементов. При одинаковой частоте — раньше тот, у кого значение меньше.

Формат ввода
Первая строка — n и k (1 <= k <= число различных элементов <= 10^5). Вторая — n чисел (-10^9 <= a[i] <= 10^9).

Формат вывода
k чисел в одну строку: по убыванию частоты, при равенстве частот — по возрастанию значения.""",
        "hints": [
            "Посчитай частоты хеш-таблицей.",
            "Дальше — k лучших по (-частота, значение): partial sort или куча размера k.",
        ],
        "tests": [
            T("sample", "6 2\n1 1 1 2 2 3\n", "1 2", sample=True),
            T("all_ties", "5 2\n4 3 5 2 1\n", "1 2"),
            T("mixed", "4 3\n7 7 8 9\n", "7 8 9"),
            T("negative", "6 2\n-1 -1 -2 -2 -2 5\n", "-2 -1"),
        ],
        "reference_solution": """import sys
from collections import Counter

data = sys.stdin.read().split()
n, k = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))
cnt = Counter(a)
top = sorted(cnt.items(), key=lambda kv: (-kv[1], kv[0]))[:k]
print(' '.join(str(v) for v, _ in top))
""",
    },
    {
        "slug": "trie-prefix-count",
        "title": "Поиск по префиксу (автодополнение)",
        "pattern": "trie",
        "level": "middle",
        "legend": """Поисковик хранит словарь слов. Для каждого запроса-префикса нужно вернуть, сколько слов словаря начинаются с этого префикса.

Формат ввода
Первая строка — n (1 <= n <= 10^5). Далее n различных слов из строчных латинских букв (длина 1..30). Затем строка — q (1 <= q <= 10^5). Далее q префиксов (строчные буквы, длина 1..30).

Формат вывода
Для каждого запроса — число слов с данным префиксом, по одному на строку.""",
        "hints": [
            "Префиксное дерево: в каждом узле храни count — сколько слов проходят через узел.",
            "Для запроса спускайся по префиксу и верни count в последнем узле (или 0, если спуск оборвался).",
            "Можно и без дерева: посчитать все префиксы слов в хеш-таблице — но на собеседовании ждут Trie.",
        ],
        "tests": [
            T("sample", "3\napple\napp\napplication\n3\napp\nappl\napex\n", "3\n2\n0", sample=True),
            T("longer_prefix", "2\nab\nabc\n2\nabcd\nab\n", "0\n2"),
            T("exact_match", "1\nhello\n2\nhell\nhello\n", "1\n1"),
            T("single_word", "1\nz\n1\nz\n", "1"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0])
words = data[1:1+n]
q = int(data[1+n])
queries = data[2+n:2+n+q]
from collections import defaultdict
cnt = defaultdict(int)
for w in words:
    for i in range(1, len(w) + 1):
        cnt[w[:i]] += 1
print('\\n'.join(str(cnt.get(p, 0)) for p in queries))
""",
    },
    {
        "slug": "gcd-tiles",
        "title": "Плитка для пола (алгоритм Евклида)",
        "pattern": "math",
        "level": "junior",
        "legend": """Пол размером a на b нужно выложить КВАДРАТНОЙ плитой максимально возможного размера без резки. Каков размер стороны плиты? (Это НОД.)

Формат ввода
Два числа a и b (1 <= a, b <= 10^9) в одной строке.

Формат вывода
Максимальный целой размер стороны квадрата.""",
        "hints": [
            "Сторона должна делить и a, и b — значит это общий делитель; нужен наибольший.",
            "Алгоритм Евклида: gcd(a, b) = gcd(b, a mod b), база gcd(a, 0) = a.",
        ],
        "tests": [
            T("sample", "6 9\n", "3", sample=True),
            T("coprime", "13 7\n", "1"),
            T("classic", "24 36\n", "12"),
            T("consecutive_large", "1000000000 999999999\n", "1"),
        ],
        "reference_solution": """import sys

a, b = map(int, sys.stdin.read().split()[:2])
while b:
    a, b = b, a % b
print(a)
""",
    },
    {
        "slug": "linked-cycle-detect",
        "title": "Есть ли цикл в списке?",
        "pattern": "linked_list",
        "level": "junior",
        "legend": """Список задан массивом указателей: next[i] — индекс следующего узла для узла i, -1 означает «конец». Голова — узел 0. Двигаясь от головы, определи, попадёшь ли ты в цикл.

Формат ввода
Первая строка — n (1 <= n <= 10^5). Вторая — n чисел next[i] (-1 <= next[i] < n).

Формат вывода
Yes или No.""",
        "hints": [
            "Хеш-множество посещённых узлов решает, но на собеседовании ждут O(1) по памяти.",
            "Алгоритм Флойда «черепаха и заяц»: медленный идёт на 1, быстрый на 2; встретились — цикл.",
            "Важно: цикл может существовать вне достижимой части списка — двигайся строго от головы.",
        ],
        "tests": [
            T("sample", "5\n1 2 3 4 2\n", "Yes", sample=True),
            T("no_cycle", "5\n1 2 -1 4 2\n", "No"),
            T("cycle_unreachable", "4\n-1 2 1 3\n", "No"),
            T("self_loop", "2\n1 1\n", "Yes"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); nxt = list(map(int, data[1:1+n]))
slow = fast = 0
found = False
while True:
    slow = nxt[slow]
    if slow == -1: break
    fast = nxt[fast]
    if fast == -1: break
    fast = nxt[fast]
    if fast == -1: break
    if slow == fast:
        found = True; break
print('Yes' if found else 'No')
""",
    },
]
