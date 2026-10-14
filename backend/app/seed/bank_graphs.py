from app.seed.bank_common import T

TASKS = [
    {
        "slug": "number-of-islands",
        "title": "Количество островов",
        "pattern": "dfs",
        "level": "middle",
        "legend": """Снимок архипелага — матрица: 1 — суша, 0 — вода. Остров — связная область единиц (соседство по сторонам света, не по диагонали). Посчитай число островов.

Формат ввода
Первая строка — n и m (1 <= n, m <= 300). Далее n строк по m чисел (0 или 1) через пробел.

Формат вывода
Количество островов.""",
        "hints": [
            "Обход связной области — DFS или BFS.",
            "Крась посещённые клетки (1 -> 0), чтобы не считать остров дважды.",
            "При n,m=300 рекурсия может исчерпать стек — используй явный стек/очередь.",
        ],
        "tests": [
            T("sample", "4 5\n1 1 0 0 0\n0 1 0 0 1\n0 0 0 1 1\n0 0 0 0 0\n", "2", sample=True),
            T("all_water", "2 2\n0 0\n0 0\n", "0"),
            T("all_land", "2 3\n1 1 1\n1 1 1\n", "1"),
            T("single_cell", "1 1\n1\n", "1"),
        ],
        "reference_solution": """import sys

data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
g = [[int(v) for v in data[2+i*m:2+(i+1)*m]] for i in range(n)]
count = 0
for i in range(n):
    for j in range(m):
        if g[i][j] == 1:
            count += 1
            stack = [(i, j)]; g[i][j] = 0
            while stack:
                x, y = stack.pop()
                for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
                    nx, ny = x+dx, y+dy
                    if 0 <= nx < n and 0 <= ny < m and g[nx][ny] == 1:
                        g[nx][ny] = 0; stack.append((nx, ny))
print(count)
""",
    },
    {
        "slug": "check-bst-preorder",
        "title": "Проверка BST по префиксному обходу",
        "pattern": "dfs",
        "level": "middle",
        "legend": """Дерево передали списком в прямом обходе (pre-order): корень, левое поддерево, правое поддерево; каждая пустая ветвь кодируется числом NUL = -1000000. Можно ли построить из последовательности корректное BST (строгое неравенство: левее меньше, правее больше)?

Формат ввода
Первая строка — n (1 <= n <= 10^5). Вторая — n чисел — полный pre-order с явными NUL.

Формат вывода
Yes или No.""",
        "hints": [
            "Спускайся по pre-order с диапазонами допустимых значений (lo, hi), как при валидации BST.",
            "Прочитал значение v — оно должно попасть в (lo, hi); левое поддерево ищи в (lo, v), правое в (v, hi).",
            "В конце должны быть прочитаны ровно все n токенов и ни одного нарушения диапазона.",
        ],
        "tests": [
            T("sample", "7\n2 1 -1000000 -1000000 3 -1000000 -1000000\n", "Yes", sample=True),
            T("invalid_bst", "7\n5 6 -1000000 -1000000 4 -1000000 -1000000\n", "No"),
            T("incomplete", "3\n2 1 -1000000\n", "No"),
            T("empty_tree", "1\n-1000000\n", "Yes"),
        ],
        "reference_solution": """import sys

NUL = -1000000
data = sys.stdin.read().split()
n = int(data[0])
seq = list(map(int, data[1:1+n]))
state = {"pos": 0, "ok": True}

def parse(lo, hi):
    if not state["ok"] or state["pos"] >= n:
        state["ok"] = False
        return
    v = seq[state["pos"]]; state["pos"] += 1
    if v == NUL:
        return
    if not (lo < v < hi):
        state["ok"] = False
        return
    parse(lo, v)
    parse(v, hi)

sys.setrecursionlimit(300000)
parse(-10**18, 10**18)
print('Yes' if state["ok"] and state["pos"] == n else 'No')
""",
    },
    {
        "slug": "rotting-oranges",
        "title": "Гниющие апельсины",
        "pattern": "bfs",
        "level": "middle",
        "legend": """На складе ящики: 2 — гнилой апельсин, 1 — свежий, 0 — пусто. Каждую минуту гнилые заражают свежие по сторонам света. Через сколько минут сгниют все?

Формат ввода
Первая строка — n и m (1 <= n, m <= 100). Далее n строк по m чисел (0, 1 или 2) через пробел.

Формат вывода
Минимум минут; -1 если что-то не сгниёт никогда; 0 если свежих изначально нет.""",
        "hints": [
            "Многоисточниковый BFS: старт — все гнилые ячейки одновременно.",
            "Считай минуты по «слоям» очереди.",
            "В конце проверь, не осталось ли свежих ячеек.",
        ],
        "tests": [
            T("sample", "3 3\n2 1 1\n1 1 0\n0 1 1\n", "4", sample=True),
            T("no_fresh", "2 2\n2 0\n0 2\n", "0"),
            T("unreachable", "2 2\n1 1\n1 0\n", "-1"),
            T("empty_all", "2 2\n0 0\n0 0\n", "0"),
        ],
        "reference_solution": """import sys
from collections import deque

data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
g = [[int(v) for v in data[2+i*m:2+(i+1)*m]] for i in range(n)]
q = deque(); fresh = 0
for i in range(n):
    for j in range(m):
        if g[i][j] == 2: q.append((i, j))
        elif g[i][j] == 1: fresh += 1
minutes = 0
while q and fresh > 0:
    minutes += 1
    for _ in range(len(q)):
        x, y = q.popleft()
        for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
            nx, ny = x+dx, y+dy
            if 0 <= nx < n and 0 <= ny < m and g[nx][ny] == 1:
                g[nx][ny] = 2; fresh -= 1; q.append((nx, ny))
print(minutes if fresh == 0 else -1)
""",
    },
    {
        "slug": "maze-shortest-path",
        "title": "Кратчайший путь в лабиринте",
        "pattern": "bfs",
        "level": "junior",
        "legend": """Робот ходит на 1 клетку вверх/вниз/влево/вправо. Клетки: S — старт, E — выход, . — свободно, # — стена. Найди минимальное число шагов от S до E.

Формат ввода
Первая строка — n и m (1 <= n, m <= 200). Далее n строк по m символов через пробел. Ровно один S и один E.

Формат вывода
Минимальное число шагов или -1.""",
        "hints": [
            "Кратчайший путь в невзвешенном графе — BFS.",
            "Храни расстояние до посещённых клеток, чтобы не заходить дважды.",
        ],
        "tests": [
            T("sample", "3 4\nS . . .\n# # # .\n. . . E\n", "5", sample=True),
            T("blocked", "2 3\nS # E\n. # .\n", "-1"),
            T("straight", "1 3\nS . E\n", "2"),
            T("adjacent", "1 2\nS E\n", "1"),
        ],
        "reference_solution": """import sys
from collections import deque

data = sys.stdin.read().split()
n, m = int(data[0]), int(data[1])
g = [data[2+i*m:2+(i+1)*m] for i in range(n)]
start = finish = None
for i in range(n):
    for j in range(m):
        if g[i][j] == 'S': start = (i, j)
        if g[i][j] == 'E': finish = (i, j)
dist = {start: 0}
q = deque([start])
while q:
    x, y = q.popleft()
    for dx, dy in ((1,0),(-1,0),(0,1),(0,-1)):
        nx, ny = x+dx, y+dy
        if 0 <= nx < n and 0 <= ny < m and g[nx][ny] != '#' and (nx, ny) not in dist:
            dist[(nx, ny)] = dist[(x, y)] + 1
            q.append((nx, ny))
print(dist.get(finish, -1))
""",
    },
]
