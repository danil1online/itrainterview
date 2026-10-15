// Список литературы по алгоритмам (PDF-ссылки) для страницы «Теория».
export interface LiteratureItem {
  label: string;
  url: string;
}

export const LITERATURE: LiteratureItem[] = [
  {
    label: 'Кнут Д.Э. Искусство программирования, том 1. Основные алгоритмы, 3-е изд.: Пер. с англ. — М.: ООО «И.Д. Вильямс», 2018. — 720 с.',
    url: 'http://lib.ysu.am/open_books/416247_1.pdf',
  },
  {
    label: 'Клейнберг Дж., Тардос Е. К48 Алгоритмы: разработка и применение. Классика Computers Science / Пер. с англ. Е. Матвеева. — СПб.: Питер, 2016. — 800 с.',
    url: 'http://old.math.nsc.ru/LBRT/k5/OR-MMF/Kleinberg_Tardoc_algoritmy_razrabotka_i_primenenie.pdf',
  },
  {
    label: 'Дасгупта С. и др. Алгоритмы / С. Дасгупта, Х. Пападимитриу, У. Вазирани; Пер. с англ. под ред. А. Шеня. — М.: МЦНМО, 2014. — 320 с.',
    url: 'https://alexanderskulikov.github.io/files/algorithms_printable.pdf',
  },
  {
    label: 'Т. Кормен, Ч. Лейзерсон, Р. Ривест, К. Штайн. Алгоритмы: построение и анализ',
    url: 'http://www.r-5.org/files/books/computers/algo-list/common/Cormen_Leiserson_Rivest_Stein-Introduction_to_Algorithms-RU.pdf',
  },
  {
    label: 'Ахмад Имран. 40 алгоритмов, которые должен знать каждый программист на Python. — СПб.: Питер, 2023. — 368 с.',
    url: 'https://library.tsilikin.ru/Техника/Программирование/Python/40%20алгоритмов.pdf',
  },
  {
    label: 'Фофанов О.Б. Алгоритмы и структуры данных: учебное пособие / Томский политехнический университет. — Томск: Изд-во Томского политехнического университета, 2014. — 126 с.',
    url: 'https://portal.tpu.ru/SHARED/o/OFOFANO/work/Tab2/up.pdf',
  },
];
