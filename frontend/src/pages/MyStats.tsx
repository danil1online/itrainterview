// Статистика студента: решено по паттернам/уровням и последние отправки.
import { useEffect, useMemo, useState } from 'react';
import { api, LEVEL_LABELS, PATTERN_LABELS, STATUS_LABELS, Submission, TaskListItem } from '../api';

export default function MyStats() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [subs, setSubs] = useState<Submission[]>([]);
  const [counts, setCounts] = useState<{ total: number; accepted: number } | null>(null);
  const [error, setError] = useState('');

  useEffect(() => {
    Promise.all([
      api<TaskListItem[]>('/api/tasks'),
      api<Submission[]>('/api/submissions?limit=50'), // только для таблицы «последние отправки»
      api<{ total: number; accepted: number }>('/api/submissions/count'), // точные счётчики без limit
    ])
      .then(([t, s, c]) => { setTasks(t); setSubs(s); setCounts(c); })
      .catch((e) => setError(e.message));
  }, []);

  // Агрегация «решено/всего» по паттернам (byLevel ниже — по уровням).
  const byPattern = useMemo(() => {
    const map = new Map<string, { total: number; solved: number }>();
    for (const t of tasks) {
      const cur = map.get(t.pattern) || { total: 0, solved: 0 };
      cur.total += 1;
      if (t.solved) cur.solved += 1;
      map.set(t.pattern, cur);
    }
    return Array.from(map.entries());
  }, [tasks]);

  const byLevel = useMemo(() => {
    const map = new Map<string, { total: number; solved: number }>();
    for (const t of tasks) {
      const cur = map.get(t.level) || { total: 0, solved: 0 };
      cur.total += 1;
      if (t.solved) cur.solved += 1;
      map.set(t.level, cur);
    }
    return ['junior', 'middle', 'senior'].map((l) => [l, map.get(l)] as const).filter(([, v]) => v);
  }, [tasks]);

  const solvedTotal = tasks.filter((t) => t.solved).length;
  const maxSolved = Math.max(1, ...byPattern.map(([, v]) => v.solved));

  return (
    <div>
      <h2>Мой прогресс</h2>
      {error && <div className="error-text">{error}</div>}
      <div className="stat-cards">
        <div className="card stat-card"><div className="num">{solvedTotal}</div><div className="muted">задач решено</div></div>
        <div className="card stat-card"><div className="num">{tasks.length}</div><div className="muted">всего в банке</div></div>
        <div className="card stat-card"><div className="num">{counts?.total ?? subs.length}</div><div className="muted">всего отправок</div></div>
        <div className="card stat-card"><div className="num">{counts?.accepted ?? 0}</div><div className="muted">принятых решений</div></div>
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>По уровням</h3>
        {byLevel.map(([level, v]) => (
          <div key={level} className="bar-row">
            <div className="bar-label">{LEVEL_LABELS[level]}</div>
            <div className="bar-track"><div className="bar-fill" style={{ width: `${((v as any).solved / (v as any).total) * 100}%` }} /></div>
            <span>{(v as any).solved}/{(v as any).total}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>По паттернам</h3>
        {byPattern.map(([p, v]) => (
          <div key={p} className="bar-row">
            <div className="bar-label">{PATTERN_LABELS[p] || p}</div>
            <div className="bar-track"><div className="bar-fill" style={{ width: `${(v.solved / maxSolved) * 100}%` }} /></div>
            <span>{v.solved}/{v.total}</span>
          </div>
        ))}
      </div>

      <div className="card">
        <h3 style={{ marginTop: 0 }}>Последние отправки</h3>
        <table className="grid">
          <thead><tr><th>Задача</th><th>Язык</th><th>Статус</th><th>Тесты</th><th>Дата</th></tr></thead>
          <tbody>
            {subs.slice(0, 20).map((s) => (
              <tr key={s.id}>
                <td>{tasks.find((t) => t.slug === s.task_slug)?.title || `#${s.task_id}`}</td>
                <td>{s.language}</td>
                <td><span className={`badge ${s.status === 'accepted' ? 'ok' : 'fail'}`}>{STATUS_LABELS[s.status] || s.status}</span></td>
                <td>{s.passed_count}/{s.total_count}</td>
                <td className="muted">{new Date(s.created_at).toLocaleString('ru-RU')}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}
