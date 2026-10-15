// Теория, часть 1: карточки паттернов (два указателя → BFS) и типы для страницы «Теория».
export interface TheoryExample {
  title: string;
  statement: string;
  solutions: { lang: string; code: string }[];
  complexity: string;
}

export interface TheorySection {
  title: string;
  body: string;
}

export interface TheoryPattern {
  id: string;
  name: string;
  idea: string;
  sections?: TheorySection[];
  examples: TheoryExample[];
  links: { label: string; url: string }[];
}

export const THEORY_PART1: TheoryPattern[] = [
  {
    id: 'two_pointers',
    name: 'Два указателя',
    idea:
      'Метод двух указателей позволяет решать широкий класс задач: например, когда мы имеем дело с отсортированным массивом (или парой отсортированных массивов) и нужно найти такие два элемента, что их сумма как можно ближе к наперёд заданному числу. Он позволяет оптимизировать решение алгоритмических задач, снижая временную сложность с квадратной O(n²) до линейной O(n), а затраты памяти — до O(1). ' +
      'Для новичка: запись O («биг-О») описывает, как быстро растёт время работы алгоритма при росте размера входа n. O(n) — линейный рост: данных стало в 10 раз больше — работа примерно в 10 раз дольше. O(n²) — квадратичный рост: время растёт как число всех пар элементов. Разница огромна: при n = 100 000 линейный алгоритм выполнит ~10⁵ операций (миллисекунды), а квадратичный — ~10¹⁰ (десятки секунд; на собеседовании это «не уложилось в лимит»).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Первое, что приходит в голову, — пройтись по всем парам элементов массива A[i] и A[j] и сравнить их сумму с X. Это делается вложенным циклом: для каждого из n элементов ещё до n проверок. Сложность такого алгоритма — O(n²), и на больших данных он не укладывается в ограничения по времени.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Теперь применим метод двух указателей. В качестве двух указателей выступают две переменные, которые в начале хранят индексы первого и последнего элемента. На каждой итерации будем сравнивать сумму элементов, на которые указывают указатели, с X. Если сумма больше X, то нужно подвинуть правый указатель влево, чтобы сумма уменьшилась (массив отсортирован). Если же сумма меньше нужной, то двинем левый указатель вправо. И так до тех пор, пока не найдём нужные элементы или же не попадём в ситуацию, когда два указателя определяют один и тот же элемент. Так как по каждому элементу мы проходимся максимум один раз, итоговая сложность — O(n).',
      },
      {
        title: 'Основные типы задач на два указателя',
        body:
          '• Указатели на краях (навстречу друг другу):\n' +
          '   – Two Sum (найти пару с суммой X): указатели ставятся на начало и конец отсортированного массива. Если сумма больше X, правый указатель сдвигается влево; если меньше — левый сдвигается вправо.\n' +
          '   – Разворот массива или строки: обмен элементов в точках указателей с последующим их сближением к центру.\n' +
          '• Указатели в одном направлении (скользящее окно или параллельное движение):\n' +
          '   – Слияние двух отсортированных массивов: сравнение элементов под указателями и запись меньшего в новый массив.\n' +
          '   – Поиск подотрезка с заданной суммой или условием: один указатель расширяет границу справа, а второй сужает слева, когда условие нарушается.\n' +
          '• Черепаха и заяц (с разной скоростью):\n' +
          '   – Поиск циклов в связных списках или удаление дубликатов на месте.',
      },
    ],
    examples: [
      {
        title: '3Sum — тройка с нулевой суммой',
        statement:
          'Дан массив целых чисел (не отсортирован). Найти все уникальные тройки (a, b, c), в сумме дающие 0. Дубликаты троек не выводить.',
        solutions: [
          {
            lang: 'Python',
            code: `# Фиксируем один элемент и решаем «two sum» на остатке двумя указателями
def three_sum(a):
    a.sort()                      # сортировка — условие для двух указателей
    res = []
    for i in range(len(a) - 2):
        if i > 0 and a[i] == a[i-1]:
            continue              # пропускаем дубликаты первого элемента
        l, r = i + 1, len(a) - 1  # два указателя: левый и правый
        while l < r:
            s = a[i] + a[l] + a[r]
            if s == 0:
                res.append((a[i], a[l], a[r]))
                # сдвигаем оба, пропуская дубликаты
                while l < r and a[l] == a[l+1]: l += 1
                while l < r and a[r] == a[r-1]: r -= 1
                l += 1; r -= 1
            elif s < 0:
                l += 1            # сумма мала — увеличиваем её (левый вправо)
            else:
                r -= 1            # сумма велика — уменьшаем (правый влево)
    return res`,
          },
          {
            lang: 'Java',
            code: `// Суть решения (метод класса): фиксация i + два указателя
List<List<Integer>> threeSum(int[] a) {
    Arrays.sort(a);               // обязательное условие для двух указателей
    List<List<Integer>> res = new ArrayList<>();
    for (int i = 0; i < a.length - 2; i++) {
        if (i > 0 && a[i] == a[i-1]) continue;   // дубликаты первого элемента
        int l = i + 1, r = a.length - 1;
        while (l < r) {
            int s = a[i] + a[l] + a[r];
            if (s == 0) {
                res.add(List.of(a[i], a[l], a[r]));
                while (l < r && a[l] == a[l+1]) l++;   // дубликаты
                while (l < r && a[r] == a[r-1]) r--;
                l++; r--;
            } else if (s < 0) {
                l++;                    // сумма мала — двигаем левый вправо
            } else {
                r--;                    // сумма велика — двигаем правый влево
            }
        }
    }
    return res;
}`,
          },
          {
            lang: 'C++',
            code: `// Фиксируем i, на остатке решаем «two sum» двумя указателями
vector<vector<int>> threeSum(vector<int>& a) {
    sort(a.begin(), a.end());     // обязательное условие метода
    vector<vector<int>> res;
    int n = a.size();
    for (int i = 0; i < n - 2; i++) {
        if (i > 0 && a[i] == a[i-1]) continue;   // пропуск дубликатов
        int l = i + 1, r = n - 1;
        while (l < r) {
            long s = (long)a[i] + a[l] + a[r];   // long — защита от переполнения
            if (s == 0) {
                res.push_back({a[i], a[l], a[r]});
                while (l < r && a[l] == a[l+1]) l++;   // дубликаты
                while (l < r && a[r] == a[r-1]) r--;
                l++; r--;
            } else if (s < 0) {
                l++;                    // сумма мала — левый указатель вправо
            } else {
                r--;                    // сумма велика — правый указатель влево
            }
        }
    }
    return res;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Фиксируем один элемент, на остатке — два указателя
function threeSum(a) {
  a.sort((x, y) => x - y);        // числовой компаратор (без него сортировка строковая!)
  const res = [];
  for (let i = 0; i < a.length - 2; i++) {
    if (i > 0 && a[i] === a[i-1]) continue;      // пропуск дубликатов
    let l = i + 1, r = a.length - 1;
    while (l < r) {
      const s = a[i] + a[l] + a[r];
      if (s === 0) {
        res.push([a[i], a[l], a[r]]);
        while (l < r && a[l] === a[l+1]) l++;    // дубликаты
        while (l < r && a[r] === a[r-1]) r--;
        l++; r--;
      } else if (s < 0) {
        l++;                        // сумма мала — увеличиваем её
      } else {
        r--;                        // сумма велика — уменьшаем
      }
    }
  }
  return res;
}`,
          },
        ],
        complexity: 'O(n²) время (внешний цикл n × внутренний проход указателей), O(log n) память на сортировку.',
      },
      {
        title: 'Перенос нулей в конец',
        statement:
          'Дан массив. Перенести все нули в конец, сохранив порядок ненулевых элементов, за один проход и без дополнительного массива.',
        solutions: [
          {
            lang: 'Python',
            code: `# Указатель zero — позиция, куда положить следующий ненулевой элемент
def move_zeros(a):
    zero = 0                      # «граница» уже расставленных элементов
    for x in a:
        if x != 0:
            a[zero] = x           # записываем ненулевой на границу
            zero += 1
    while zero < len(a):          # всё после границы — нули
        a[zero] = 0
        zero += 1
    return a
# [0,1,0,3,12] -> [1,3,12,0,0]`,
          },
          {
            lang: 'Java',
            code: `// Два указателя: i — обход, j — куда класть следующий ненулевой
void moveZeroes(int[] a) {
    int j = 0;                    // позиция следующего ненулевого элемента
    for (int i = 0; i < a.length; i++) {
        if (a[i] != 0) {
            int tmp = a[j];       // обмен «вперёд» (если i == j — тривиален)
            a[j] = a[i];
            a[i] = tmp;
            j++;                  // границу сдвигаем только на ненулевом
        }
    }
}
// [0,1,0,3,12] -> [1,3,12,0,0]`,
          },
          {
            lang: 'C++',
            code: `// Два указателя: i — обход массива, j — позиция следующего ненулевого
void moveZeroes(vector<int>& a) {
    int j = 0;                    // куда класть следующий ненулевой элемент
    for (int i = 0; i < (int)a.size(); i++) {
        if (a[i] != 0) {
            swap(a[j], a[i]);     // обмен «вперёд», тривиален при i == j
            j++;                  // границу сдвигаем только на ненулевом
        }
    }
}
// [0,1,0,3,12] -> [1,3,12,0,0]`,
          },
          {
            lang: 'JavaScript',
            code: `// Указатель j — граница: куда положить следующий ненулевой элемент
function moveZeros(a) {
  let j = 0;
  for (let i = 0; i < a.length; i++) {
    if (a[i] !== 0) {
      [a[j], a[i]] = [a[i], a[j]]; // обмен «вперёд» на месте, O(1) памяти
      j++;                         // границу двигаем только на ненулевом
    }
  }
  return a;
}
// [0,1,0,3,12] -> [1,3,12,0,0]`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Two Pointer Technique', url: 'https://www.geeksforgeeks.org/two-pointer-technique/' },
      { label: 'LeetCode — задачи с тегом Two Pointers', url: 'https://leetcode.com/tag/two-pointers/' },
    ],
  },
  {
    id: 'sliding_window',
    name: 'Скользящее окно',
    idea:
      'Скользящее окно — приём для задач о непрерывных отрезках (подмассивах и подстроках): найти самый короткий/длинный отрезок или их количество с нужным свойством. Окно — это пара индексов [left, right]: правая граница расширяет окно, левая сужает его, когда условие нарушено или окно стало «хорошим». Обе границы движутся только вперёд, поэтому суммарная сложность — O(n) (линейная: время растёт пропорционально длине массива), а не O(n²), как при переборе всех отрезков. Типичные формулировки: «минимальный/максимальный отрезок подряд, удовлетворяющий условию».',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Наивно проверить каждый из ~n²/2 отрезков и для каждого посчитать сумму с нуля — это O(n³); даже с аккуратным подсчётом «на лету» наивный перебор даёт O(n²). При n = 10⁵ (сто тысяч элементов) квадратичный алгоритм выполняет ~10¹⁰ операций и не успевает за отведённое время.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Двигаем правый край окна по массиву, добавляя элемент в «состояние окна» (сумму, счётчик нулей и т.п.). Как только условие выполнилось (или наоборот нарушилось) — сдвигаем левый край, вычитая выходящие элементы из состояния. Каждое число вошло в окно и вышло из него не более одного раза, поэтому общая работа — O(n), дополнительная память — O(1).',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Кратчайший подмассив с суммой ≥ target (при положительных числах).\n' +
          '• Самая длинная подстрока без повторяющихся символов.\n' +
          '• Максимальная длина отрезка из единиц после переворота не более K нулей.\n' +
          '• Окно фиксированного размера k: сумма, среднее; максимум в окне — вариант с монотонной очередью (deque).',
      },
    ],
    examples: [
      {
        title: 'Кратчайший подмассив с суммой >= target',
        statement:
          'Дан массив положительных целых и число target. Найти длину кратчайшего непрерывного подмассива, сумма которого не меньше target. Если нет — 0.',
        solutions: [
          {
            lang: 'Python',
            code: `# Окно [left, right], current_sum — его сумма
def min_subarray_len(target, a):
    left = 0
    cur = 0                       # сумма текущего окна
    best = float('inf')
    for right, x in enumerate(a):
        cur += x                  # расширяем окно вправо
        # сужаем слева, пока окно остаётся «хорошим»
        while cur >= target:
            best = min(best, right - left + 1)
            cur -= a[left]
            left += 1
    return best if best != float('inf') else 0`,
          },
          {
            lang: 'Java',
            code: `// Окно [left, right]; сужаем, пока сумма >= target
int minSubArrayLen(int target, int[] a) {
    int left = 0, sum = 0, best = Integer.MAX_VALUE;
    for (int right = 0; right < a.length; right++) {
        sum += a[right];          // расширение окна
        while (sum >= target) {   // окно хорошее — пробуем сжать
            best = Math.min(best, right - left + 1);
            sum -= a[left++];
        }
    }
    return best == Integer.MAX_VALUE ? 0 : best;
}`,
          },
          {
            lang: 'C++',
            code: `// Окно [left, right]; сужаем слева, пока сумма >= target
int minSubArrayLen(int target, vector<int>& a) {
    int left = 0, best = INT_MAX;
    long sum = 0;                 // long — защита от переполнения суммы
    for (int right = 0; right < (int)a.size(); right++) {
        sum += a[right];          // расширение окна
        while (sum >= target) {   // окно хорошее — пробуем сжать
            best = min(best, right - left + 1);
            sum -= a[left++];
        }
    }
    return best == INT_MAX ? 0 : best;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Окно [left, right]: расширяем вправо, сужаем слева, пока сумма >= target
function minSubArrayLen(target, a) {
  let left = 0, sum = 0, best = Infinity;
  for (let right = 0; right < a.length; right++) {
    sum += a[right];                // расширяем окно
    while (sum >= target) {         // окно хорошее — пробуем сжать
      best = Math.min(best, right - left + 1);
      sum -= a[left++];
    }
  }
  return best === Infinity ? 0 : best;
}`,
          },
        ],
        complexity: 'O(n) время (каждая граница проходит массив не более одного раза), O(1) память.',
      },
      {
        title: 'Максимум единиц с переворотом не более K нулей',
        statement:
          'Дан массив из 0 и 1. Можно перевернуть не более K нулей в единицы. Найти максимальную длину непрерывного отрезка, содержащего только единицы после таких переворотов.',
        solutions: [
          {
            lang: 'Python',
            code: `# Окно содержит <= K нулей; правая граница всегда идёт вперёд
def longest_ones(a, k):
    left = 0
    zeros = 0                     # число нулей в текущем окне
    best = 0
    for right, x in enumerate(a):
        if x == 0:
            zeros += 1
        while zeros > k:          # окно «плохое» — сдвигаем левую границу
            if a[left] == 0:
                zeros -= 1
            left += 1
        best = max(best, right - left + 1)
    return best`,
          },
          {
            lang: 'Java',
            code: `// Инвариант окна: количество нулей <= k
int longestOnes(int[] a, int k) {
    int left = 0, zeros = 0, best = 0;
    for (int right = 0; right < a.length; right++) {
        if (a[right] == 0) zeros++;
        while (zeros > k) {       // сужаем, пока условие не выполнено
            if (a[left++] == 0) zeros--;
        }
        best = Math.max(best, right - left + 1);
    }
    return best;
}`,
          },
          {
            lang: 'C++',
            code: `// Инвариант окна: количество нулей <= k
int longestOnes(vector<int>& a, int k) {
    int left = 0, zeros = 0, best = 0;
    for (int right = 0; right < (int)a.size(); right++) {
        if (a[right] == 0) zeros++;
        while (zeros > k) {       // сужаем, пока условие не восстановлено
            if (a[left++] == 0) zeros--;
        }
        best = max(best, right - left + 1);
    }
    return best;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Инвариант окна: нулей внутри не больше k
function longestOnes(a, k) {
  let left = 0, zeros = 0, best = 0;
  for (let right = 0; right < a.length; right++) {
    if (a[right] === 0) zeros++;
    while (zeros > k) {           // окно «плохое» — сдвигаем левую границу
      if (a[left++] === 0) zeros--;
    }
    best = Math.max(best, right - left + 1);
  }
  return best;
}`,
          },
        ],
        complexity: 'O(n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Sliding Window Technique', url: 'https://www.geeksforgeeks.org/sliding-window-technique/' },
      { label: 'LeetCode — задачи с тегом Sliding Window', url: 'https://leetcode.com/problem-list/sliding-window/' },
    ],
  },
  {
    id: 'prefix_sum',
    name: 'Префиксная сумма',
    idea:
      'Префиксная сумма — предвычисление накопленных итогов: pref[i] = сумма первых i элементов массива. Тогда ответ на любой запрос «сумма от l до r» получается одним вычитанием pref[r+1] − pref[l] за O(1) («константная» сложность: время ответа не зависит ни от размера массива, ни от длины запроса). Цена — один проход O(n) и память O(n): классический размен «память ради скорости». Работает для любой ассоциативной операции, у которой есть «обратная» (для произведения — с осторожностью из-за нулей или через модульную арифметику).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Считать сумму на каждом запросе в цикле по элементам отрезка — O(n) на один запрос. При q запросах получается O(n·q): для массива из 10⁵ элементов и 10⁵ запросов это ~10¹⁰ операций — слишком медленно, хотя данные статичны и ответ можно подготовить заранее.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Один раз за O(n) строим массив pref, где pref[0] = 0, а pref[i+1] = pref[i] + a[i]. После этого сумма элементов с l по r включительно — это pref[r+1] − pref[l], одна операция вычитания. Все запросы «с нуля» заменены одной подготовкой.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Много запросов суммы/среднего на статичном массиве.\n' +
          '• Наличие подмассива с данной суммой (префиксные суммы + множество просмотренных значений).\n' +
          '• Произведение массива, кроме себя (префиксные и суффиксные произведения).\n' +
          '• Разностный массив (массовые прибавления на отрезке) и 2D-префиксы для запросов на матрице.',
      },
    ],
    examples: [
      {
        title: 'Запросы суммы на статичном массиве',
        statement:
          'Дан неизменяемый массив и множество запросов sum(l, r) (индексы с 0). Ответить на каждый запрос максимально быстро.',
        solutions: [
          {
            lang: 'Python',
            code: `# pref[i] = сумма первых i элементов; pref[0] = 0
def build(a):
    pref = [0] * (len(a) + 1)
    for i, x in enumerate(a):
        pref[i+1] = pref[i] + x   # один проход O(n)
    return pref

def range_sum(pref, l, r):
    return pref[r+1] - pref[l]    # O(1) на запрос
# a = [1, 2, 3, 4]; range_sum(pref, 1, 2) == 5`,
          },
          {
            lang: 'Java',
            code: `// Префиксный массив строится один раз, запросы — O(1)
int[] pref;

void build(int[] a) {
    pref = new int[a.length + 1];
    for (int i = 0; i < a.length; i++) {
        pref[i+1] = pref[i] + a[i];
    }
}

int rangeSum(int l, int r) {      // сумма элементов с l по r включительно
    return pref[r+1] - pref[l];
}`,
          },
          {
            lang: 'C++',
            code: `// Префиксный массив строится один раз, каждый запрос — O(1)
vector<long> pref;

void build(const vector<int>& a) {
    pref.assign(a.size() + 1, 0);
    for (size_t i = 0; i < a.size(); i++)
        pref[i+1] = pref[i] + a[i];   // один проход O(n)
}

long rangeSum(int l, int r) {         // сумма с l по r включительно
    return pref[r+1] - pref[l];       // O(1) на запрос
}`,
          },
          {
            lang: 'JavaScript',
            code: `// pref[i] = сумма первых i элементов; pref[0] = 0
function build(a) {
  const pref = new Array(a.length + 1).fill(0);
  for (let i = 0; i < a.length; i++)
    pref[i + 1] = pref[i] + a[i];     // один проход O(n)
  return pref;
}

function rangeSum(pref, l, r) {
  return pref[r + 1] - pref[l];       // O(1) на запрос
}
// a = [1,2,3,4]; rangeSum(pref, 1, 2) === 5`,
          },
        ],
        complexity: 'O(n) предвычисление + O(1) на запрос; память O(n).',
      },
      {
        title: 'Произведение массива, кроме себя',
        statement:
          'Дан массив n чисел. Для каждой позиции i вычислить произведение всех элементов, кроме a[i]. Без деления и за O(n).',
        solutions: [
          {
            lang: 'Python',
            code: `# Два прохода: слева — произведение «до i», справа — «после i»
def product_except_self(a):
    n = len(a)
    res = [1] * n
    left = 1
    for i in range(n):            # res[i] = произведение a[0..i-1]
        res[i] = left
        left *= a[i]
    right = 1
    for i in range(n - 1, -1, -1):# умножаем на произведение a[i+1..n-1]
        res[i] *= right
        right *= a[i]
    return res
# [1,2,3,4] -> [24,12,8,6]`,
          },
          {
            lang: 'Java',
            code: `// Левый проход собирает произведение «слева», правый — доумножает «справа»
int[] productExceptSelf(int[] a) {
    int n = a.length;
    int[] res = new int[n];
    res[0] = 1;
    for (int i = 1; i < n; i++) {
        res[i] = res[i-1] * a[i-1];      // произведение всех слева от i
    }
    int right = 1;
    for (int i = n - 1; i >= 0; i--) {
        res[i] *= right;                 // умножаем на произведение справа
        right *= a[i];
    }
    return res;
}`,
          },
          {
            lang: 'C++',
            code: `// Левый проход — произведение «до i», правый — доумножение «после i»
vector<long> productExceptSelf(const vector<int>& a) {
    int n = a.size();
    vector<long> res(n, 1);
    long left = 1;
    for (int i = 0; i < n; i++) {        // res[i] = произведение a[0..i-1]
        res[i] = left;
        left *= a[i];
    }
    long right = 1;
    for (int i = n - 1; i >= 0; i--) {   // умножаем на произведение a[i+1..n-1]
        res[i] *= right;
        right *= a[i];
    }
    return res;
}
// [1,2,3,4] -> [24,12,8,6]`,
          },
          {
            lang: 'JavaScript',
            code: `// Два прохода: слева — произведение «до i», справа — «после i»
function productExceptSelf(a) {
  const n = a.length, res = new Array(n).fill(1);
  let left = 1;
  for (let i = 0; i < n; i++) {          // res[i] = произведение a[0..i-1]
    res[i] = left;
    left *= a[i];
  }
  let right = 1;
  for (let i = n - 1; i >= 0; i--) {     // умножаем на произведение справа от i
    res[i] *= right;
    right *= a[i];
  }
  return res;
}
// [1,2,3,4] -> [24,12,8,6]`,
          },
        ],
        complexity: 'O(n) время, O(1) дополнительная память (не считая ответа).',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Prefix Sum Array', url: 'https://www.geeksforgeeks.org/prefix-sum-array-set-1-introduction/' },
      { label: 'LeetCode — задачи с тегом Prefix Sum', url: 'https://leetcode.com/tag/prefix-sum/' },
    ],
  },
  {
    id: 'binary_search',
    name: 'Бинарный поиск',
    idea:
      'Бинарный поиск находит элемент или границу перехода на монотонном предикате P(x) — условии, которое ложно на левой части диапазона и истинно на правой — за O(log n). Логарифмическая сложность означает: область поиска каждый раз уменьшается вдвое, поэтому даже для миллиарда элементов нужно всего ~30 шагов (log₂ 10⁹ ≈ 30), тогда как линейный перебор сделал бы до 10⁹ сравнений. Ключевой навык — правильно сформулировать предикат и инвариант (какие индексы ещё могут содержать ответ). Базовый шаблон: while lo <= hi, mid = (lo+hi)//2, сдвиг lo/hi в зависимости от P(mid). Приём обобщается на «поиск по ответу»: ищем не позицию в массиве, а значение (например, минимальную достаточную скорость).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Линейный перебор всех элементов — O(n): просматриваем массив целиком, пока не найдём цель. Для отсортированных данных это выбрасывает половину информации: сравнив цель с серединой, можно мгновенно отбросить целый полуинтервал, а перебор делает это сравнение до n раз.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Держим границы [lo, hi] области, где возможен ответ. На каждом шаге вычисляем середину mid и одним сравнением оставляем только ту половину, где ответ ещё возможен: a[mid] < цель — ответ справа (lo = mid + 1), иначе — слева (hi = mid − 1). Область сожмётся до пустой за log₂ n шагов → O(log n). Тот же шаблон решает «поиск по ответу» на числовой прямой.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Поиск точного значения в отсортированном массиве (классический).\n' +
          '• Границы lower_bound / upper_bound — первый элемент ≥ x и первый > x.\n' +
          '• Поиск по ответу: минимальное достаточное значение (доставка, распиловка, «минимум максимальной нагрузки»).\\n' +
          '• Повёрнутые отсортированные массивы, пик/минимум, поиск в отсортированной матрице.',
      },
    ],
    examples: [
      {
        title: 'Поиск в отсортированной матрице',
        statement:
          'Данная m×n матрица отсортирована по строкам и столбцам (каждая строка начинается числом больше последнего числа предыдущей). Найти элемент за O(log(m*n)).',
        solutions: [
          {
            lang: 'Python',
            code: `# Матрицу можно «развернуть» в отсортированный массив виртуально
def search_matrix(mat, target):
    m, n = len(mat), len(mat[0])
    lo, hi = 0, m * n - 1          # бинарный поиск по индексу плоского массива
    while lo <= hi:
        mid = (lo + hi) // 2
        v = mat[mid // n][mid % n]  # индекс -> (строка, столбец)
        if v == target:
            return True
        elif v < target:
            lo = mid + 1
        else:
            hi = mid - 1
    return False`,
          },
          {
            lang: 'Java',
            code: `// Виртуальный плоский отсортированный массив: idx -> (idx/n, idx%n)
boolean searchMatrix(int[][] mat, int target) {
    int m = mat.length, n = mat[0].length;
    int lo = 0, hi = m * n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;   // защита от переполнения
        int v = mat[mid / n][mid % n];
        if (v == target) return true;
        else if (v < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return false;
}`,
          },
          {
            lang: 'C++',
            code: `// Виртуальный плоский отсортированный массив: idx -> (idx/n, idx%n)
bool searchMatrix(vector<vector<int>>& mat, int target) {
    int m = mat.size(), n = mat[0].size();
    int lo = 0, hi = m * n - 1;
    while (lo <= hi) {
        int mid = lo + (hi - lo) / 2;   // защита от переполнения
        int v = mat[mid / n][mid % n];
        if (v == target) return true;
        else if (v < target) lo = mid + 1;
        else hi = mid - 1;
    }
    return false;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Матрицу «разворачиваем» в виртуальный плоский отсортированный массив
function searchMatrix(mat, target) {
  const m = mat.length, n = mat[0].length;
  let lo = 0, hi = m * n - 1;            // поиск по индексу «плоского» массива
  while (lo <= hi) {
    const mid = (lo + hi) >> 1;
    const v = mat[Math.floor(mid / n)][mid % n]; // индекс -> (строка, столбец)
    if (v === target) return true;
    else if (v < target) lo = mid + 1;
    else hi = mid - 1;
  }
  return false;
}`,
          },
        ],
        complexity: 'O(log(m·n)) время, O(1) память.',
      },
      {
        title: 'Минимум в повёрнутом отсортированном массиве',
        statement:
          'Отсортированный по возрастанию массив без дубликатов повёрнут на неизвестное число позиций (например [4,5,6,7,0,1,2]). Найти минимальный элемент за O(log n).',
        solutions: [
          {
            lang: 'Python',
            code: `# Сравниваем a[mid] с a[hi]: если a[mid] > a[hi], минимум справа от mid
def find_min(a):
    lo, hi = 0, len(a) - 1
    while lo < hi:
        mid = (lo + hi) // 2
        if a[mid] > a[hi]:
            lo = mid + 1          # mid не может быть минимумом — ищем справа
        else:
            hi = mid              # a[mid] <= a[hi]: минимум в [lo, mid]
    return a[lo]`,
          },
          {
            lang: 'Java',
            code: `// Инвариант: ответ всегда в [lo, hi]; сравниваем с правым краем
int findMin(int[] a) {
    int lo = 0, hi = a.length - 1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] > a[hi]) {
            lo = mid + 1;         // «разрыв» сортировки справа от mid
        } else {
            hi = mid;             // минимум в левой части (включая mid)
        }
    }
    return a[lo];
}`,
          },
          {
            lang: 'C++',
            code: `// Инвариант: ответ всегда в [lo, hi]; сравниваем середину с правым краем
int findMin(vector<int>& a) {
    int lo = 0, hi = (int)a.size() - 1;
    while (lo < hi) {
        int mid = lo + (hi - lo) / 2;
        if (a[mid] > a[hi])
            lo = mid + 1;         // «разрыв» сортировки справа от mid
        else
            hi = mid;             // минимум в [lo, mid]
    }
    return a[lo];
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Инвариант: ответ всегда в [lo, hi]; сравниваем с правым краем
function findMin(a) {
  let lo = 0, hi = a.length - 1;
  while (lo < hi) {
    const mid = (lo + hi) >> 1;
    if (a[mid] > a[hi]) lo = mid + 1;  // минимум справа от mid
    else hi = mid;                     // минимум в [lo, mid]
  }
  return a[lo];
}`,
          },
        ],
        complexity: 'O(log n) время, O(1) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Binary Search', url: 'https://www.geeksforgeeks.org/binary-search/' },
      { label: 'LeetCode — задачи с тегом Binary Search', url: 'https://leetcode.com/tag/binary-search/' },
    ],
  },
  {
    id: 'sorting',
    name: 'Сортировки / D&C',
    idea:
      'Сортировка — базовый навык, а «разделяй и властвуй» (Divide & Conquer) — способ её построить: разбить массив на части, решить каждую рекурсивно, объединить результаты. Сравняющие сортировки (merge sort, quicksort, heap sort) имеют доказанную нижнюю границу Ω(n log n) сравнений; величина n log n растёт лишь чуть быстрее линейной: для 10⁶ элементов это ~2·10⁷ операций — мгновенно. Merge sort гарантирует O(n log n) в худшем случае (в отличие от quicksort) и устойчива. Счётная и поразрядная сортировки обходят границу сравнений, используя ограниченность значений: O(n + k).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Пузырьковая сортировка и сортировка вставками просты в написании, но делают O(n²) сравнений и обменов. При n = 10⁵ это ~10¹⁰ операций — за секунды не выполняется, и на собеседовании такое решение не пройдёт ограничения по времени.',
      },
      {
        title: 'Эффективное решение',
        body:
          'Merge sort делит массив пополам, сортирует половины рекурсивно и сливает две отсортированные части за O(n): итог — O(n log n) даже в худшем случае. Quicksort быстрее на практике, но в неудачном случае деградирует до O(n²). Для целых чисел из небольшого диапазона сравнения вообще не нужны: counting sort считает частоты значений за O(n + k), где k — размер диапазона.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Сортировка интервалов по началу/концу перед жадным выбором.\n' +
          '• Подсчёт инверсий через merge sort (классика «измени слияние»).\\n' +
          '• K-я порядковая статистика (quickselect за O(n) в среднем или куча).\n' +
          '• Группировка, дедупликация и лексикографические сравнения через сортировку.',
      },
    ],
    examples: [
      {
        title: 'Счётная сортировка для цифр',
        statement:
          'Отсортировать массив однозначных чисел 0..9 за O(n + k), где k = 10, без сравнений.',
        solutions: [
          {
            lang: 'Python',
            code: `# Считаем частоты, затем «разворачиваем» счётчики в отсортированный массив
def counting_sort(a):
    cnt = [0] * 10                # k = 10 возможных значений
    for x in a:
        cnt[x] += 1               # подсчёт частот — O(n)
    out = []
    for v, c in enumerate(cnt):   # восстановление порядка — O(k)
        out.extend([v] * c)
    return out
# [4,2,9,0,2,7] -> [0,2,2,4,7,9]`,
          },
          {
            lang: 'Java',
            code: `// Частотный массив + накопительный проход (стабильность!)
int[] countingSort(int[] a) {
    int[] cnt = new int[10];
    for (int x : a) cnt[x]++;         // подсчёт частот
    int[] out = new int[a.length];
    int pos = 0;
    for (int v = 0; v < 10; v++) {    // заполняем ответ по возрастанию
        for (int i = 0; i < cnt[v]; i++) {
            out[pos++] = v;
        }
    }
    return out;
}`,
          },
          {
            lang: 'C++',
            code: `// Считаем частоты значений, затем «разворачиваем» счётчики по возрастанию
vector<int> countingSort(const vector<int>& a) {
    int cnt[10] = {0};                // k = 10 возможных значений
    for (int x : a) cnt[x]++;         // подсчёт частот — O(n)
    vector<int> out;
    for (int v = 0; v < 10; v++)      // восстановление порядка — O(k)
        while (cnt[v]--) out.push_back(v);
    return out;
}
// [4,2,9,0,2,7] -> [0,2,2,4,7,9]`,
          },
          {
            lang: 'JavaScript',
            code: `// Считаем частоты значений, затем «разворачиваем» счётчики по возрастанию
function countingSort(a) {
  const cnt = new Array(10).fill(0);   // k = 10 возможных значений
  for (const x of a) cnt[x]++;         // подсчёт частот — O(n)
  const out = [];
  for (let v = 0; v < 10; v++)         // восстановление порядка — O(k)
    for (let i = 0; i < cnt[v]; i++) out.push(v);
  return out;
}
// [4,2,9,0,2,7] -> [0,2,2,4,7,9]`,
          },
        ],
        complexity: 'O(n + k) время, O(k) память. Эффективна при малом диапазоне значений.',
      },
      {
        title: 'Подсчёт инверсий через merge sort',
        statement:
          'Инверсия — пара (i, j), i < j и a[i] > a[j]. Посчитать количество инверсий за O(n log n).',
        solutions: [
          {
            lang: 'Python',
            code: `# При слиянии двух отсортированных половин каждый «перескок» — инверсия
def count_inversions(a):
    def sort_count(arr):
        if len(arr) <= 1:
            return arr, 0
        mid = len(arr) // 2
        left, inv_l = sort_count(arr[:mid])
        right, inv_r = sort_count(arr[mid:])
        merged, inv = [], inv_l + inv_r
        i = j = 0
        while i < len(left) and j < len(right):
            if left[i] <= right[j]:    # <= : устойчиво, не считаем
                merged.append(left[i]); i += 1
            else:
                # left[i] больше ВСЕХ оставшихся right[j..] — инверсии
                merged.append(right[j])
                inv += len(left) - i
                j += 1
        merged.extend(left[i:]); merged.extend(right[j:])
        return merged, inv
    return sort_count(a)[1]`,
          },
          {
            lang: 'Java',
            code: `// Классический merge sort с подсчётом на этапе слияния
long countInversions(int[] a) {
    int[] tmp = new int[a.length];
    return mergeCount(a, 0, a.length, tmp);
}

long mergeCount(int[] a, int lo, int hi, int[] tmp) {
    if (hi - lo <= 1) return 0;
    int mid = lo + (hi - lo) / 2;
    long inv = mergeCount(a, lo, mid, tmp) + mergeCount(a, mid, hi, tmp);
    int i = lo, j = mid, k = lo;
    while (i < mid && j < hi) {
        if (a[i] <= a[j]) tmp[k++] = a[i++];
        else {
            tmp[k++] = a[j++];
            inv += mid - i;      // a[j] меньше всех оставшихся в левой части
        }
    }
    while (i < mid) tmp[k++] = a[i++];
    while (j < hi)  tmp[k++] = a[j++];
    System.arraycopy(tmp, lo, a, lo, hi - lo);
    return inv;
}`,
          },
          {
            lang: 'C++',
            code: `// Merge sort с подсчётом инверсий на этапе слияния
long long mergeCount(vector<int>& a, vector<int>& tmp, int lo, int hi) {
    if (hi - lo <= 1) return 0;
    int mid = lo + (hi - lo) / 2;
    long long inv = mergeCount(a, tmp, lo, mid) + mergeCount(a, tmp, mid, hi);
    int i = lo, j = mid, k = lo;
    while (i < mid && j < hi) {
        if (a[i] <= a[j]) tmp[k++] = a[i++];
        else {
            tmp[k++] = a[j++];
            inv += mid - i;      // a[j] меньше всех оставшихся в левой части
        }
    }
    while (i < mid) tmp[k++] = a[i++];
    while (j < hi)  tmp[k++] = a[j++];
    for (int t = lo; t < hi; t++) a[t] = tmp[t];
    return inv;
}

long long countInversions(vector<int>& a) {
    vector<int> tmp(a.size());
    return mergeCount(a, tmp, 0, a.size());
}`,
          },
          {
            lang: 'JavaScript',
            code: `// При слиянии двух отсортированных половин каждый «перескок» — инверсия
function countInversions(a) {
  function sortCount(arr) {
    if (arr.length <= 1) return [arr, 0];
    const mid = arr.length >> 1;
    const [left, invL] = sortCount(arr.slice(0, mid));
    const [right, invR] = sortCount(arr.slice(mid));
    const merged = [];
    let inv = invL + invR, i = 0, j = 0;
    while (i < left.length && j < right.length) {
      if (left[i] <= right[j]) {         // устойчиво — не считаем
        merged.push(left[i++]);
      } else {
        merged.push(right[j++]);
        inv += left.length - i;          // left[i] больше всех оставшихся справа
      }
    }
    return [merged.concat(left.slice(i), right.slice(j)), inv];
  }
  return sortCount(a)[1];
}`,
          },
        ],
        complexity: 'O(n log n) время, O(n) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — Count Inversions in an Array', url: 'https://www.geeksforgeeks.org/count-inversions-an-array/' },
      { label: 'LeetCode — задачи с тегом Sorting', url: 'https://leetcode.com/tag/sorting/' },
    ],
  },
  {
    id: 'dfs',
    name: 'DFS / Графы',
    idea:
      'DFS (depth-first search, поиск в глубину): из текущей вершины идём как можно глубже по одному ребру, упираемся — откатываемся (backtrack) и пробуем следующую ветвь. Реализуется рекурсией или явным стеком; посещённые вершины обязательно помечаем. Полный обход структуры стоит O(V + E) — «вершины плюс рёбра»: каждый элемент обработан ровно один раз, поэтому даже на графе с миллионами рёбер работа линейна. DFS отвечает на вопросы о достижимости, компонентах связности, наличии циклов, топологической сортировке; на деревьях — любые задачи про поддерево (суммы, глубина, сравнение).',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'Без отметок «посещено» обход графа с циклами может ходить по кругу бесконечно или экспоненциально перебирать одни и те же пути повторно. Наивная рекурсия на глубокой структуре (цепочка из 10⁵ узлов) дополнительно рискует переполнить стек вызовов (stack overflow).',
      },
      {
        title: 'Эффективное решение',
        body:
          'Помечаем вершину сразу при входе, идём вглубь до тупика, затем откатываемся и пробуем непосещённых соседей. Каждая вершина и каждое ребро обрабатываются один раз → O(V + E). Для глубоких деревьев и цепочек вместо рекурсии используем явный стек — он живёт в куче и не ограничен размером стека вызовов.',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Проверка достижимости и подсчёт компонент связности.\n' +
          '• Обнаружение циклов, топологическая сортировка (DAG), раскраска.\n' +
          '• Задачи на деревьях: глубина, сумма поддерева, «одинаковы ли деревья».\n' +
          '• Перебор с возвратом (backtracking): расстановки ладьей, комбинации, слово в сетке букв.',
      },
    ],
    examples: [
      {
        title: 'Максимальная глубина бинарного дерева',
        statement:
          'Дано бинарное дерево в порядке обхода в ширину (0 — отсутствующий узел). Найти максимальную глубину (число узлов на самом длинном пути от корня).',
        solutions: [
          {
            lang: 'Python',
            code: `# Итеративный DFS со стеком пар (индекс, глубина)
def max_depth(vals):
    if not vals or vals[0] == 0:
        return 0
    best = 0
    stack = [(0, 1)]               # (индекс узла, глубина)
    while stack:
        i, d = stack.pop()
        best = max(best, d)
        l, r = 2 * i + 1, 2 * i + 2
        if l < len(vals) and vals[l] != 0:
            stack.append((l, d + 1))
        if r < len(vals) and vals[r] != 0:
            stack.append((r, d + 1))
    return best
# [3,9,2,0,0,7,4] -> 3`,
          },
          {
            lang: 'Java',
            code: `// Явный стек пар (index, depth) — без риска переполнения рекурсии
int maxDepth(int[] vals) {
    if (vals.length == 0 || vals[0] == 0) return 0;
    int best = 0;
    Deque<int[]> stack = new ArrayDeque<>();
    stack.push(new int[]{0, 1});   // индекс корня, глубина 1
    while (!stack.isEmpty()) {
        int[] cur = stack.pop();
        int i = cur[0], d = cur[1];
        best = Math.max(best, d);
        int l = 2 * i + 1, r = 2 * i + 2;
        if (l < vals.length && vals[l] != 0) stack.push(new int[]{l, d + 1});
        if (r < vals.length && vals[r] != 0) stack.push(new int[]{r, d + 1});
    }
    return best;
}`,
          },
          {
            lang: 'C++',
            code: `// Явный стек пар (индекс, глубина) — без риска переполнения рекурсии
int maxDepth(const vector<int>& vals) {
    if (vals.empty() || vals[0] == 0) return 0;
    int best = 0;
    stack<pair<int,int>> st;
    st.push({0, 1});                   // индекс корня, глубина 1
    while (!st.empty()) {
        auto [i, d] = st.top(); st.pop();
        best = max(best, d);
        int l = 2 * i + 1, r = 2 * i + 2;
        if (l < (int)vals.size() && vals[l] != 0) st.push({l, d + 1});
        if (r < (int)vals.size() && vals[r] != 0) st.push({r, d + 1});
    }
    return best;
}
// [3,9,2,0,0,7,4] -> 3`,
          },
          {
            lang: 'JavaScript',
            code: `// Итеративный DFS со стеком пар (индекс, глубина)
function maxDepth(vals) {
  if (!vals.length || vals[0] === 0) return 0;
  let best = 0;
  const stack = [[0, 1]];              // (индекс узла, глубина)
  while (stack.length) {
    const [i, d] = stack.pop();
    best = Math.max(best, d);
    const l = 2 * i + 1, r = 2 * i + 2;
    if (l < vals.length && vals[l] !== 0) stack.push([l, d + 1]);
    if (r < vals.length && vals[r] !== 0) stack.push([r, d + 1]);
  }
  return best;
}
// [3,9,2,0,0,7,4] -> 3`,
          },
        ],
        complexity: 'O(n) время (каждый узел один раз), O(n) память на стек.',
      },
      {
        title: 'Равенство двух деревьев',
        statement:
          'Даны два бинарных дерева (обход в ширину, 0 — отсутствующий узел). Проверить, одинаковы ли они по структуре и значениям узлов.',
        solutions: [
          {
            lang: 'Python',
            code: `# Одновременный обход двух деревьев одним стеком пар индексов
def is_same(a, b):
    stack = [(0, 0)]               # (индекс в a, индекс в b)
    while stack:
        i, j = stack.pop()
        va = a[i] if i < len(a) else 0
        vb = b[j] if j < len(b) else 0
        if va != vb:               # различие значений или структуры (0 vs число)
            return False
        if va != 0:                # оба есть — сравниваем детей
            stack.append((2*i + 1, 2*j + 1))
            stack.append((2*i + 2, 2*j + 2))
    return True`,
          },
          {
            lang: 'Java',
            code: `// Пары индексов в одном стеке; отсутствующий узел кодируем нулём
boolean isSameTree(int[] a, int[] b) {
    Deque<int[]> stack = new ArrayDeque<>();
    stack.push(new int[]{0, 0});
    while (!stack.isEmpty()) {
        int[] p = stack.pop();
        int i = p[0], j = p[1];
        int va = i < a.length ? a[i] : 0;
        int vb = j < b.length ? b[j] : 0;
        if (va != vb) return false;         // значение или структура
        if (va != 0) {
            stack.push(new int[]{2*i + 1, 2*j + 1});
            stack.push(new int[]{2*i + 2, 2*j + 2});
        }
    }
    return true;
}`,
          },
          {
            lang: 'C++',
            code: `// Пары индексов в одном стеке; отсутствующий узел кодируем нулём
bool isSameTree(const vector<int>& a, const vector<int>& b) {
    stack<pair<int,int>> st;
    st.push({0, 0});
    while (!st.empty()) {
        auto [i, j] = st.top(); st.pop();
        int va = i < (int)a.size() ? a[i] : 0;
        int vb = j < (int)b.size() ? b[j] : 0;
        if (va != vb) return false;         // значение или структура
        if (va != 0) {
            st.push({2*i + 1, 2*j + 1});
            st.push({2*i + 2, 2*j + 2});
        }
    }
    return true;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// Одновременный обход двух деревьев стеком пар индексов
function isSame(a, b) {
  const stack = [[0, 0]];              // (индекс в a, индекс в b)
  while (stack.length) {
    const [i, j] = stack.pop();
    const va = i < a.length ? a[i] : 0;
    const vb = j < b.length ? b[j] : 0;
    if (va !== vb) return false;       // различие значений или структуры
    if (va !== 0) {                    // оба узла есть — сравниваем детей
      stack.push([2*i + 1, 2*j + 1]);
      stack.push([2*i + 2, 2*j + 2]);
    }
  }
  return true;
}`,
          },
        ],
        complexity: 'O(min(n, m)) время, O(min(n, m)) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — DFS using Adjacency List', url: 'https://www.geeksforgeeks.org/depth-first-search-dfs-using-adjacency-list/' },
      { label: 'LeetCode — задачи с тегом Depth-First Search', url: 'https://leetcode.com/tag/depth-first-search/' },
    ],
  },
  {
    id: 'bfs',
    name: 'BFS',
    idea:
      'BFS (breadth-first search, поиск в ширину) разливается от стартовой вершины «волнами»: сначала посещаем всех соседей на расстоянии 1, затем на расстоянии 2 и так далее — порядок задаёт очередь (FIFO). Главная суперсила BFS: когда вершина достигнута впервые, это гарантированно кратчайший путь по числу рёбер. Время O(V + E), память O(V). На деревьях даёт обход по уровням; с метками расстояний решает задачи «минимальное число шагов/преобразований».',
    sections: [
      {
        title: 'Малоэффективное решение',
        body:
          'DFS не даёт кратчайший путь: первая найденная ветка может оказаться сколь угодно длинной. Полный перебор всех путей с выбором кратчайшего — экспоненциальная работа, а хранить все пути «на всякий случай» невозможно: их число растёт лавинообразно.',
      },
      {
        title: 'Эффективное решение',
        body:
          'BFS слоями: кладём старт в очередь; на каждом шаге достаём вершину и добавляем её непосещённых соседей с расстоянием «на один больше». Поскольку волны идут по порядку, первая волна, дошедшая до цели, и есть кратчайший путь. Каждая вершина попадает в очередь один раз → O(V + E).',
      },
      {
        title: 'Основные типы задач',
        body:
          '• Кратчайший путь в невзвешенном графе или лабиринте (минимум шагов).\n' +
          '• Обход дерева по уровням (level order).\n' +
          '• Multi-source BFS: распространение от нескольких источников («гниющие апельсины», пожар).\n' +
          '• Минимальная цепочка превращений объектов (word ladder, пазлы-пятнашки).',
      },
    ],
    examples: [
      {
        title: 'Обход дерева по уровням',
        statement:
          'Дано бинарное дерево (обход в ширину, 0 — отсутствующий узел). Вернуть значения узлов, сгруппированные по уровням (слева направо).',
        solutions: [
          {
            lang: 'Python',
            code: `# Очередь индексов; обрабатываем «слой за слоем»
def level_order(vals):
    if not vals or vals[0] == 0:
        return []
    from collections import deque
    q = deque([0])                 # очередь индексов текущего уровня
    res = []
    while q:
        level = []
        for _ in range(len(q)):    # ровно столько, сколько узлов на этом уровне
            i = q.popleft()
            level.append(vals[i])
            l, r = 2 * i + 1, 2 * i + 2
            if l < len(vals) and vals[l] != 0:
                q.append(l)
            if r < len(vals) and vals[r] != 0:
                q.append(r)
        res.append(level)
    return res
# [3,9,2,4,0,7,1] -> [[3],[9,2],[4,7,1]]`,
          },
          {
            lang: 'Java',
            code: `// Классический BFS: на каждом шаге обрабатываем весь текущий уровень
List<List<Integer>> levelOrder(int[] vals) {
    List<List<Integer>> res = new ArrayList<>();
    if (vals.length == 0 || vals[0] == 0) return res;
    Deque<Integer> q = new ArrayDeque<>();
    q.add(0);                      // индекс корня
    while (!q.isEmpty()) {
        List<Integer> level = new ArrayList<>();
        for (int s = q.size(); s > 0; s--) {   // размер уровня фиксирован
            int i = q.poll();
            level.add(vals[i]);
            int l = 2 * i + 1, r = 2 * i + 2;
            if (l < vals.length && vals[l] != 0) q.add(l);
            if (r < vals.length && vals[r] != 0) q.add(r);
        }
        res.add(level);
    }
    return res;
}`,
          },
          {
            lang: 'C++',
            code: `// Классический BFS: за один шаг обрабатываем весь текущий уровень
vector<vector<int>> levelOrder(const vector<int>& vals) {
    vector<vector<int>> res;
    if (vals.empty() || vals[0] == 0) return res;
    queue<int> q;
    q.push(0);                          // индекс корня
    while (!q.empty()) {
        vector<int> level;
        for (int s = q.size(); s > 0; s--) {   // размер уровня фиксирован
            int i = q.front(); q.pop();
            level.push_back(vals[i]);
            int l = 2 * i + 1, r = 2 * i + 2;
            if (l < (int)vals.size() && vals[l] != 0) q.push(l);
            if (r < (int)vals.size() && vals[r] != 0) q.push(r);
        }
        res.push_back(level);
    }
    return res;
}
// [3,9,2,4,0,7,1] -> [[3],[9,2],[4,7,1]]`,
          },
          {
            lang: 'JavaScript',
            code: `// Очередь индексов; обрабатываем «слой за слоем»
function levelOrder(vals) {
  if (!vals.length || vals[0] === 0) return [];
  const queue = [0];                   // FIFO-очередь индексов
  const res = [];
  while (queue.length) {
    const level = [];
    for (let s = queue.length; s > 0; s--) {  // узлы текущего уровня
      const i = queue.shift();         // берём из начала очереди
      level.push(vals[i]);
      const l = 2 * i + 1, r = 2 * i + 2;
      if (l < vals.length && vals[l] !== 0) queue.push(l);
      if (r < vals.length && vals[r] !== 0) queue.push(r);
    }
    res.push(level);
  }
  return res;
}
// [3,9,2,4,0,7,1] -> [[3],[9,2],[4,7,1]]`,
          },
        ],
        complexity: 'O(n) время, O(n) память на очередь.',
      },
      {
        title: 'Минимальная глубина дерева',
        statement:
          'Найти длину кратчайшего пути от корня до любого листа (лист — узел без детей). Дерево задано обходом в ширину, 0 — отсутствующий узел.',
        solutions: [
          {
            lang: 'Python',
            code: `# BFS останавливается на ПЕРВОМ листе — это и есть кратчайший путь
def min_depth(vals):
    if not vals or vals[0] == 0:
        return 0
    from collections import deque
    q = deque([(0, 1)])            # (индекс, глубина)
    while q:
        i, d = q.popleft()
        l, r = 2 * i + 1, 2 * i + 2
        has_left  = l < len(vals) and vals[l] != 0
        has_right = r < len(vals) and vals[r] != 0
        if not has_left and not has_right:
            return d               # первый встреченный лист — ответ
        if has_left:
            q.append((l, d + 1))
        if has_right:
            q.append((r, d + 1))
    return 0`,
          },
          {
            lang: 'Java',
            code: `// BFS с меткой глубины; первый лист в очереди — кратчайший путь
int minDepth(int[] vals) {
    if (vals.length == 0 || vals[0] == 0) return 0;
    Deque<int[]> q = new ArrayDeque<>();
    q.add(new int[]{0, 1});        // индекс, глубина
    while (!q.isEmpty()) {
        int[] cur = q.poll();
        int i = cur[0], d = cur[1];
        int l = 2 * i + 1, r = 2 * i + 2;
        boolean hl = l < vals.length && vals[l] != 0;
        boolean hr = r < vals.length && vals[r] != 0;
        if (!hl && !hr) return d;  // лист — остановка
        if (hl) q.add(new int[]{l, d + 1});
        if (hr) q.add(new int[]{r, d + 1});
    }
    return 0;
}`,
          },
          {
            lang: 'C++',
            code: `// BFS с меткой глубины; первый достигнутый лист — кратчайший путь
int minDepth(const vector<int>& vals) {
    if (vals.empty() || vals[0] == 0) return 0;
    queue<pair<int,int>> q;
    q.push({0, 1});                    // индекс, глубина
    while (!q.empty()) {
        auto [i, d] = q.front(); q.pop();
        int l = 2 * i + 1, r = 2 * i + 2;
        bool hl = l < (int)vals.size() && vals[l] != 0;
        bool hr = r < (int)vals.size() && vals[r] != 0;
        if (!hl && !hr) return d;      // первый лист — ответ
        if (hl) q.push({l, d + 1});
        if (hr) q.push({r, d + 1});
    }
    return 0;
}`,
          },
          {
            lang: 'JavaScript',
            code: `// BFS останавливается на ПЕРВОМ листе — это кратчайший путь
function minDepth(vals) {
  if (!vals.length || vals[0] === 0) return 0;
  const queue = [[0, 1]];              // (индекс, глубина)
  while (queue.length) {
    const [i, d] = queue.shift();
    const l = 2 * i + 1, r = 2 * i + 2;
    const hasLeft  = l < vals.length && vals[l] !== 0;
    const hasRight = r < vals.length && vals[r] !== 0;
    if (!hasLeft && !hasRight) return d;   // первый лист — ответ
    if (hasLeft) queue.push([l, d + 1]);
    if (hasRight) queue.push([r, d + 1]);
  }
  return 0;
}`,
          },
        ],
        complexity: 'O(n) время в худшем случае, O(n) память.',
      },
    ],
    links: [
      { label: 'GeeksforGeeks — BFS of a Graph', url: 'https://www.geeksforgeeks.org/breadth-first-search-bfs-graph/' },
      { label: 'LeetCode — задачи с тегом Breadth-First Search', url: 'https://leetcode.com/tag/breadth-first-search/' },
    ],
  },
];
