/**
 * Админ-панель: пользователи, задачи, вайб-задачи, результаты, настройки (роуты /admin/*).
 * Экспорт задачи как community-вклада: перед генерацией файла бэкенд проверяет эталонное решение в песочнице.
 */
import { FormEvent, useCallback, useEffect, useState } from 'react';
import { Route, Routes, useLocation, useNavigate } from 'react-router-dom';
import { api, AdminUser, LEVEL_LABELS, PATTERN_LABELS, STATUS_LABELS, VibeAdminTask, downloadFile, pollLlmJob } from '../api';
import { useAuth } from '../auth';

const TABS = [
  { path: '/admin', label: 'Пользователи' },
  { path: '/admin/tasks', label: 'Задачи' },
  { path: '/admin/vibe', label: 'Вайб-задачи' },
  { path: '/admin/results', label: 'Результаты' },
  { path: '/admin/settings', label: 'Настройки' },
];

export default function Admin() {
  const navigate = useNavigate();
  const location = useLocation();
  return (
    <div>
      <h2>Администрирование</h2>
      <div className="admin-tabs">
        {TABS.map((t) => (
          <button key={t.path} className={`btn ghost ${location.pathname === t.path ? 'active' : ''}`} style={location.pathname === t.path ? { borderColor: 'var(--accent2)', color: 'var(--text)' } : {}} onClick={() => navigate(t.path)}>
            {t.label}
          </button>
        ))}
      </div>
      <Routes>
        <Route path="/" element={<UsersTab />} />
        <Route path="/tasks" element={<TasksTab />} />
        <Route path="/vibe" element={<VibeTasksTab />} />
        <Route path="/results" element={<ResultsTab />} />
        <Route path="/settings" element={<SettingsTab />} />
      </Routes>
    </div>
  );
}

// Вкладка «Пользователи»: поиск, смена роли/блокировка, сброс пароля.
function UsersTab() {
  const [users, setUsers] = useState<AdminUser[]>([]);
  const [q, setQ] = useState('');
  const [error, setError] = useState('');
  const load = useCallback(() => api<AdminUser[]>(`/api/admin/users${q ? `?q=${encodeURIComponent(q)}` : ''}`).then(setUsers).catch((e) => setError(e.message)), [q]);
  // debounce: не шлём запрос на каждый символ поиска
  useEffect(() => {
    const t = setTimeout(load, 300);
    return () => clearTimeout(t);
  }, [load]);

  const patch = async (id: number, body: object) => { await api(`/api/admin/users/${id}`, { method: 'PATCH', body: JSON.stringify(body) }); load(); };
  const resetPassword = async (id: number) => {
    const pw = prompt('Новый пароль (минимум 6 символов):');
    if (!pw) return;
    // пароль в теле запроса, а не в URL — не попадает в историю/логи
    try { await api(`/api/admin/users/${id}/reset_password`, { method: 'POST', body: JSON.stringify({ new_password: pw }) }); alert('Пароль обновлён'); } catch (e: any) { alert(e.message); }
  };

  return (
    <div className="card">
      <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
        <input className="input" style={{ maxWidth: 300 }} placeholder="Поиск по имени/email…" value={q} onChange={(e) => setQ(e.target.value)} />
      </div>
      {error && <div className="error-text">{error}</div>}
      <table className="grid">
        <thead><tr><th>Пользователь</th><th>Email</th><th>Роль</th><th>Статус</th><th>Отправок</th><th>Решено</th><th /></tr></thead>
        <tbody>
          {users.map((u) => (
            <tr key={u.id}>
              <td>{u.username}</td>
              <td className="muted">{u.email}</td>
              <td>
                <select className="input" style={{ padding: '2px 6px', width: 'auto' }} value={u.role} onChange={(e) => patch(u.id, { role: e.target.value })}>
                  <option value="student">student</option>
                  <option value="admin">admin</option>
                </select>
              </td>
              <td>{u.is_active ? <span className="badge ok">активен</span> : <span className="badge fail">заблокирован</span>}</td>
              <td>{u.submissions}</td>
              <td>{u.solved_tasks}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="btn ghost small" onClick={() => patch(u.id, { is_active: !u.is_active })}>{u.is_active ? 'Блок' : 'Разблок'}</button>{' '}
                <button className="btn ghost small" onClick={() => resetPassword(u.id)}>Пароль</button>
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface AdminTask {
  id: number; slug: string; title: string; legend: string; pattern: string; level: string;
  hints: string[]; tests: any[]; reference_solution: string; is_active: boolean;
}

// Вкладка «Задачи»: список + форма редактирования (тесты — JSON), ИИ-генерация легенды через LLM-очередь, community-экспорт.
function TasksTab() {
  const { user } = useAuth();
  const [tasks, setTasks] = useState<AdminTask[]>([]);
  const [editing, setEditing] = useState<AdminTask | null>(null);
  const [jsonText, setJsonText] = useState('');
  const [error, setError] = useState('');
  // Экспорт задачи как community-вклада
  const [exporting, setExporting] = useState<AdminTask | null>(null);
  const [expAuthor, setExpAuthor] = useState('');
  const [expBusy, setExpBusy] = useState(false);
  const [expError, setExpError] = useState('');
  const [expResult, setExpResult] = useState<{ filename: string; content: string; instructions: string } | null>(null);

  const load = useCallback(() => api<AdminTask[]>('/api/admin/tasks').then(setTasks).catch((e) => setError(e.message)), []);
  useEffect(() => { load(); }, [load]);

  const save = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    if (!editing) return;
    try {
      JSON.parse(jsonText);
    } catch { setError('Тесты: некорректный JSON'); return; }
    const body = { ...editing, tests: JSON.parse(jsonText) };
    try {
      if (editing.id === 0) await api('/api/admin/tasks', { method: 'POST', body: JSON.stringify(body) });
      else await api(`/api/admin/tasks/${editing.id}`, { method: 'PUT', body: JSON.stringify(body) });
      setEditing(null); load();
    } catch (err: any) { setError(err.message); }
  };

  // Просит LLM переписать легенду: job в очереди, ждём поллингом и перезагружаем список.
  const retitle = async (t: AdminTask) => {
    try {
      const { job_id } = await api<{ job_id: number }>(`/api/admin/tasks/${t.id}/retitle`, { method: 'POST' });
      alert('Легенда отправлена в очередь генерации…');
      const job = await pollLlmJob(job_id);
      if (job.status === 'done') { alert('Легенда обновлена ИИ'); load(); }
      else alert(`Генерация не удалась: ${job.error || job.status}`);
    } catch (e: any) { alert(e.message); }
  };

  const openExport = (t: AdminTask) => {
    setExporting(t);
    setExpAuthor(user?.username || '');
    setExpError('');
    setExpResult(null);
  };

  // Генерация community-файла: сервер сначала прогоняет эталон по всем тестам задачи.
  const runExport = async () => {
    if (!exporting) return;
    setExpBusy(true);
    setExpError('');
    try {
      const res = await api<{ filename: string; content: string; instructions: string }>(
        `/api/admin/tasks/${exporting.id}/export-community`,
        { method: 'POST', body: JSON.stringify({ author: expAuthor.trim() || user?.username || 'admin' }) },
      );
      setExpResult(res);
    } catch (e: any) {
      setExpError(e.message);
    } finally {
      setExpBusy(false);
    }
  };

  const downloadExport = () => {
    if (!expResult) return;
    const blob = new Blob([expResult.content], { type: 'text/x-python;charset=utf-8' });
    const url = URL.createObjectURL(blob);
    const aEl = document.createElement('a');
    aEl.href = url;
    aEl.download = expResult.filename;
    aEl.click();
    URL.revokeObjectURL(url);
  };

  const copyExport = async () => {
    if (!expResult) return;
    try { await navigator.clipboard.writeText(expResult.content); alert('Скопировано в буфер обмена'); }
    catch { alert('Не удалось скопировать — выделите код вручную'); }
  };

  if (exporting) {
    return (
      <div className="card">
        <h3>Community-вклад — {exporting.slug}</h3>
        <p className="muted" style={{ marginTop: 4 }}>
          Сгенерируем файл <code>backend/app/seed/bank_community_*.py</code> для PR в репозиторий.
          Перед этим эталонное решение прогонится в песочнице по всем тестам задачи.
        </p>
        <div className="form-row">
          <label>Автор вклада (имя, которое будет в файле)</label>
          <input className="input" value={expAuthor} onChange={(e) => setExpAuthor(e.target.value)} placeholder={user?.username || 'admin'} />
        </div>
        {expError && <div className="error-text">{expError}</div>}
        {!expResult && (
          <button className="btn green" disabled={expBusy} onClick={runExport}>
            {expBusy ? 'Проверяем эталон в песочнице…' : 'Проверить и сгенерировать'}
          </button>
        )}
        {expResult && (
          <>
            <div className="form-row">
              <label>Файл: {expResult.filename}</label>
              <pre className="code-block" style={{ fontSize: 12, maxHeight: 320 }}>{expResult.content}</pre>
              <button className="btn green small" onClick={downloadExport}>⬇ Скачать .py</button>{' '}
              <button className="btn ghost small" onClick={copyExport}>Копировать код</button>
            </div>
            <div className="form-row">
              <label>Как предложить в репозиторий</label>
              <pre className="code-block" style={{ fontSize: 12, whiteSpace: 'pre-wrap' }}>{expResult.instructions}</pre>
            </div>
          </>
        )}
        <button className="btn ghost" onClick={() => setExporting(null)}>Закрыть</button>
      </div>
    );
  }

  if (editing) {
    return (
      <form className="card" onSubmit={save}>
        <h3>{editing.id === 0 ? 'Новая задача' : `Задача #${editing.id}`}</h3>
        <div className="form-row">
          <label>Адрес задачи (slug)</label>
          <input className="input" value={editing.slug} onChange={(e) => setEditing({ ...editing, slug: e.target.value })} required />
          <p className="muted" style={{ fontSize: 12, margin: '4px 0 0' }}>
            Латиницей, цифры и дефисы, без пробелов (например two-sum-ii). Используется в URL задачи: /solve/&lt;slug&gt;. После публикации менять нежелательно.
          </p>
        </div>
        <div className="form-row"><label>Заголовок</label><input className="input" value={editing.title} onChange={(e) => setEditing({ ...editing, title: e.target.value })} required /></div>
        <div className="form-row">
          <label>Легенда (условие задачи)</label>
          <textarea className="input" rows={8} value={editing.legend} onChange={(e) => setEditing({ ...editing, legend: e.target.value })} required />
          <p className="muted" style={{ fontSize: 12, margin: '4px 0 0' }}>
            Сюжет + разделы «Формат ввода» и «Формат вывода». Примеры НЕ пиши — они показываются автоматически из тестов с sample: true.
          </p>
        </div>
        <div style={{ display: 'flex', gap: 10 }}>
          <div className="form-row" style={{ flex: 1 }}><label>Паттерн</label><input className="input" value={editing.pattern} onChange={(e) => setEditing({ ...editing, pattern: e.target.value })} required /></div>
          <div className="form-row" style={{ flex: 1 }}>
            <label>Уровень</label>
            <select className="input" value={editing.level} onChange={(e) => setEditing({ ...editing, level: e.target.value })}>
              <option value="junior">junior</option><option value="middle">middle</option><option value="senior">senior</option>
            </select>
          </div>
        </div>
        <div className="form-row">
          <label>Тесты (JSON)</label>
          <textarea className="input" rows={10} value={jsonText} onChange={(e) => setJsonText(e.target.value)} />
          <p className="muted" style={{ fontSize: 12, margin: '4px 0 0' }}>
            Массив объектов. Поля: <b>name</b> — имя теста (латиницей); <b>stdin</b> — входные данные (переносы строк через \n);{' '}
            <b>expected_stdout</b> — ожидаемый вывод; <b>sample: true</b> — пример из условия, показывается студенту (обычно один). Пример:
          </p>
          <pre className="code-block" style={{ fontSize: 12, marginTop: 6 }}>
{`[
  {"name": "sample", "stdin": "9\\n1 8 6 2 5 4 8 3 7\\n49", "expected_stdout": "49", "sample": true},
  {"name": "t2", "stdin": "5\\n1 2 3 4 5\\n7", "expected_stdout": "3 4", "sample": false}
]`}
          </pre>
        </div>
        {error && <div className="error-text">{error}</div>}
        <button className="btn green" type="submit">Сохранить</button>{' '}
        <button className="btn ghost" type="button" onClick={() => setEditing(null)}>Отмена</button>
      </form>
    );
  }

  return (
    <div className="card">
      <button className="btn green" style={{ marginBottom: 12 }} onClick={() => { setEditing({ id: 0, slug: '', title: '', legend: '', pattern: 'dp', level: 'junior', hints: [], tests: [{ name: 'sample', stdin: '', expected_stdout: '', sample: true }], reference_solution: '', is_active: true }); setJsonText(JSON.stringify([{ name: 'sample', stdin: '', expected_stdout: '', sample: true }], null, 2)); }}>
        + Новая задача
      </button>
      {error && <div className="error-text">{error}</div>}
      <table className="grid">
        <thead><tr><th>Адрес (slug)</th><th>Заголовок</th><th>Паттерн</th><th>Уровень</th><th>Тестов</th><th>Статус</th><th /></tr></thead>
        <tbody>
          {tasks.map((t) => (
            <tr key={t.id}>
              <td>{t.slug}</td>
              <td>{t.title}</td>
              <td className="muted">{PATTERN_LABELS[t.pattern] || t.pattern}</td>
              <td><span className={`badge ${t.level}`}>{LEVEL_LABELS[t.level]}</span></td>
              <td>{t.tests.length}</td>
              <td>{t.is_active ? <span className="badge ok">активна</span> : <span className="badge fail">скрыта</span>}</td>
              <td style={{ whiteSpace: 'nowrap' }}>
                <button className="btn ghost small" onClick={() => { setEditing(t); setJsonText(JSON.stringify(t.tests, null, 2)); }}>Ред.</button>{' '}
                <button className="btn ghost small" onClick={() => retitle(t)}>ИИ-легенда</button>{' '}
                <button className="btn ghost small" title="Экспорт задачи как community-файла для PR в репозиторий" onClick={() => openExport(t)}>📤 Вклад</button>{' '}
                {t.is_active && <button className="btn danger small" onClick={async () => { await api(`/api/admin/tasks/${t.id}`, { method: 'DELETE' }); load(); }}>Скрыть</button>}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

interface ResultRow {
  id: number; username: string; task_slug: string; level: string; pattern: string;
  language: string; status: string; passed_count: number; total_count: number; time_ms: number; created_at: string;
}

// Вкладка «Результаты»: все отправки с фильтром по статусу; клик по строке — детали (код + разбор ИИ).
function ResultsTab() {
  const [rows, setRows] = useState<ResultRow[]>([]);
  const [status, setStatus] = useState('');
  const [detail, setDetail] = useState<any>(null);
  const [error, setError] = useState('');

  const load = useCallback(() => api<ResultRow[]>(`/api/admin/results${status ? `?status=${status}` : ''}`).then(setRows).catch((e) => setError(e.message)), [status]);
  useEffect(() => { load(); }, [load]);

  return (
    <div className="card">
      <div style={{ display: 'flex', gap: 10, marginBottom: 12 }}>
        <select className="input" style={{ width: 240 }} value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">Все статусы</option>
          {Object.entries(STATUS_LABELS).map(([k, v]) => <option key={k} value={k}>{v}</option>)}
        </select>
        <button className="btn ghost" onClick={() => downloadFile('/api/admin/export/submissions.csv', 'submissions.csv').catch((e) => setError(e.message))}>⬇ CSV</button>
      </div>
      {error && <div className="error-text">{error}</div>}
      <table className="grid">
        <thead><tr><th>Студент</th><th>Задача</th><th>Язык</th><th>Статус</th><th>Тесты</th><th>мс</th><th>Дата</th></tr></thead>
        <tbody>
          {rows.map((r) => (
            <tr key={r.id} style={{ cursor: 'pointer' }} onClick={async () => setDetail(await api(`/api/admin/results/${r.id}`))}>
              <td>{r.username}</td>
              <td>{r.task_slug}</td>
              <td>{r.language}</td>
              <td><span className={`badge ${r.status === 'accepted' ? 'ok' : 'fail'}`}>{STATUS_LABELS[r.status] || r.status}</span></td>
              <td>{r.passed_count}/{r.total_count}</td>
              <td className="muted">{r.time_ms}</td>
              <td className="muted">{new Date(r.created_at).toLocaleString('ru-RU')}</td>
            </tr>
          ))}
        </tbody>
      </table>
      {detail && (
        <div style={{ marginTop: 16 }}>
          <h3>#{detail.id} — {detail.username} / {detail.task}</h3>
          {detail.ai_feedback && <div className="feedback-box" style={{ marginBottom: 12 }}>{detail.ai_feedback}</div>}
          <pre className="code-block">{detail.code}</pre>
          <button className="btn ghost small" onClick={() => setDetail(null)}>Закрыть</button>
        </div>
      )}
    </div>
  );
}

// Настройки LLM и песочницы; применяются на бэкенде без перезапуска.
function SettingsTab() {
  const [values, setValues] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState('');
  const [error, setError] = useState('');

  useEffect(() => { api<Record<string, string>>('/api/admin/settings').then(setValues).catch((e) => setError(e.message)); }, []);

  const save = async (e: FormEvent) => {
    e.preventDefault(); setError(''); setMsg('');
    try {
      await api('/api/admin/settings', { method: 'PUT', body: JSON.stringify({ values }) });
      setMsg('Сохранено — применяется без перезапуска');
    } catch (err: any) { setError(err.message); }
  };

  const FIELDS: Array<[string, string, string]> = [
    ['llm_base_url', 'LLM: OpenAI-совместимый URL', 'http://192.168.2.83:8080/v1'],
    ['llm_model', 'LLM: имя модели (пусто = автоопределение)', 'qwen2.5-3b-instruct-q4_k_m.gguf'],
    ['llm_api_key', 'LLM: API-ключ (если нужен)', ''],
    ['llm_max_concurrent', 'LLM-очередь: параллельных запросов к модели (1..32)', '1'],
    ['sandbox_timeout_sec', 'Песочница: таймаут, сек (1..60)', '5'],
    ['sandbox_memory_mb', 'Песочница: память, МБ (64..2048)', '256'],
    ['sandbox_max_concurrent', 'Песочница: одновременных контейнеров (пусто = min(CPU, 8))', ''],
  ];

  return (
    <form className="card" style={{ maxWidth: 640 }} onSubmit={save}>
      {FIELDS.map(([key, label, ph]) => (
        <div className="form-row" key={key}>
          <label>{label}</label>
          <input className="input" placeholder={ph} value={values[key] ?? ''} onChange={(e) => setValues({ ...values, [key]: e.target.value })} />
        </div>
      ))}
      <div className="form-row">
        <label>Разрешить самостоятельную регистрацию</label>
        <select className="input" value={values['allow_self_registration'] ?? 'true'} onChange={(e) => setValues({ ...values, allow_self_registration: e.target.value })}>
          <option value="true">да</option>
          <option value="false">нет (только админ)</option>
        </select>
      </div>
      {error && <div className="error-text">{error}</div>}
      {msg && <div className="ok-text">{msg}</div>}
      <button className="btn green" type="submit">Сохранить настройки</button>
    </form>
  );
}


// ---------- Вайб-задачи ----------

const VIBE_TYPES: Record<string, string> = {
  bugfix: 'Исправление бага',
  tests: 'Юнит-тесты (мутанты)',
  refactor: 'Рефакторинг',
  contract: 'Генерация по контракту',
};

const EMPTY_VIBE: Omit<VibeAdminTask, 'id'> = {
  slug: '', task_type: 'bugfix', title: '', description_md: '', initial_code: '',
  hidden_tests: [], reference_solution: '', mutants: [], min_mutants_caught: 0, enabled: true,
};

// CRUD вайб-задач: скрытые тесты/мутанты — JSON, эталон проверяется в песочнице при сохранении.
function VibeTasksTab() {
  const [tasks, setTasks] = useState<VibeAdminTask[]>([]);
  const [editing, setEditing] = useState<(Omit<VibeAdminTask, 'id'> & { id?: number }) | null>(null);
  const [testsText, setTestsText] = useState('[]');
  const [mutantsText, setMutantsText] = useState('[]');
  const [error, setError] = useState('');
  const [msg, setMsg] = useState('');

  const load = useCallback(() => {
    api<VibeAdminTask[]>('/api/admin/vibe-tasks').then(setTasks).catch((e) => setError(e.message));
  }, []);
  useEffect(() => { load(); }, [load]);

  const startEdit = (t: VibeAdminTask | null) => {
    setError('');
    setMsg('');
    const src = t || EMPTY_VIBE;
    setEditing({ ...src });
    setTestsText(JSON.stringify(src.hidden_tests, null, 2));
    setMutantsText(JSON.stringify(src.mutants, null, 2));
  };

  const save = async () => {
    if (!editing) return;
    setError('');
    setMsg('');
    let hidden_tests: any[];
    let mutants: any[];
    try {
      hidden_tests = JSON.parse(testsText);
      mutants = JSON.parse(mutantsText);
    } catch {
      setError('hidden_tests или mutants — невалидный JSON');
      return;
    }
    const body = { ...editing, hidden_tests, mutants };
    try {
      if (editing.id) {
        await api(`/api/admin/vibe-tasks/${editing.id}`, { method: 'PATCH', body: JSON.stringify(body) });
      } else {
        await api('/api/admin/vibe-tasks', { method: 'POST', body: JSON.stringify(body) });
      }
      setMsg('Сохранено (эталон проверен в песочнице)');
      setEditing(null);
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const remove = async (t: VibeAdminTask) => {
    if (!confirm(`Удалить вайб-задачу «${t.title}»?`)) return;
    try {
      await api(`/api/admin/vibe-tasks/${t.id}`, { method: 'DELETE' });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const toggle = async (t: VibeAdminTask) => {
    try {
      await api(`/api/admin/vibe-tasks/${t.id}`, { method: 'PATCH', body: JSON.stringify({ ...t, enabled: !t.enabled }) });
      load();
    } catch (e: any) {
      setError(e.message);
    }
  };

  const set = (patch: Partial<Omit<VibeAdminTask, 'id'>>) => setEditing((e) => (e ? { ...e, ...patch } : e));
  const mono = { fontFamily: 'ui-monospace, Menlo, Consolas, monospace', fontSize: 12 };

  return (
    <div>
      <div className="card">
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <h3 style={{ margin: 0, flex: 1 }}>Задачи тренажёра «Вайб-кодинг»</h3>
          <button className="btn" onClick={() => startEdit(null)}>+ Новая задача</button>
        </div>
        {error && <div className="error-text">{error}</div>}
        {msg && <div className="ok-text">{msg}</div>}
        <table className="grid" style={{ marginTop: 10 }}>
          <thead>
            <tr><th>Slug</th><th>Тип</th><th>Название</th><th>Тестов</th><th>Мутантов</th><th>Статус</th><th></th></tr>
          </thead>
          <tbody>
            {tasks.map((t) => (
              <tr key={t.id}>
                <td>{t.slug}</td>
                <td>{VIBE_TYPES[t.task_type] || t.task_type}</td>
                <td>{t.title}</td>
                <td>{t.hidden_tests.length}</td>
                <td>{t.mutants.length} (мин {t.min_mutants_caught})</td>
                <td>{t.enabled ? <span className="badge ok">включена</span> : <span className="badge">выключена</span>}</td>
                <td style={{ whiteSpace: 'nowrap' }}>
                  <button className="btn ghost small" onClick={() => startEdit(t)}>Ред.</button>{' '}
                  <button className="btn ghost small" onClick={() => toggle(t)}>{t.enabled ? 'Отключить' : 'Включить'}</button>{' '}
                  <button className="btn danger small" onClick={() => remove(t)}>✕</button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {editing && (
        <form
          className="card"
          onSubmit={(e) => {
            e.preventDefault();
            save();
          }}
        >
          <h3 style={{ marginTop: 0 }}>{editing.id ? `Правка: ${editing.slug}` : 'Новая вайб-задача'}</h3>
          <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
            <div className="form-row" style={{ flex: 2, minWidth: 200 }}>
              <label>Slug (латиница, дефисы)</label>
              <input className="input" value={editing.slug} onChange={(e) => set({ slug: e.target.value })} disabled={!!editing.id} />
            </div>
            <div className="form-row" style={{ flex: 1, minWidth: 160 }}>
              <label>Тип</label>
              <select className="input" value={editing.task_type} onChange={(e) => set({ task_type: e.target.value })}>
                {Object.entries(VIBE_TYPES).map(([v, l]) => <option key={v} value={v}>{l}</option>)}
              </select>
            </div>
            <div className="form-row" style={{ flex: 2, minWidth: 200 }}>
              <label>Название</label>
              <input className="input" value={editing.title} onChange={(e) => set({ title: e.target.value })} />
            </div>
          </div>
          <div className="form-row">
            <label>Описание (поддерживается **жирный**)</label>
            <textarea className="input" rows={4} value={editing.description_md} onChange={(e) => set({ description_md: e.target.value })} />
          </div>
          <div className="form-row">
            <label>Стартовый код студента {editing.task_type === 'tests' && '(для типа tests обязателен маркер «# === ВАШИ ТЕСТЫ НИЖЕ»)'} </label>
            <textarea className="input" rows={8} style={mono} value={editing.initial_code} onChange={(e) => set({ initial_code: e.target.value })} />
          </div>
          {editing.task_type !== 'tests' ? (
            <>
              <div className="form-row">
                <label>Скрытые тесты JSON: [{'{'}name, code — assert-кейс{'}'}]</label>
                <textarea className="input" rows={6} style={mono} value={testsText} onChange={(e) => setTestsText(e.target.value)} />
              </div>
              <div className="form-row">
                <label>Эталонное решение (проверяется в песочнице при сохранении)</label>
                <textarea className="input" rows={8} style={mono} value={editing.reference_solution} onChange={(e) => set({ reference_solution: e.target.value })} />
              </div>
            </>
          ) : (
            <>
              <div className="form-row">
                <label>Мутанты JSON: [{'{'}name, code — изменённый эталон{'}'}]</label>
                <textarea className="input" rows={8} style={mono} value={mutantsText} onChange={(e) => setMutantsText(e.target.value)} />
              </div>
              <div className="form-row" style={{ maxWidth: 220 }}>
                <label>Минимум пойманных мутантов</label>
                <input className="input" type="number" min={0} max={20} value={editing.min_mutants_caught}
                  onChange={(e) => set({ min_mutants_caught: parseInt(e.target.value || '0', 10) })} />
              </div>
            </>
          )}
          <label className="check-item" style={{ marginBottom: 10 }}>
            <input type="checkbox" checked={editing.enabled} onChange={(e) => set({ enabled: e.target.checked })} /> задача включена
          </label>
          <div style={{ display: 'flex', gap: 8 }}>
            <button className="btn green" type="submit">Сохранить</button>
            <button className="btn ghost" type="button" onClick={() => setEditing(null)}>Отмена</button>
          </div>
        </form>
      )}
    </div>
  );
}
