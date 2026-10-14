import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { api, LEVEL_LABELS, PATTERN_LABELS, TaskListItem, pollLlmJobs } from '../api';

export default function Dashboard() {
  const [tasks, setTasks] = useState<TaskListItem[]>([]);
  const [pattern, setPattern] = useState('');
  const [level, setLevel] = useState('');
  const [error, setError] = useState('');
  const [genBusy, setGenBusy] = useState(false);
  const [genProgress, setGenProgress] = useState('');
  const [genResult, setGenResult] = useState('');
  const [genTheme, setGenTheme] = useState('');
  const navigate = useNavigate();

  useEffect(() => {
    api<TaskListItem[]>('/api/tasks').then(setTasks).catch((e) => setError(e.message));
  }, []);

  const filtered = useMemo(
    () => tasks.filter((t) => (!pattern || t.pattern === pattern) && (!level || t.level === level)),
    [tasks, pattern, level],
  );
  const patterns = useMemo(() => Array.from(new Set(tasks.map((t) => t.pattern))).sort(), [tasks]);
  const solvedCount = tasks.filter((t) => t.solved).length;

  const generateSet = async () => {
    if (genBusy) return;
    const list = filtered.length ? filtered : tasks;
    setGenBusy(true);
    setGenResult('');
    try {
      const { job_ids } = await api<{ job_ids: number[] }>('/api/tasks/generate-set', {
        method: 'POST',
        body: JSON.stringify({ slugs: list.map((t) => t.slug), theme: genTheme.trim() || null }),
      });
      const total = job_ids.length;
      let doneCount = 0;
      setGenProgress(`Очередь: отправлено ${total} задач…`);
      const jobs = await pollLlmJobs(job_ids, (js) => {
        doneCount = js.filter((j) => j.status !== 'pending' && j.status !== 'running').length;
        setGenProgress(`Генерация: ${doneCount}/${total}…`);
      });
      const failed = jobs.filter((j) => j.status !== 'done');
      const ok = total - failed.length;
      setGenProgress('');
      setGenResult(
        failed.length === 0
          ? `Готово: новые легенды сгенерированы и сохранены для ${ok} задач.`
          : `Готово: успешно ${ok}, не удалось ${failed.length}. Неудавшиеся задачи сохранили прежнюю легенду.`,
      );
    } catch (e: any) {
      setGenProgress('');
      setGenResult(`Ошибка: ${e.message}`);
    }
    setGenBusy(false);
  };

  return (
    <div>
      <h2>Банк задач</h2>
      <p className="muted">
        Решено: {solvedCount} из {tasks.length}. Каждая задача построена на классическом паттерне —
        меняйте легенду ИИ-помощником и тренируйте суть.
      </p>
      {error && <div className="error-text">{error}</div>}
      <div className="filters">
        <select className="input" style={{ width: 280 }} value={pattern} onChange={(e) => setPattern(e.target.value)}>
          <option value="">Все паттерны</option>
          {patterns.map((p) => (
            <option key={p} value={p}>
              {PATTERN_LABELS[p] || p}
            </option>
          ))}
        </select>
        {['', 'junior', 'middle', 'senior'].map((l) => (
          <button key={l} className={`btn ghost ${level === l ? 'active' : ''}`} style={level === l ? { borderColor: 'var(--accent2)', color: 'var(--text)' } : {}} onClick={() => setLevel(l)}>
            {l === '' ? 'Все уровни' : LEVEL_LABELS[l]}
          </button>
        ))}
      </div>
      <div className="card" style={{ marginTop: 12 }}>
        <div style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
          <button className="btn green" onClick={generateSet} disabled={genBusy}>
            {genBusy ? `${genProgress || 'Генерация…'}` : '🎲 Сгенерировать новый комплект задач'}
          </button>
          <input
            className="input"
            style={{ width: 340 }}
            placeholder="Тема легенд (необязательно), напр.: космос, кухня, курьерская служба…"
            value={genTheme}
            onChange={(e) => setGenTheme(e.target.value)}
            disabled={genBusy}
          />
        </div>
        <p className="muted" style={{ fontSize: 12, margin: '8px 0 0' }}>
          ИИ придумает новые сюжетные легенды для {filtered.length ? `выбранных ${filtered.length}` : `всех ${tasks.length}`} задач —
          логика и тесты не меняются, поэтому корректность гарантирована. Легенды сохраняются только для вас (персональный комплект).
        </p>
        {genResult && <p className="muted" style={{ fontSize: 12, margin: '8px 0 0' }}>{genResult}</p>}
      </div>
      <div className="task-grid">
        {filtered.map((t) => (
          <div key={t.slug} className="card task-card" onClick={() => navigate(`/solve/${t.slug}`)}>
            <h3>
              <span>{t.title}</span>
              {t.solved && <span className="badge ok">✓ решено</span>}
            </h3>
            <div className="task-meta">
              <span className={`badge ${t.level}`}>{LEVEL_LABELS[t.level]}</span>
              <span className="badge">{PATTERN_LABELS[t.pattern] || t.pattern}</span>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}
