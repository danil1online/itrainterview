from app.seed.bank_common import T

TASKS = [
    {
        "slug": "two-sum-ii",
        "title": "Сумма двух в отсортированном",
        "pattern": "two_pointers",
        "level": "junior",
        "legend": """В архиве курьера сохранился отсортированный по возрастанию список цен на детали. Нужно найти ДВЕ различные позиции с суммой ровно `target`.

Формат ввода
Первая строка — n (2 <= n <= 10^5). Вторая — n целых чисел по возрастанию (-10^9 <= a[i] <= 10^9). Третья — target. Решение гарантированно существует и единственно.

Формат вывода
Два числа — позиции пары (нумерация с 1, i < j) через пробел.""",
        "hints": [
            "Массив отсортирован — перебор всех пар не нужен.",
            "Один указатель в начало, другой в конец; сравнивай сумму с target.",
            "Сумма меньше target — двигай левый вправо, иначе правый влево.",
        ],
        "tests": [
            T("sample", "4\n2 7 11 15\n9\n", "1 2", sample=True),
            T("negatives", "3\n-1 0 4\n3\n", "1 3"),
            T("large_sum", "2\n1000000000 2000000000\n3000000000\n", "1 2"),
            T("middle_pair", "5\n1 2 4 8 16\n20\n", "3 5"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); a = list(map(int, data[1:1+n])); target = int(data[1+n])
l, r = 0, n - 1
while l < r:
    s = a[l] + a[r]
    if s == target:
        print(l + 1, r + 1); break
    if s < target: l += 1
    else: r -= 1
""",
    },
    {
        "slug": "container-water",
        "title": "Контейнер с наибольшей водой",
        "pattern": "two_pointers",
        "level": "middle",
        "legend": """Вдоль причала стоят вертикальные стенки разной высоты. Выбери две стенки так, чтобы «ванна» между ними вмещала максимум воды (шаг между соседними стенками — 1).

Формат ввода
Первая строка — n (2 <= n <= 10^5). Вторая — n высот h[i] (0 <= h[i] <= 10^9).

Формат вывода
Максимальное количество воды.""",
        "hints": [
            "Объём между i и j = min(h[i], h[j]) * (j - i).",
            "Двигай указатель у более низкой стенки: сдвиг высокой не увеличит объём.",
        ],
        "tests": [
            T("sample", "9\n1 8 6 2 5 4 8 3 7\n", "49", sample=True),
            T("two", "2\n1 1\n", "1"),
            T("descending", "4\n4 3 2 1\n", "4"),
            T("middle_peak", "5\n1 2 4 3 5\n", "8"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); h = list(map(int, data[1:1+n]))
l, r, best = 0, n - 1, 0
while l < r:
    best = max(best, min(h[l], h[r]) * (r - l))
    if h[l] < h[r]: l += 1
    else: r -= 1
print(best)
""",
    },
    {
        "slug": "remove-duplicates-sorted",
        "title": "Удаление дубликатов на месте",
        "pattern": "two_pointers",
        "level": "junior",
        "legend": """Датчик выдаёт отсортированный по возрастанию поток значений с повторами. Оставь каждое значение ровно один раз.

Формат ввода
Первая строка — n (1 <= n <= 10^5). Вторая — n чисел по возрастанию.

Формат вывода
Первая строка — количество уникальных k. Вторая — k значений через пробел в исходном порядке.""",
        "hints": [
            "Дубликаты в отсортированном массиве стоят рядом.",
            "Медленный указатель — конец результата, быстрый идёт вперёд.",
        ],
        "tests": [
            T("sample", "8\n0 0 1 1 2 3 3 5\n", "5\n0 1 2 3 5", sample=True),
            T("single", "1\n7\n", "1\n7"),
            T("negatives", "5\n-2 -2 -1 0 0\n", "3\n-2 -1 0"),
            T("all_same", "4\n9 9 9 9\n", "1\n9"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); a = list(map(int, data[1:1+n]))
res = []
for x in a:
    if not res or res[-1] != x:
        res.append(x)
print(len(res))
print(' '.join(map(str, res)))
""",
    },
    {
        "slug": "longest-unique-substring",
        "title": "Самая длинная подстрока без повторов",
        "pattern": "sliding_window",
        "level": "middle",
        "legend": """Лицензионный ключ — строка из строчных латинских букв. Найди длину самого длинного фрагмента, где ни одна буква не встречается дважды.

Формат ввода
Одна строка длины от 1 до 10^5 (строчные латинские буквы).

Формат вывода
Максимальная длина подстроки без повторяющихся символов.""",
        "hints": [
            "Перебор всех подстрок — O(N^2) или хуже. Нужно O(N).",
            "Окно [l..r] с уникальными символами; при повторе сдвигай l.",
            "Храни индекс последнего вхождения символа в словаре.",
        ],
        "tests": [
            T("sample", "abcabcbb\n", "3", sample=True),
            T("all_same", "bbbbb\n", "1"),
            T("mixed", "pwwkew\n", "3"),
            T("unique_all", "abcdef\n", "6"),
        ],
        "reference_solution": """import sys

s = sys.stdin.read().strip()
last = {}; l = 0; best = 0
for r, c in enumerate(s):
    if c in last and last[c] >= l:
        l = last[c] + 1
    last[c] = r
    best = max(best, r - l + 1)
print(best)
""",
    },
    {
        "slug": "max-sum-k-subarray",
        "title": "Максимальная сумма окна размера K",
        "pattern": "sliding_window",
        "level": "junior",
        "legend": """Сенсор каждую минуту пишет температуру. Найди интервал из ровно k подряд идущих минут с максимальной суммарной температурой.

Формат ввода
Первая строка — n и k (1 <= k <= n <= 10^5). Вторая — n чисел (-10^4 <= a[i] <= 10^4).

Формат вывода
Максимальная сумма окна длины k.""",
        "hints": [
            "Не пересчитывай сумму каждого окна с нуля.",
            "Сумма следующего окна = прежняя - вышедший + вошедший.",
        ],
        "tests": [
            T("sample", "5 2\n2 1 5 1 3\n", "6", sample=True),
            T("negatives", "5 3\n-1 -2 -3 -4 -5\n", "-6"),
            T("k_equals_n", "4 4\n1 2 3 4\n", "10"),
            T("k_one", "3 1\n-5 7 -2\n", "7"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n, k = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))
cur = sum(a[:k]); best = cur
for i in range(k, n):
    cur += a[i] - a[i-k]
    best = max(best, cur)
print(best)
""",
    },
    {
        "slug": "equilibrium-index",
        "title": "Индекс равновесия",
        "pattern": "prefix_sum",
        "level": "junior",
        "legend": """Балансир нужно подвесить так, чтобы сумма масс слева от точки подвеса равнялась сумме справа. Найди самую левую подходящую позицию.

Формат ввода
Первая строка — n (1 <= n <= 10^5). Вторая — n чисел (-10^4 <= a[i] <= 10^4).

Формат вывода
Минимальная позиция (нумерация с 1), сумма строго левее и строго правее которой равны; иначе -1.""",
        "hints": [
            "Суммы слева и справа выражаются через общую сумму массива.",
            "Иди по массиву с prefix_sum; справа = total - prefix_sum - a[i].",
        ],
        "tests": [
            T("sample", "5\n1 3 5 2 2\n", "3", sample=True),
            T("single", "1\n5\n", "1"),
            T("none", "3\n1 2 3\n", "-1"),
            T("negatives", "4\n-1 3 -2 2\n", "3"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n = int(data[0]); a = list(map(int, data[1:1+n]))
total = sum(a); left = 0
for i, x in enumerate(a):
    if left == total - left - x:
        print(i + 1); break
    left += x
else:
    print(-1)
""",
    },
    {
        "slug": "subarray-sum-equals-k",
        "title": "Количество подмассивов с суммой K",
        "pattern": "prefix_sum",
        "level": "middle",
        "legend": """Кладовщик фиксирует приход и расход деталей (отрицательные — списания). Посчитай число непрерывных периодов с суммарным балансом ровно k.

Формат ввода
Первая строка — n и k (1 <= n <= 10^5, |k| <= 10^9). Вторая — n чисел (-10^4 <= a[i] <= 10^4).

Формат вывода
Количество подмассивов с суммой ровно k.""",
        "hints": [
            "Сумма подмассива (i..j] = pref[j] - pref[i]; нужны пары с разностью k.",
            "Храни частоты уже встреченных префиксных сумм в словаре.",
            "Для текущей суммы s добавь count[s-k], затем count[s] += 1; начни с pref=0.",
        ],
        "tests": [
            T("sample", "3 2\n1 1 1\n", "2", sample=True),
            T("negatives", "5 -1\n-1 0 1 -1 0\n", "6"),
            T("zeros", "4 0\n0 0 0 0\n", "10"),
            T("none", "3 0\n1 2 3\n", "0"),
        ],
        "reference_solution": """import sys
from collections import Counter

data = sys.stdin.read().split()
n, k = int(data[0]), int(data[1])
a = list(map(int, data[2:2+n]))
cnt = Counter({0: 1}); s = 0; ans = 0
for x in a:
    s += x
    ans += cnt[s - k]
    cnt[s] += 1
print(ans)
""",
    },
]
