// Теория, часть 2: карточки паттернов (ДП, жадные, куча, trie, математика, связные списки).
import type { TheoryPattern } from './data1';

export const THEORY_PART2: TheoryPattern[] = [
  {
    id: 'dp',
    name: 'Динамическое программирование',
    idea:
      'Динамическое программирование (ДП) решает задачу, агрегируя ответы перекрывающихся подзадач: сначала вычисляются маленькие подзадачи, на их основе — большие, через рекуррентное соотношение («переход»). Экономия принципиальна: экспоненциальный перебор превращается в полиномиальный (например O(n²) или O(n·W)). Три шага построения: (1) состояние — что кодируют индексы таблицы dp; (2) переход — как состояние выражается через более простые; (3) базовый случай и порядок вычисления. Сложность ДП = число состояний × стоимость одного перехода.',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Наивная рекурсия пересчитывает одно и то же по многу раз: вычисление чисел Фибоначчи «в лоб» делает ~2ⁿ вызовов (для n = 50 это квадриллионы операций). Причина — перекрывающиеся подзадачи: fib(48) и fib(47) независимо вычисляют fib(47), fib(46) и т.д.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Запоминаем ответы подзадач: сверху вниз (мемоизация — кэш при рекурсии) или снизу вверх (таблица dp, заполняем по порядку от базовых случаев). Каждое состояние вычисляется ровно один раз → время = число состояний × переход. Память часто можно сжать до одной строки или пары переменных, если переход зависит только от последних состояний.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Линейное ДП: лестница (climbing stairs), разбойник-грабитель, максимальная сумма без соседних элементов.\n' +
          '• Ранец и подмножества (по сумме/весу), монеты (число способов).\n' +
          '• На двух последовательностях: наибольшая возрастающая подпоследовательность (LIS), общая подпоследовательность (LCS), расстояние редактирования.\n' +
          '• ДП на деревьях и по маске (маленькие n, обход подмножеств).',
      },
    ],
    examples: [
      {
        title: 'Наибольшая возрастающая подпоследовательность, O(n log n)',
        statement:
          'Дан массив. Найти длину наибольшей строго возрастающей подпоследовательности (не обязательно непрерывной) за O(n log n).',
        solutions: [
          {
            lang: 'Python',
            code: `# tails[k] — минимальное «хвостовое» значение возрастающей подпоследовательности длины k+1
from bisect import bisect_left

def lis_length(a):
    tails = []
    for x in a:
        i = bisect_left(tails, x)   # позиция, где x может улучшить хвост
        if i == len(tails):
            tails.append(x)          # удлинили самую длинную подпоследовательность
        else:
            tails[i] = x             # нашли меньший хвост для длины i+1
    return len(tails)
# [10,9,2,5,3,7,101,18] -> 4 (2,3,7,18)`,
          },
          {
            lang: 'Java',
            code: `// tails[i] — минимальный хвост возрастающей подпоследовательности длины i+1
int lengthOfLIS(int[] a) {
    int[] tails = new int[a.length];
    int size = 0;                   // текущая длина LIS
    for (int x : a) {
        // бинарный поиск первого tails[i] >= x
        int lo = 0, hi = size;
        while (lo < hi) {
            int mid = (lo + hi) / 2;
            if (tails[mid] < x) lo = mid + 1;
            else hi = mid;
        }
        tails[lo] = x;               // заменяем хвост (или удлиняем)
        if (lo == size) size++;
    }
    return size;
}`,
          },
          {
            lang: 'C++',
            code: `// tails[i] — минимальный «хвост» возрастающей подпоследовательности длины i+1
int lengthOfLIS(vector<int>& a) {
    vector<int> tails;
    for (int x : a) {
        auto it = lower_bound(tails.begin(), tails.end(), x); // первый >= x
        if (it == tails.end())
            tails.push_back(x);       // удлинили самую длинную подпоследовательность
        else
            *it = x;                  // нашли меньший хвост для этой длины
    }
    return (int)tails.size();
}
// [10,9,2,5,3,7,101,18] -> 4 (2,3,7,18)`,
          },
          {
            lang: 'JavaScript',
            code: `// tails[k] — минимальный «хвост» возрастающей подпоследовательности длины k+1
function lisLength(a) {
  const tails = [];
  for (const x of a) {
    let lo = 0, hi = tails.length;      // бинарный поиск первого >= x
    while (lo < hi) {
      const mid = (lo + hi) >> 1;
      if (tails[mid] < x) lo = mid + 1;
      else hi = mid;
    }
    if (lo === tails.length) tails.push(x); // удлинили подпоследовательность
    else tails[lo] = x;                     // улучшили хвост длины lo+1
  }
  return tails.length;
}
// [10,9,2,5,3,7,101,18] -> 4 (2,3,7,18)`,
          },
        ],
        complexity: 'O(n log n) время, O(n) память. (Классический ДП — O(n²).)',
      },
      {
        title: 'Максимальное произведение подмассива',
        statement:
          'Дан массив целых (могут быть отрицательные и нули). Найти максимальное произведение непрерывного подмассива.',
        solutions: [
          {
            lang: 'Python',
            code: `# Отрицательное число может превратить минимальный «хвост» в максимальный —
# поэтому ведём и max, и min одновременно
def max_product(a):
    best = cur_max = cur_min = a[0]
    for x in a[1:]:
        if x < 0:                   # знак меняется — max/min меняются местами
            cur_max, cur_min = cur_min, cur_max
        cur_max = max(x, cur_max * x)   # либо начать заново, либо продолжить
        cur_min = min(x, cur_min * x)
        best = max(best, cur_max)
    return best
# [2,3,-2,4] -> 6 (2*3), [-2,0,-1] -> 0`,
          },
          {
            lang: 'Java',
            code: `// Параллельно следим за максимумом и минимумом — из-за отрицательных чисел
int maxProduct(int[] a) {
    int best = a[0], curMax = a[0], curMin = a[0];
    for (int i = 1; i < a.length; i++) {
        int x = a[i];
        if (x < 0) {                // отрицательное: max <-> min
            int t = curMax; curMax = curMin; curMin = t;
        }
        curMax = Math.max(x, curMax * x);   // продолжить или начать заново
        curMin = Math.min(x, curMin * x);
        best = Math.max(best, curMax);
    }
    return best;
}`,
          },
          {
            lang: 'C++',
            code: `// Отрицательное число превращает минимум в максимум — ведём оба
int maxProduct(vector<int>& a) {
    int best = a[0], curMax = a[0], curMin = a[0];
    for (size_t i = 1; i < a.size(); i++) {
        int x = a[i];
        if (x < 0) swap(curMax, curMin);     // знак меняется — max/min местами
        curMax = max(x, curMax * x);         // начать заново или продолжить
        curMin = min(x, curMin * x);
        best = max(best, curMax);
    }
    return best;
}
// [2,3,-2,4] -> 6 (2*3), [-2,0,-1] -> 0`,
          },
          {
            lang: 'JavaScript',
            code: `// Отрицательное число превращает минимум в максимум — ведём оба
function maxProduct(a) {
  let best = a[0], curMax = a[0], curMin = a[0];
  for (let i = 1; i < a.length; i++) {
    const x = a[i];
    if (x < 0) [curMax, curMin] = [curMin, curMax]; // знак меняется — меняем местами
    curMax = Math.max(x, curMax * x);   // начать заново или продолжить
    curMin = Math.min(x, curMin * x);
    best = Math.max(best, curMax);
  }
  return best;
}
// [2,3,-2,4] -> 6 (2*3), [-2,0,-1] -> 0`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Dynamic Programming', url: 'https://www.geeksforgeeks.org/dynamic-programming/' },
      { label: 'LeetCode — задачи с тегом Dynamic Programming', url: 'https://leetcode.com/tag/dynamic-programming/' },
    ],
  },
  {
    id: 'greedy',
    name: 'Жадные алгоритмы',
    idea:
      'Жадный алгоритм на каждом шаге делает локально лучший выбор и «фиксирует» его, не возвращаясь. Работает, если доказано, что жадный выбор приводит к глобальному оптимуму — обычно через «аргумент замены»: любое оптимальное решение можно перестроить так, чтобы оно содержало жадный выбор, не став хуже. После сортировки за O(n log n) сам жадный проход — O(n). Обязательна проверка контрпримером: для произвольных систем номиналов монет жадная раздача сдачи ошибается (например, номиналы 1, 3, 4 и сумма 6: жадно 4+1+1=3 монеты, оптимум 3+3=2).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Полный перебор всех последовательностей решений экспоненциален: например, «максимум непересекающихся интервалов» прямым перебором — это 2ⁿ подмножеств; уже при n = 40 это нереально долго. ДП для таких задач часто избыточно — достаточно одного умного прохода.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Сортируем объекты по «правильному» ключу (интервалы — по времени окончания, предметы — по удельной ценности) и один раз проходим, беря каждый совместимый элемент. Итог — O(n log n) из-за сортировки, сам проход линеен. Более сложные варианты используют кучу («лучший среди активных») или два прохода туда-обратно.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Выбор максимума непересекающихся событий/интервалов (сортировка по концу).\n' +
          '• Заправка на кольцевой дороге, минимальное число прыжков до конца массива.\n' +
          '• Размен монетами — только для канонических систем номиналов (иначе нужен ДП)!\n' +
          '• Кодирование Хаффмана, планирование с дедлайнами, интервальные расписания.',
      },
    ],
    examples: [
      {
        title: 'Заправка на кольцевой дороге',
        statement:
          'n станций в кольце. На станции i можно заправить gas[i], чтобы проехать к следующей station[i] нужно fuel[i]. С какой станции начать круг, чтобы успеть весь? Гарантирован ровно один ответ.',
        solutions: [
          {
            lang: 'Python',
            code: `# Если из старта s не хватает топлива до t, то НЕЛЬЗЯ стартовать ни с одной
# станции между s и t (у них меньше накопленного) — пропускаем их целиком
def can_complete(gas, cost):
    n = len(gas)
    total = 0
    tank = 0
    start = 0
    for i in range(n):
        diff = gas[i] - cost[i]
        total += diff
        tank += diff
        if tank < 0:                # из start не доехать до i+1
            start = i + 1           # ...и ни из одной станции между ними
            tank = 0
    return start if total >= 0 else -1`,
          },
          {
            lang: 'Java',
            code: `// Жадно «отбрасываем» невозможные стартовые позиции одним проходом
int canCompleteCircuit(int[] gas, int[] cost) {
    int total = 0, tank = 0, start = 0;
    for (int i = 0; i < gas.length; i++) {
        int diff = gas[i] - cost[i];
        total += diff;
        tank += diff;
        if (tank < 0) {             // старт не дальше, чем i+1
            start = i + 1;
            tank = 0;
        }
    }
    return total >= 0 ? start : -1;
}`,
          },
          {
            lang: 'C++',
            code: `// Если бак опустел к станции i — ни один старт между ними тоже не годится
int canCompleteCircuit(vector<int>& gas, vector<int>& cost) {
    int total = 0, tank = 0, start = 0;
    for (int i = 0; i < (int)gas.size(); i++) {
        int diff = gas[i] - cost[i];
        total += diff;              // общий баланс по всему кольцу
        tank += diff;               // баланс от текущего старта
        if (tank < 0) {             // из start не доехать до i+1
            start = i + 1;          // и ни с одной станции между ними
            tank = 0;
        }
    }
    return total >= 0 ? start : -1;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Если бак опустел к станции i — старт раньше (i+1) невозможен, сдвигаем его
function canCompleteCircuit(gas, cost) {
  let total = 0, tank = 0, start = 0;
  for (let i = 0; i < gas.length; i++) {
    const diff = gas[i] - cost[i];
    total += diff;                  // баланс по всему кольцу
    tank += diff;                   // баланс от текущего старта
    if (tank < 0) {                 // из start не доехать до i+1
      start = i + 1;                // и ни с одной станции между ними
      tank = 0;
    }
  }
  return total >= 0 ? start : -1;
}`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
      {
        title: 'Минимальное число прыжков до конца',
        statement:
          'Дан массив, где a[i] — максимальная длина прыжка из позиции i. Найти минимальное число прыжков от позиции 0 до последней (гарантированно достижима).',
        solutions: [
          {
            lang: 'Python',
            code: `# BFS-подобно: каждый «прыжок» — уровень; держим дальность текущего уровня
def min_jumps(a):
    jumps = 0
    cur_end = 0                    # правая граница, достижимая за jumps прыжков
    farthest = 0                   # максимальная дальность от всех посещённых
    for i in range(len(a) - 1):
        farthest = max(farthest, i + a[i])
        if i == cur_end:           # исчерпали текущий уровень — прыгаем
            jumps += 1
            cur_end = farthest
    return jumps
# [2,3,1,1,4] -> 2 (0->1->4)`,
          },
          {
            lang: 'Java',
            code: `// Каждый «уровень» BFS = один прыжок; граница уровня — curEnd
int jump(int[] a) {
    int jumps = 0, curEnd = 0, farthest = 0;
    for (int i = 0; i < a.length - 1; i++) {
        farthest = Math.max(farthest, i + a[i]);
        if (i == curEnd) {         // дошли до края текущего уровня
            jumps++;
            curEnd = farthest;     // следующий уровень — всё, что видно дальше
        }
    }
    return jumps;
}`,
          },
          {
            lang: 'C++',
            code: `// Каждый «прыжок» — уровень: держим границу curEnd и дальность farthest
int jump(vector<int>& a) {
    int jumps = 0, curEnd = 0, farthest = 0;
    for (int i = 0; i < (int)a.size() - 1; i++) {
        farthest = max(farthest, i + a[i]);   // как далеко видно из позиции i
        if (i == curEnd) {          // исчерпан текущий уровень — прыгаем
            jumps++;
            curEnd = farthest;      // следующий уровень — вся дальность
        }
    }
    return jumps;
}
// [2,3,1,1,4] -> 2 (0->1->4)`,
          },
          {
            lang: 'JavaScript',
            code: `// Каждый прыжок = «уровень»: граница уровня curEnd, дальность farthest
function minJumps(a) {
  let jumps = 0, curEnd = 0, farthest = 0;
  for (let i = 0; i < a.length - 1; i++) {
    farthest = Math.max(farthest, i + a[i]); // как далеко видно из позиции i
    if (i === curEnd) {             // исчерпан текущий уровень — прыгаем
      jumps++;
      curEnd = farthest;            // следующий уровень — вся дальность
    }
  }
  return jumps;
}
// [2,3,1,1,4] -> 2 (0->1->4)`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Greedy Algorithms', url: 'https://www.geeksforgeeks.org/greedy-algorithms/' },
      { label: 'LeetCode — задачи с тегом Greedy', url: 'https://leetcode.com/tag/greedy/' },
    ],
  },
  {
    id: 'heap',
    name: 'Куча / Priority Queue',
    idea:
      'Двоичная куча (priority queue) — почти полное дерево, записанное в массив, с свойством кучи: родитель «лучше» детей, поэтому минимум (min-куча) или максимум (max-куча) всегда лежит на вершине и доступен за O(1). Добавление и извлечение — O(log n): элемент «всплывает» или «просеивается» по пути длиной log n. Построение кучи из готового массива — O(n). Это структура для задач, где экстремум нужно извлекать многократно: топ-K, слияние k потоков, приоритеты, жадные алгоритмы с «лучшим среди активных».',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Искать минимум линейным сканом при каждом извлечении — O(n) на операцию, O(n·k) на k извлечений. Полная сортировка тоже не спасает динамические данные: после каждого добавления массив пришлось бы пересортировывать заново.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Держим кучу: push — ставим элемент в конец массива и «всплываем» его вверх, меняя местами с родителем (O(log n)); pop — снимаем вершину, ставим на её место последний элемент и «просеиваем» вниз к меньшему из детей (O(log n)). k извлечений стоят O(k log n), а данные могут прилетать между операциями без пересортировки всего множества.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Топ-K элементов по частоте/значению (K наиболее часто встречающихся).\n' +
          '• Слияние k отсортированных потоков/списков за O(N log k).\n' +
          '• Скользящая медиана / медиана потока — две кучи (max-нижняя + min-верхняя).\n' +
          '• Алгоритм Дейкстры, планирование задач по приоритету, очереди обслуживания.',
      },
    ],
    examples: [
      {
        title: 'Очередь скорой помощи',
        statement:
          'Операции: "add <priority> <id>" (пациент с приоритетом, чем больше — тем срочнее) и "serve" (вызвать самого срочного; при равенстве — с меньшим id). Вывести id для каждого serve.',
        solutions: [
          {
            lang: 'Python',
            code: `# Min-heap на кортежах (-priority, id): максимум приоритета, минимум id
import heapq

def process(ops):
    heap = []                      # (-priority, id)
    out = []
    for op in ops:
        if op[0] == 'add':
            _, p, i = op
            heapq.heappush(heap, (-int(p), int(i)))   # O(log n)
        else:
            neg_p, i = heapq.heappop(heap)            # лучший на вершине
            out.append(str(i))
    return "\\n".join(out)`,
          },
          {
            lang: 'Java',
            code: `// PriorityQueue с comparator: сначала больший приоритет, затем меньший id
List<String> process(List<String[]> ops) {
    PriorityQueue<int[]> pq = new PriorityQueue<>(
        (x, y) -> x[0] != y[0] ? y[0] - x[0] : x[1] - y[1]); // max priority, min id
    List<String> out = new ArrayList<>();
    for (String[] op : ops) {
        if (op[0].equals("add")) {
            pq.offer(new int[]{Integer.parseInt(op[1]), Integer.parseInt(op[2])});
        } else {
            out.add(String.valueOf(pq.poll()[1]));   // вершина = самый срочный
        }
    }
    return out;
}`,
          },
          {
            lang: 'C++',
            code: `// Max-heap по приоритету; при равенстве — меньший id (пары сравниваются лексикографически)
vector<string> process(vector<vector<string>>& ops) {
    priority_queue<pair<int,int>> pq;   // (priority, -id): max приоритет -> min id
    vector<string> out;
    for (auto& op : ops) {
        if (op[0] == "add") {
            int p = stoi(op[1]), i = stoi(op[2]);
            pq.push({p, -i});           // O(log n), вершина — лучший
        } else {
            out.push_back(to_string(-pq.top().second)); // снимаем самого срочного
            pq.pop();
        }
    }
    return out;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// В JS нет встроенной кучи — мини-реализация бинарной min-кучи с компаратором
class MinHeap {
  constructor(cmp) { this.a = []; this.cmp = cmp; }
  push(x) {                            // добавить и «всплывать» вверх
    const a = this.a; a.push(x);
    let i = a.length - 1;
    while (i > 0) {
      const p = (i - 1) >> 1;          // индекс родителя
      if (this.cmp(a[i], a[p]) < 0) { [a[i], a[p]] = [a[p], a[i]]; i = p; }
      else break;
    }
  }
  pop() {                              // снять вершину, последний — просеять вниз
    const a = this.a, top = a[0], last = a.pop();
    if (a.length) {
      a[0] = last; let i = 0;
      for (;;) {
        const l = 2*i + 1, r = 2*i + 2;
        let m = i;
        if (l < a.length && this.cmp(a[l], a[m]) < 0) m = l;
        if (r < a.length && this.cmp(a[r], a[m]) < 0) m = r;
        if (m === i) break;
        [a[i], a[m]] = [a[m], a[i]]; i = m;
      }
    }
    return top;
  }
}

function process(ops) {
  // ключ (-priority, id): больший приоритет срочнее, при равенстве — меньший id
  const heap = new MinHeap((x, y) => x[0] !== y[0] ? x[0] - y[0] : x[1] - y[1]);
  const out = [];
  for (const op of ops) {
    if (op[0] === 'add') heap.push([-Number(op[1]), Number(op[2])]); // O(log n)
    else out.push(String(heap.pop()[1]));   // вершина — самый срочный
  }
  return out.join('\\n');
}`,
          },
        ],
        complexity: 'O(q log n) на все операции, O(n) память.',
      },
      {
        title: 'K пар с наименьшей суммой',
        statement:
          'Даны два отсортированных по возрастанию массива A и B. Найти k пар (a, b), a из A, b из B, с наименьшими суммами a + b.',
        solutions: [
          {
            lang: 'Python',
            code: `# Куча позиций (i, j): стартуем от (0,0); из (i,j) возможны только (i+1,j) и (i,j+1)
import heapq

def k_smallest_pairs(a, b, k):
    seen = {(0, 0)}
    heap = [(a[0] + b[0], 0, 0)]   # (сумма, i, j)
    res = []
    while heap and len(res) < k:
        s, i, j = heapq.heappop(heap)
        res.append((a[i], b[j]))
        for ni, nj in ((i + 1, j), (i, j + 1)):   # расширяем «фронт»
            if ni < len(a) and nj < len(b) and (ni, nj) not in seen:
                seen.add((ni, nj))
                heapq.heappush(heap, (a[ni] + b[nj], ni, nj))
    return res`,
          },
          {
            lang: 'Java',
            code: `// Куча индексов; из каждой позиции — только два новых соседа (многоугольник)
List<int[]> kSmallestPairs(int[] a, int[] b, int k) {
    Set<Long> seen = new HashSet<>();
    PriorityQueue<long[]> pq = new PriorityQueue<>(Comparator.comparingLong(x -> x[0]));
    pq.offer(new long[]{a[0] + b[0], 0, 0});
    List<int[]> res = new ArrayList<>();
    while (!pq.isEmpty() && res.size() < k) {
        long[] cur = pq.poll();
        int i = (int) cur[1], j = (int) cur[2];
        res.add(new int[]{a[i], b[j]});
        for (int[] d : new int[][]{{1, 0}, {0, 1}}) {   // два направления
            int ni = i + d[0], nj = j + d[1];
            if (ni < a.length && nj < b.length) {
                long key = ((long) ni << 32) | nj;
                if (seen.add(key)) {
                    pq.offer(new long[]{a[ni] + b[nj], ni, nj});
                }
            }
        }
    }
    return res;
}`,
          },
          {
            lang: 'C++',
            code: `// Куча позиций (i, j) по сумме; из (i,j) расширяем только вправо и вниз
vector<pair<int,int>> kSmallestPairs(vector<int>& a, vector<int>& b, int k) {
    using Node = tuple<long,int,int>;                  // (сумма, i, j)
    priority_queue<Node, vector<Node>, greater<Node>> pq;  // min-куча
    set<pair<int,int>> seen;
    pq.push({(long)a[0] + b[0], 0, 0});
    seen.insert({0, 0});
    vector<pair<int,int>> res;
    while (!pq.empty() && (int)res.size() < k) {
        auto [s, i, j] = pq.top(); pq.pop();
        res.push_back({a[i], b[j]});
        const int d[2][2] = {{1, 0}, {0, 1}};          // два направления «фронта»
        for (auto& dir : d) {
            int ni = i + dir[0], nj = j + dir[1];
            if (ni < (int)a.size() && nj < (int)b.size() && !seen.count({ni, nj})) {
                seen.insert({ni, nj});
                pq.push({(long)a[ni] + b[nj], ni, nj});
            }
        }
    }
    return res;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Мини-куча по сумме (подробная реализация — в примере выше)
function kSmallestPairs(a, b, k) {
  const heap = [];                                  // [сумма, i, j]
  const cmp = (x, y) => x[0] - y[0];
  const swap = (i, j) => { [heap[i], heap[j]] = [heap[j], heap[i]]; };
  const up = (i) => { while (i > 0) { const p = (i-1) >> 1;
      if (cmp(heap[i], heap[p]) < 0) { swap(i, p); i = p; } else break; } };
  const down = (i) => { for (;;) { const l = 2*i+1, r = 2*i+2; let m = i;
      if (l < heap.length && cmp(heap[l], heap[m]) < 0) m = l;
      if (r < heap.length && cmp(heap[r], heap[m]) < 0) m = r;
      if (m === i) break; swap(i, m); i = m; } };
  const push = (x) => { heap.push(x); up(heap.length - 1); };
  const pop = () => { const top = heap[0], last = heap.pop();
    if (heap.length) { heap[0] = last; down(0); } return top; };

  const seen = new Set(['0,0']);
  push([a[0] + b[0], 0, 0]);
  const res = [];
  while (heap.length && res.length < k) {
    const [, i, j] = pop();
    res.push([a[i], b[j]]);
    for (const [ni, nj] of [[i + 1, j], [i, j + 1]]) {   // расширяем «фронт»
      if (ni < a.length && nj < b.length && !seen.has(ni + ',' + nj)) {
        seen.add(ni + ',' + nj);
        push([a[ni] + b[nj], ni, nj]);
      }
    }
  }
  return res;
}`,
          },
        ],
        complexity: 'O(k log k) время, O(k) память (seen + куча).',
      },
    ],
    links: [
      { label: 'Wikipedia — Binary heap', url: 'https://en.wikipedia.org/wiki/Binary_heap' },
      { label: 'LeetCode — задачи с тегом Heap / Priority Queue', url: 'https://leetcode.com/tag/heap-priority-queue/' },
    ],
  },
  {
    id: 'trie',
    name: 'Префиксное дерево',
    idea:
      'Префиксное дерево (trie, произносится «три») хранит множество строк в виде дерева путей от корня: каждое ребро — один символ, а помеченный узел означает «здесь заканчивается слово». Вставка и поиск слова — O(L) по длине слова, независимо от размера словаря; для сравнения, в хеш-таблице поиск всех слов с данным префиксом стоил бы O(n·L). Все слова с заданным префиксом лежат в одном поддереве — отсюда автодополнение, словари, проверка орфографии и поиск по маске с бэктрекингом.',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Проверять наличие префикса, сканируя весь словарь из n строк и сравнивая первые L символов каждой, — O(n·L) на запрос. Для словаря из 10⁵ слов это слишком медленно для интерактивного автодополнения, где ответ нужен за миллисекунды.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Строим trie один раз за O(суммарной длины всех слов). Запрос начинается со спуска по символам префикса — O(L); если спуск оборвался, слов с таким префиксом нет. Дальше достаточно обойти поддерево (DFS), чтобы собрать нужные слова. Память — O(суммарная длина × алфавит) в плотной реализации, заметно меньше — при хранении переходов в словаре/хеш-таблице.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Автодополнение и «поиск по префиксу» в словаре.\n' +
          '• Словарь с wildcard-поиском (символ «.» — любая буква) через бэктрекинг.\n' +
          '• Подсчёт слов с префиксом, лексикографическая выдача без сортировки.\n' +
          '• Максимум XOR двух чисел — двоичное trie по битам.',
      },
    ],
    examples: [
      {
        title: 'Автодополнение: топ-3 предложения по префиксу',
        statement:
          'Дан словарь слов. Для каждого запроса-префикса вернуть до 3 слов из словаря, начинающихся с него (в лексикографическом порядке).',
        solutions: [
          {
            lang: 'Python',
            code: `# В узлах trie храним список слов, «заканчивающихся» в его поддереве (не более 3)
def build_trie(words):
    root = {}
    for w in sorted(words):        # сортируем — сборка по обходу даст лексикопорядок
        node = root
        for ch in w:
            node = node.setdefault(ch, {})
        node['#'] = node.get('#', []) + [w]   # слово заканчивается здесь
    return root

def suggest(root, prefix):
    node = root
    for ch in prefix:              # спускаемся по префиксу
        if ch not in node:
            return []              # нет слов с таким префиксом
        node = node[ch]
    res = []
    stack = [node]                 # DFS-сборка завершённых слов (<= 3 на узле)
    while stack and len(res) < 3:
        cur = stack.pop()
        for k, v in cur.items():
            if k == '#':
                res.extend(v[:3 - len(res)])
            else:
                stack.append(v)
    return res[:3]`,
          },
          {
            lang: 'Java',
            code: `// Узел trie; в каждом узле — до 3 слов, заканчивающихся в его поддереве
class Node {
    Map<Character, Node> next = new HashMap<>();
    List<String> ends = new ArrayList<>();   // слова, кончающиеся здесь/ниже (<=3)
}

void insert(Node root, String w) {
    Node node = root;
    for (char c : w.toCharArray()) {
        node = node.next.computeIfAbsent(c, k -> new Node());
    }
    if (node.ends.size() < 3) node.ends.add(w);   // словарь отсортирован заранее
}

List<String> suggest(Node root, String prefix) {
    Node node = root;
    for (char c : prefix.toCharArray()) {
        if (!node.next.containsKey(c)) return List.of();
        node = node.next.get(c);
    }
    // DFS-сборка до 3 слов из поддерева
    List<String> res = new ArrayList<>();
    Deque<Node> stack = new ArrayDeque<>();
    stack.push(node);
    while (!stack.isEmpty() && res.size() < 3) {
        Node cur = stack.pop();
        for (String w : cur.ends) { if (res.size() >= 3) break; res.add(w); }
        for (Node child : cur.next.values()) stack.push(child);
    }
    return res;
}`,
          },
          {
            lang: 'C++',
            code: `// Узел trie; в каждом узле — до 3 слов из его поддерева (словарь отсортирован)
struct TrieNode {
    map<char, TrieNode*> next;     // map даёт обход в лексикографическом порядке
    vector<string> ends;           // <= 3 слова, кончающихся здесь или ниже
};

void insert(TrieNode* root, const string& w) {
    TrieNode* node = root;
    for (char c : w) {
        if (!node->next.count(c)) node->next[c] = new TrieNode();
        node = node->next[c];      // спуск/создание перехода по символу
    }
    if (node->ends.size() < 3) node->ends.push_back(w);
}

vector<string> suggest(TrieNode* root, const string& prefix) {
    TrieNode* node = root;
    for (char c : prefix) {
        if (!node->next.count(c)) return {};   // нет слов с таким префиксом
        node = node->next[c];
    }
    vector<string> res;                        // DFS по поддереву, собираем <= 3
    stack<TrieNode*> st;
    st.push(node);
    while (!st.empty() && res.size() < 3) {
        TrieNode* cur = st.top(); st.pop();
        for (const string& w : cur->ends)
            if (res.size() < 3) res.push_back(w);
        vector<TrieNode*> kids;                // кладём детей в обратном порядке,
        for (auto& kv : cur->next) kids.push_back(kv.second);   // чтобы pop шёл по алфавиту
        for (auto it = kids.rbegin(); it != kids.rend(); ++it) st.push(*it);
    }
    return res;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// В узлах trie храним до 3 слов из его поддерева (словарь отсортирован заранее)
function buildTrie(words) {
  const root = {};
  for (const w of [...words].sort()) {        // лексикографический порядок
    let node = root;
    for (const ch of w) node = node[ch] ??= {};   // переход или новый узел
    (node.ends ??= []).push(w);               // слово заканчивается здесь
  }
  return root;
}

function suggest(root, prefix) {
  let node = root;
  for (const ch of prefix) {
    if (!node[ch]) return [];                 // нет слов с таким префиксом
    node = node[ch];
  }
  const res = [];                             // DFS-сборка до 3 слов
  const stack = [node];
  while (stack.length && res.length < 3) {
    const cur = stack.pop();
    for (const w of cur.ends ?? []) if (res.length < 3) res.push(w);
    for (const k of Object.keys(cur).sort().reverse())  // обход по алфавиту
      if (k !== 'ends') stack.push(cur[k]);
  }
  return res.slice(0, 3);
}`,
          },
        ],
        complexity: 'Вставка O(L), запрос O(L + ответ). Память O(сумма длин слов).',
      },
      {
        title: 'Слова на телефонной клавиатуре',
        statement:
          'Дан словарь и последовательность цифр (2-9). Перечислить все слова словаря, которые можно набрать этим набором (каждая буква соответствует одной цифре в заданном порядке).',
        solutions: [
          {
            lang: 'Python',
            code: `# Словарь -> trie; по цифрам идём бэктрекингом по допустимым буквам
KEYS = {'2': 'abc', '3': 'def', '4': 'ghi', '5': 'jkl',
        '6': 'mno', '7': 'pqrs', '8': 'tuv', '9': 'wxyz'}

def build_trie(words):
    root = {}
    for w in words:
        node = root
        for ch in w:
            node = node.setdefault(ch, {})
        node['#'] = True
    return root

def match(root, digits):
    res = []
    def dfs(node, pos, path):
        if pos == len(digits):
            if '#' in node:
                res.append(''.join(path))
            return
        for ch in KEYS[digits[pos]]:   # буквы, соответствующие этой цифре
            if ch in node:
                path.append(ch)
                dfs(node[ch], pos + 1, path)
                path.pop()
    dfs(root, 0, [])
    return res`,
          },
          {
            lang: 'Java',
            code: `// Бэктрекинг по trie: на каждой цифре пробуем все её буквы
static final String[] KEYS = {"", "", "abc", "def", "ghi", "jkl",
                              "mno", "pqrs", "tuv", "wxyz"};

List<String> match(Node root, String digits) {
    List<String> res = new ArrayList<>();
    dfs(root, 0, digits, new StringBuilder(), res);
    return res;
}

void dfs(Node node, int pos, String digits, StringBuilder path, List<String> res) {
    if (pos == digits.length()) {
        if (node.isEnd) res.add(path.toString());
        return;
    }
    for (char c : KEYS[digits.charAt(pos) - '0'].toCharArray()) {
        Node next = node.next.get(c);
        if (next != null) {
            path.append(c);
            dfs(next, pos + 1, digits, path, res);
            path.setLength(path.length() - 1);   // откат
        }
    }
}`,
          },
          {
            lang: 'C++',
            code: `// Бэктрекинг по trie: на каждой цифре пробуем только её буквы-переходы
static const string KEYS[10] = {"", "", "abc", "def", "ghi", "jkl",
                                "mno", "pqrs", "tuv", "wxyz"};

void dfs(TrieNode* node, int pos, const string& digits,
         string& path, vector<string>& res) {
    if (pos == (int)digits.size()) {
        if (node->isEnd) res.push_back(path);    // здесь кончается слово словаря
        return;
    }
    for (char c : KEYS[digits[pos] - '0']) {     // буквы текущей цифры
        if (node->next.count(c)) {               // такой переход есть в словаре
            path.push_back(c);
            dfs(node->next[c], pos + 1, digits, path, res);
            path.pop_back();                     // откат (backtrack)
        }
    }
}

vector<string> match(TrieNode* root, const string& digits) {
    vector<string> res; string path;
    dfs(root, 0, digits, path, res);
    return res;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Бэктрекинг по trie: на каждой цифре пробуем все её буквы
const KEYS = ['', '', 'abc', 'def', 'ghi', 'jkl', 'mno', 'pqrs', 'tuv', 'wxyz'];

function match(root, digits) {
  const res = [];
  const dfs = (node, pos, path) => {
    if (pos === digits.length) {
      if (node.end) res.push(path);     // здесь кончается слово словаря
      return;
    }
    for (const ch of KEYS[+digits[pos]]) {   // буквы текущей цифры
      if (node[ch]) dfs(node[ch], pos + 1, path + ch);
    }
  };
  dfs(root, 0, '');
  return res;
}`,
          },
        ],
        complexity: 'O(размер поддерева × длина) на запрос; вставка O(L).',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Trie (Insert and Search)', url: 'https://www.geeksforgeeks.org/trie-insert-and-search/' },
      { label: 'LeetCode — задачи с тегом Trie', url: 'https://leetcode.com/tag/trie/' },
    ],
  },
  {
    id: 'math',
    name: 'Математика (Евклид)',
    idea:
      'Алгоритмические задачи на теоретико-числовые конструкции: НОД/НОК (алгоритм Евклида), простые числа и решето Эратосфена, быстрое возведение в степень, свойства факториалов. Общий приём — заменить «наивный» перебор формулой или логарифмическим алгоритмом: алгоритм Евклида считает НОД за O(log min(a,b)) (каждая итерация уменьшает числа минимум вдвое), решето Эратосфена вычёркивает составные за O(n log log n) — почти линейно, быстрое возведение в степень — за O(log b) вместо b умножений.',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'НОД перебором всех делителей от 1 до min(a,b) — это O(min): для чисел порядка 10⁹ это миллиард итераций. Проверка каждого числа на простоту полным переделом делителей до самого числа — тоже неприемлема; даже «до корня» для всех чисел до n даёт ~n·√n операций.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Евклид: gcd(a, b) = gcd(b, a mod b), остаток убывает как минимум вдвое за две итерации → O(log min). Простые числа до n — решето: вычёркиваем кратные каждого простого, начиная с p² (меньшие кратные уже вычеркнуты), итого O(n log log n). Степень a^b — «возведением в квадрат» по двоичным разрядам показателя за O(log b) умножений.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• НОД/НОК, сокращение дробей, диагонали прямоугольника.\n' +
          '• Простые числа: решето Эратосфена, проверка простоты за O(√n).\n' +
          '• Быстрое возведение в степень и арифметика по модулю (хеш-подсчёты, шифрование).\n' +
          '• Нули в конце факториала, подсчёт множителей 2 и 5.',
      },
    ],
    examples: [
      {
        title: 'Решето Эратосфена — количество простых до N',
        statement:
          'Дано N. Посчитать, сколько простых чисел не больше N.',
        solutions: [
          {
            lang: 'Python',
            code: `# Отмечаем кратные каждого простого, начиная с p*p (меньшие уже отмечены)
def count_primes(n):
    if n < 2:
        return 0
    is_prime = [True] * n
    is_prime[0] = is_prime[1] = False
    for p in range(2, int(n**0.5) + 1):
        if is_prime[p]:
            for multiple in range(p * p, n, p):   # старт с p*p — оптимизация
                is_prime[multiple] = False
    return sum(is_prime)
# count_primes(10) == 4 (2, 3, 5, 7)`,
          },
          {
            lang: 'Java',
            code: `// Классическое решето; старт отметки с p*p — кратные p*2..p*(p-1) уже вычеркнуты
int countPrimes(int n) {
    if (n < 2) return 0;
    boolean[] composite = new boolean[n];
    for (int p = 2; (long) p * p < n; p++) {
        if (!composite[p]) {
            for (int m = p * p; m < n; m += p) {
                composite[m] = true;
            }
        }
    }
    int count = 0;
    for (int i = 2; i < n; i++) if (!composite[i]) count++;
    return count;
}`,
          },
          {
            lang: 'C++',
            code: `// Решето: вычёркиваем кратные p, начиная с p*p (меньшие уже вычеркнуты)
int countPrimes(int n) {
    if (n < 2) return 0;
    vector<bool> composite(n, false);
    for (int p = 2; (long)p * p < n; p++) {
        if (!composite[p]) {
            for (int m = p * p; m < n; m += p)
                composite[m] = true;
        }
    }
    int count = 0;
    for (int i = 2; i < n; i++) if (!composite[i]) count++;
    return count;
}
// countPrimes(10) == 4 (2, 3, 5, 7)`,
          },
          {
            lang: 'JavaScript',
            code: `// Отмечаем кратные каждого простого, стартуя с p*p — меньшие уже отмечены
function countPrimes(n) {
  if (n < 2) return 0;
  const composite = new Array(n).fill(false);
  for (let p = 2; p * p < n; p++) {
    if (!composite[p]) {
      for (let m = p * p; m < n; m += p)   // шаг p — только кратные
        composite[m] = true;
    }
  }
  let count = 0;
  for (let i = 2; i < n; i++) if (!composite[i]) count++;
  return count;
}
// countPrimes(10) === 4 (2, 3, 5, 7)`,
          },
        ],
        complexity: 'O(n log log n) время, O(n) память.',
      },
      {
        title: 'Нули в конце факториала',
        statement:
          'Найти количество завершающих нулей в n! (без вычисления самого факториала).',
        solutions: [
          {
            lang: 'Python',
            code: `# Нуль рождается парой 2×5; двоек всегда больше, чем пятёрок —
# считаем только множители 5 в разложениях чисел 1..n
def trailing_zeros(n):
    count = 0
    d = 5
    while d <= n:
        count += n // d           # сколько чисел до n делятся на d
        d *= 5                    # учёт кратных 25, 125, ... (у них два и более 5)
    return count
# trailing_zeros(30) == 4 (из 5,10,15,20,25 — последняя даёт две пятёрки)`,
          },
          {
            lang: 'Java',
            code: `// Количество множителей 5 в n! = floor(n/5) + floor(n/25) + floor(n/125) + ...
int trailingZeroes(int n) {
    int count = 0;
    while (n >= 5) {
        n /= 5;                   // каждый делитель 5 «снимает» один уровень
        count += n;
    }
    return count;
}`,
          },
          {
            lang: 'C++',
            code: `// Нули даёт пара 2×5; пятёрок всегда меньше — считаем только их в n!
int trailingZeroes(int n) {
    int count = 0;
    while (n >= 5) {
        n /= 5;                   // floor(n/5) + floor(n/25) + floor(n/125) + ...
        count += n;               // кратные 25 дают две пятёрки — уже учтены
    }
    return count;
}
// trailingZeroes(30) == 4`,
          },
          {
            lang: 'JavaScript',
            code: `// Нуль рождается парой 2×5; двоек больше — считаем только пятёрки в n!
function trailingZeros(n) {
  let count = 0;
  while (n >= 5) {
    n = Math.floor(n / 5);        // floor(n/5) + floor(n/25) + floor(n/125) + ...
    count += n;                   // кратные 25 дают две пятёрки — учтены
  }
  return count;
}
// trailingZeros(30) === 4`,
          },
        ],
        complexity: 'O(log₅ n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'CP-Algorithms — Sieve of Eratosthenes', url: 'https://cp-algorithms.com/num_methods/primes_sieve.html' },
      { label: 'LeetCode — задачи с тегом Math', url: 'https://leetcode.com/tag/math/' },
    ],
  },
  {
    id: 'linked_list',
    name: 'Связные списки (Флойд)',
    idea:
      'Односвязный список — цепочка узлов «значение + ссылка на следующий»: нельзя идти назад или обратиться к элементу по индексу за O(1), поэтому многие операции строятся на «двух бегунах». Медленный и быстрый указатели движутся с разной скоростью (приём Роберта Флойда): пока быстрый дошёл до конца, медленный оказался ровно в середине; если в списке есть цикл, бегуны обязательно встретятся внутри него. Все эти задачи решаются за O(n) времени при O(1) дополнительной памяти.',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Найти середину списка, сначала посчитав его длину, — два прохода вместо одного (работает, но медленнее). Обнаружить цикл, сохраняя каждый посещённый узел в хеш-множестве, — O(n) дополнительной памяти; на собеседовании почти всегда требуют обход за O(1) по памяти.',
      },
      {
        title: 'Эффективное решение',
        body:
          '«Черепаха и заяц»: медленный делает шаг +1, быстрый +2. Середина и факт наличия цикла находятся за один проход O(n)/O(1): при наличии цикла разрыв скоростей 1 означает, что бегуны «догонят» друг друга. Точку входа в цикл догоняем второй черепахой, стартовав от начала списка. Разворот списка — три указателя prev/cur/next за один проход.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Середина списка; k-й элемент с конца (два указателя с зазором k).\n' +
          '• Обнаружение цикла и поиск точки входа в цикл (алгоритм Флойда).\n' +
          '• Разворот списка (итеративно/рекурсивно), слияние двух отсортированных списков.\n' +
          '• Проверка палиндрома связного списка за O(1) памяти (середина + разворот).',
      },
    ],
    examples: [
      {
        title: 'Обратить связный список',
        statement:
          'Дан однонаправленный связный список (как массив значений). Перевернуть его за O(n) и O(1) дополнительной памяти. Вернуть значения в обратном порядке.',
        solutions: [
          {
            lang: 'Python',
            code: `# Три указателя: prev, cur, next — перенаправляем стрелки по одному узлу
def reverse_list(vals):
    # моделируем список парами (value, next_index)
    n = len(vals)
    nxt = [i + 1 if i + 1 < n else -1 for i in range(n)]
    prev = -1
    cur = 0
    while cur != -1:
        save = nxt[cur]           # сохранить следующего ПЕРЕД перенаправлением
        nxt[cur] = prev           # стрелка теперь назад
        prev = cur
        cur = save
    # собираем результат от нового начала (prev)
    res, i = [], prev
    while i != -1:
        res.append(vals[i])
        i = nxt[i]
    return res
# [1,2,3,4,5] -> [5,4,3,2,1]`,
          },
          {
            lang: 'Java',
            code: `// Классическая итерация: prev / cur / next
ListNode reverseList(ListNode head) {
    ListNode prev = null;
    ListNode cur = head;
    while (cur != null) {
        ListNode save = cur.next;  // следующий узел до перенаправления
        cur.next = prev;           // разворачиваем указатель
        prev = cur;                // «хвост» развёрнутой части сдвинулся
        cur = save;
    }
    return prev;                   // новое начало списка
}`,
          },
          {
            lang: 'C++',
            code: `// Три указателя: prev / cur / save — перенаправляем стрелки по одному узлу
ListNode* reverseList(ListNode* head) {
    ListNode* prev = nullptr;
    ListNode* cur = head;
    while (cur != nullptr) {
        ListNode* save = cur->next;  // следующий узел ДО перенаправления
        cur->next = prev;            // разворачиваем указатель назад
        prev = cur;                  // новое начало развёрнутой части
        cur = save;
    }
    return prev;                     // прежнее nullptr-«дно» стало концом
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Разворот за один проход: prev / cur / save (узел: {val, next})
function reverseList(head) {
  let prev = null, cur = head;
  while (cur !== null) {
    const save = cur.next;      // следующий узел до перенаправления
    cur.next = prev;            // разворачиваем стрелку назад
    prev = cur;                 // новое начало развёрнутой части
    cur = save;
  }
  return prev;                  // новое начало списка
}
// [1,2,3,4,5] -> [5,4,3,2,1]`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
      {
        title: 'Середина списка',
        statement:
          'Дан однонаправленный список. Найти средний узел (при чётной длине — второй из средних) за один проход без подсчёта длины. Вернуть его значение и позицию (с 1).',
        solutions: [
          {
            lang: 'Python',
            code: `# Медленный бегун делает 1 шаг, быстрый — 2; когда быстрый у конца, медленный в середине
def middle(vals):
    n = len(vals)
    slow = fast = 0                # индексы «бегунов»
    while fast + 1 < n and fast + 2 < n:   # быстрый может сделать двойной шаг
        slow += 1
        fast += 2
    return vals[slow], slow + 1
# [1,2,3,4,5] -> (3, 3); [1,2,3,4] -> (3, 3)`,
          },
          {
            lang: 'Java',
            code: `// Флойд в «спокойном» режиме: slow +1, fast +2
ListNode middleNode(ListNode head) {
    ListNode slow = head;
    ListNode fast = head;
    while (fast != null && fast.next != null) {
        slow = slow.next;          // один шаг
        fast = fast.next.next;     // два шага
    }
    return slow;                   // fast уперся — slow в середине
}`,
          },
          {
            lang: 'C++',
            code: `// Черепаха (+1) и заяц (+2): заяц дошёл до конца — черепаха в середине
ListNode* middleNode(ListNode* head) {
    ListNode* slow = head;
    ListNode* fast = head;
    while (fast != nullptr && fast->next != nullptr) {
        slow = slow->next;         // один шаг
        fast = fast->next->next;   // два шага
    }
    return slow;                   // при чётной длине — второй из средних
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Медленный бегун +1, быстрый +2: быстрый у конца — медленный в середине
function middleNode(head) {
  let slow = head, fast = head;
  while (fast !== null && fast.next !== null) {
    slow = slow.next;              // один шаг
    fast = fast.next.next;         // два шага
  }
  return slow;                     // при чётной длине — второй из средних
}`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Linked List Data Structure', url: 'https://www.geeksforgeeks.org/data-structures/linked-list/' },
      { label: 'LeetCode — задачи с тегом Linked List', url: 'https://leetcode.com/tag/linked-list/' },
    ],
  },
];
