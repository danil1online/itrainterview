import { useEffect, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import { api, pollLlmJob, VibeRunResult, VibeSession, VibeTaskListItem } from '../api';

const TYPE_META: Record<string, { label: string; color: string }> = {
  bugfix: { label: 'Исправление бага', color: '#e5484d' },
  tests: { label: 'Юнит-тесты', color: '#3e63dd' },
  refactor: { label: 'Рефакторинг', color: '#30a46c' },
  contract: { label: 'По контракту', color: '#f76b15' },
};

function TypeBadge({ type }: { type: string }) {
  const m = TYPE_META[type] || { label: type, color: '#888' };
  return (
    <span className="badge" style={{ background: m.color, color: '#fff', border: 'none' }}>
      {m.label}
    </span>
  );
}

function MdText({ text }: { text: string }) {
  return (
    <div style={{ whiteSpace: 'pre-wrap', fontSize: 13, lineHeight: 1.5 }}>
      {text.split(/(\*\*[^*]+\*\*)/g).map((part, i) =>
        part.startsWith('**') && part.endsWith('**') ? <b key={i}>{part.slice(2, -2)}</b> : <span key={i}>{part}</span>,
      )}
    </div>
  );
}

export default function VibeCoding() {
  const [tasks, setTasks] = useState<VibeTaskListItem[]>([]);
  const [session, setSession] = useState<VibeSession | null>(null);
  const [error, setError] = useState('');
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    api<VibeTaskListItem[]>('/api/vibe/tasks').then(setTasks).catch((e) => setError(e.message));
  }, []);

  const open = async (taskId: number) => {
    setLoading(true);
    setError('');
    try {
      setSession(await api<VibeSession>(`/api/vibe/tasks/${taskId}/session`, { method: 'POST' }));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setLoading(false);
    }
  };

  if (session) {
    return (
      <SessionView
        session={session}
        onBack={() => {
          setSession(null);
          api<VibeTaskListItem[]>('/api/vibe/tasks').then(setTasks).catch(() => undefined);
        }}
      />
    );
  }

  const done = tasks.filter((t) => t.status === 'passed').length;

  return (
    <div>
      <h2 style={{ marginTop: 0 }}>Вайб-Кодинг</h2>
      <div className="card" style={{ marginBottom: 14 }}>
        <p style={{ margin: 0 }}>
          Тренажёр работы с <b>компактной моделью ИИ</b> (Qwen 3B, 32k контекста). Модель намеренно
          «слабая» и <b>не видит ваш редактор</b> — работает только тот код, который вы сами вставите в диалог.
          Тренируются три навыка: <b>декомпозиция</b> (задачи по 5–30 строк), <b>точечный контекст</b>
          (слать модели только нужное) и <b>контроль галлюцинаций</b> (ревью каждого ответа).
        </p>
        <p className="muted" style={{ margin: '8px 0 0', fontSize: 12 }}>
          Пройдено: {done} из {tasks.length}. Баллы: 50 за зелёные тесты + итерации диалога + качество промптов + гигиена кода.
        </p>
      </div>

      {error && <div className="error-text">{error}</div>}

      {tasks.map((t) => (
        <div key={t.id} className="card" style={{ display: 'flex', alignItems: 'center', gap: 12, flexWrap: 'wrap' }}>
          <TypeBadge type={t.task_type} />
          <div style={{ flex: 1, minWidth: 200 }}>
            <b>{t.title}</b>
            {t.status === 'passed' && <span className="badge ok" style={{ marginLeft: 8 }}>зачёт · {t.score} баллов</span>}
            {t.status === 'in_progress' && <span className="badge" style={{ marginLeft: 8 }}>в процессе</span>}
          </div>
          <button className="btn" disabled={loading} onClick={() => open(t.id)}>
            {t.status === 'passed' ? 'Открыть' : t.status === 'in_progress' ? 'Продолжить' : 'Начать'}
          </button>
        </div>
      ))}
    </div>
  );
}

function SessionView({ session, onBack }: { session: VibeSession; onBack: () => void }) {
  const [code, setCode] = useState(session.code);
  const [messages, setMessages] = useState<{ role: string; content: string }[]>(session.messages || []);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [runBusy, setRunBusy] = useState(false);
  const [result, setResult] = useState<VibeRunResult | null>(session.last_run ? { ...session.last_run } as VibeRunResult : null);
  const [error, setError] = useState('');
  const [queueInfo, setQueueInfo] = useState('');
  const [prompts, setPrompts] = useState(session.prompts_count || 0);
  const [passed, setPassed] = useState(session.status === 'passed');
  const [score, setScore] = useState<number | null>(session.score);
  const endRef = useRef<HTMLDivElement>(null);
  const firstCode = useRef(true);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  // автосохранение кода (debounce), пока задача не решена
  useEffect(() => {
    if (firstCode.current) {
      firstCode.current = false;
      return;
    }
    if (passed) return;
    const t = setTimeout(() => {
      api(`/api/vibe/sessions/${session.id}/code`, { method: 'PUT', body: JSON.stringify({ code }) }).catch(() => undefined);
    }, 1200);
    return () => clearTimeout(t);
  }, [code, passed, session.id]);

  const queueLine = (j: { status: string; position: number }) =>
    j.status === 'running' ? 'Модель думает…' : `Модель занята — вы №${j.position + 1} в очереди`;

  const send = async () => {
    const text = input.trim();
    if (!text || busy || passed) return;
    setBusy(true);
    setError('');
    setMessages((m) => [...m, { role: 'user', content: text }]);
    setInput('');
    try {
      const res = await api<{ job_id: number; prompts_count: number }>(`/api/vibe/sessions/${session.id}/chat`, {
        method: 'POST',
        body: JSON.stringify({ content: text }),
      });
      setPrompts(res.prompts_count);
      const job = await pollLlmJob(res.job_id, (j) => setQueueInfo(queueLine(j)));
      if (job.status !== 'done' || !job.result) throw new Error(job.error || 'Модель не ответила');
      setMessages((m) => [...m, { role: 'assistant', content: job.result as string }]);
    } catch (e: any) {
      setError(e.message);
      setMessages((m) => m.slice(0, -1));
    } finally {
      setBusy(false);
      setQueueInfo('');
    }
  };

  const run = async () => {
    setRunBusy(true);
    setError('');
    try {
      const res = await api<VibeRunResult>(`/api/vibe/sessions/${session.id}/run`, {
        method: 'POST',
        body: JSON.stringify({ code }),
      });
      setResult(res);
      if (res.passed) setPassed(true);
      setScore((s) => Math.max(s || 0, res.score));
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRunBusy(false);
    }
  };

  const insertCode = () => {
    setInput((prev) => (prev ? prev + '\n' : '') + 'Вот мой код:\n```python\n' + code + '\n```\n');
  };

  return (
    <div>
      <div className="card" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap', marginBottom: 12 }}>
        <button className="btn ghost" onClick={onBack}>← К списку</button>
        <TypeBadge type={session.task_type} />
        <b style={{ flex: 1 }}>{session.title}</b>
        <span className="muted" style={{ fontSize: 12 }}>промптов модели: {prompts}</span>
        {passed && <span className="badge ok">зачёт · {score} баллов</span>}
      </div>

      {queueInfo && <p className="muted" style={{ fontSize: 12 }}>{queueInfo}</p>}
      {error && <div className="error-text">{error}</div>}

      <div style={{ display: 'grid', gridTemplateColumns: 'minmax(280px, 1fr) minmax(320px, 1.25fr) minmax(340px, 1.3fr)', gap: 12, alignItems: 'start' }}>
        {/* 1. Текст задачи */}
        <div className="card">
          <h3 style={{ marginTop: 0, fontSize: 14 }}>Задача</h3>
          <MdText text={session.description_md} />
        </div>

        {/* 2. Диалог с ИИ */}
        <div className="card" style={{ display: 'flex', flexDirection: 'column' }}>
          <h3 style={{ marginTop: 0, fontSize: 14 }}>Диалог с моделью</h3>
          <p className="muted" style={{ fontSize: 11, margin: '0 0 8px' }}>
            Модель не видит редактор — вставляйте нужные фрагменты сами (кнопка ниже или вручную).
          </p>
          <div style={{ height: 380, overflowY: 'auto', display: 'flex', flexDirection: 'column', gap: 8, paddingRight: 4 }}>
            {messages.length === 0 && (
              <p className="muted" style={{ fontSize: 12 }}>
                Начните с точного вопроса: что за функция, что сломано, какой формат ответа нужен.
              </p>
            )}
            {messages.map((m, i) => (
              <div
                key={i}
                style={{
                  alignSelf: m.role === 'user' ? 'flex-end' : 'flex-start',
                  background: m.role === 'user' ? 'rgba(62,99,221,.15)' : 'rgba(255,255,255,.05)',
                  border: '1px solid rgba(255,255,255,.08)',
                  borderRadius: 8, padding: '6px 10px', maxWidth: '95%',
                  whiteSpace: 'pre-wrap', fontSize: 12.5, lineHeight: 1.45,
                }}
              >
                {m.content}
              </div>
            ))}
            <div ref={endRef} />
          </div>
          <div style={{ display: 'flex', gap: 6, marginTop: 8 }}>
            <button className="btn ghost small" onClick={insertCode} disabled={passed}>📎 код в промпт</button>
            <span className="muted" style={{ alignSelf: 'center', fontSize: 11 }}>Enter — отправить, Shift+Enter — новая строка</span>
          </div>
          <textarea
            className="input"
            rows={3}
            style={{ marginTop: 6 }}
            placeholder={passed ? 'Задача решена — диалог закрыт' : 'Спросите модель…'}
            value={input}
            disabled={busy || passed}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                send();
              }
            }}
          />
          <button className="btn" style={{ marginTop: 6 }} onClick={send} disabled={busy || passed}>
            {busy ? 'Думаем…' : 'Отправить'}
          </button>
        </div>

        {/* 3. Редактор + тесты */}
        <div className="card">
          <div style={{ display: 'flex', gap: 8, alignItems: 'center', marginBottom: 8 }}>
            <h3 style={{ margin: 0, fontSize: 14, flex: 1 }}>Редактор</h3>
            <button className="btn ghost small" onClick={() => setCode(session.initial_code)} disabled={passed}>
              ↺ сбросить код
            </button>
            <button className="btn green" onClick={run} disabled={runBusy}>
              {runBusy ? 'Тесты…' : '▶ Запустить тесты'}
            </button>
          </div>
          <div style={{ height: 300, border: '1px solid rgba(255,255,255,.1)', borderRadius: 6, overflow: 'hidden' }}>
            <Editor
              language="python"
              theme="vs-dark"
              value={code}
              onChange={(v) => setCode(v || '')}
              options={{ fontSize: 13, minimap: { enabled: false }, readOnly: passed, autoIndent: 'full', scrollBeyondLastLine: false }}
            />
          </div>

          {result && (
            <div style={{ marginTop: 10 }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 6 }}>
                {result.passed ? <span className="badge ok">зачёт</span> : <span className="badge" style={{ background: '#e5484d', color: '#fff' }}>не пройдено</span>}
                <b>{result.score} / 100</b>
              </div>
              {(result.results || []).map((t, i) => (
                <div key={i} style={{ fontSize: 12.5, margin: '2px 0' }}>
                  {t.passed ? <span style={{ color: '#30a46c' }}>✓</span> : <span style={{ color: '#e5484d' }}>✗</span>}{' '}
                  {t.name}
                  {!t.passed && t.detail && <span className="muted"> — {t.detail.slice(0, 140)}</span>}
                </div>
              ))}
              {result.status !== 'ok' && result.status !== 'accepted' && (
                <p className="muted" style={{ fontSize: 12 }}>Статус прогона: {result.status}</p>
              )}

              {result.mutation && (
                <div style={{ marginTop: 8, fontSize: 12.5 }}>
                  <b>Мутанты поймано:</b> {result.mutation.caught_count} из {(result.mutation.mutants || []).length}
                  {(result.mutation.mutants || []).map((m: any, i: number) => (
                    <span key={i} className="muted" style={{ marginLeft: 8 }}>
                      [{m.caught ? 'пойман: ' + m.name : 'ПРОПУЩЕН: ' + m.name}]
                    </span>
                  ))}
                  {result.mutation.note && <p style={{ color: '#e5484d', fontSize: 12 }}>{result.mutation.note}</p>}
                </div>
              )}

              <div className="muted" style={{ marginTop: 8, fontSize: 12 }}>
                {Object.entries(result.breakdown || {}).map(([k, v]) => (
                  <span key={k} style={{ marginRight: 10 }}>{k}: <b style={{ color: 'inherit' }}>{String(v)}</b></span>
                ))}
              </div>

              {result.passed && (
                <p style={{ fontSize: 12.5, marginTop: 8 }}>
                  Зачёт! Разбор: использовано промптов — {prompts}. Ориентир мастера вайб-кодинга — 3–6 точных запросов;
                  каждый ответ модели проверяйте перед вставкой в редактор.
                </p>
              )}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
