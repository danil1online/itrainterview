import { useEffect, useRef, useState } from 'react';
import Editor from '@monaco-editor/react';
import { useParams } from 'react-router-dom';
import {
  api, LANGUAGES, LEVEL_LABELS, PATTERN_LABELS, RunResponse, STATUS_LABELS, Submission, TaskDetail, pollLlmJob,
} from '../api';

interface ChatMsg { role: 'user' | 'assistant'; content: string; }

export default function Solve() {
  const { slug = '' } = useParams();
  const [task, setTask] = useState<TaskDetail | null>(null);
  const [language, setLanguage] = useState('python');
  const [code, setCode] = useState(LANGUAGES.python.template);
  const [runResult, setRunResult] = useState<RunResponse | null>(null);
  const [submission, setSubmission] = useState<Submission | null>(null);
  const [busy, setBusy] = useState<'run' | 'submit' | 'retitle' | 'chat' | ''>('');
  const [queueInfo, setQueueInfo] = useState('');
  const [error, setError] = useState('');
  const [openTest, setOpenTest] = useState<string>('');
  const [hintsOpen, setHintsOpen] = useState(false);

  const [chat, setChat] = useState<ChatMsg[]>([]);
  const [chatInput, setChatInput] = useState('');
  const [chatMode, setChatMode] = useState<'hint' | 'explain'>('hint');
  const chatEndRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<TaskDetail>(`/api/tasks/${slug}`).then(setTask).catch((e) => setError(e.message));
    api<ChatMsg[]>(`/api/assistant/history?task_slug=${slug}`)
      .then((h) => setChat(h.map((m: any) => ({ role: m.role as ChatMsg['role'], content: m.content }))))
      .catch(() => {});
  }, [slug]);

  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [chat]);

  const changeLanguage = (lang: string) => {
    setLanguage(lang);
    setCode(LANGUAGES[lang].template);
  };

  const run = async () => {
    setBusy('run'); setError(''); setSubmission(null);
    try {
      setRunResult(await api<RunResponse>(`/api/tasks/${slug}/run`, { method: 'POST', body: JSON.stringify({ language, code }) }));
    } catch (e: any) { setError(e.message); } finally { setBusy(''); }
  };

  const submit = async () => {
    setBusy('submit'); setError(''); setRunResult(null);
    try {
      const sub = await api<Submission>(`/api/tasks/${slug}/submit`, { method: 'POST', body: JSON.stringify({ language, code, want_feedback: true }) });
      setSubmission(sub);
      if (sub.status === 'accepted') {
        setTask((t) => (t ? { ...t, solved: true } : t));
      }
      if (sub.feedback_job_id) {
        // разбор генерируется в LLM-очереди — подождём и перезагрузим сабмит
        const job = await pollLlmJob(sub.feedback_job_id, (j) => setQueueInfo(queueLine(j)));
        if (job.status === 'done') {
          const fresh = await api<Submission>(`/api/submissions/${sub.id}`);
          setSubmission(fresh);
        } else {
          setError(`Разбор не удалось сгенерировать: ${job.error || job.status}`);
        }
      }
    } catch (e: any) { setError(e.message); } finally { setBusy(''); setQueueInfo(''); }
  };

  const retitle = async () => {
    setBusy('retitle'); setError('');
    try {
      const { job_id } = await api<{ job_id: number }>(`/api/tasks/${slug}/retitle`, { method: 'POST', body: JSON.stringify({ save: true }) });
      const job = await pollLlmJob(job_id, (j) => setQueueInfo(queueLine(j)));
      if (job.status !== 'done' || !job.result) throw new Error(job.error || 'Генерация не удалась');
      const v = JSON.parse(job.result);
      setTask((t) => (t ? { ...t, title: v.title, legend: v.legend } : t));
    } catch (e: any) { setError(e.message); } finally { setBusy(''); setQueueInfo(''); }
  };

  const sendChat = async () => {
    const text = chatInput.trim();
    if (!text || busy) return;
    setChatInput('');
    const next: ChatMsg[] = [...chat, { role: 'user', content: text }];
    setChat(next);
    setBusy('chat');
    try {
      const { job_id } = await api<{ job_id: number }>('/api/assistant/chat', {
        method: 'POST',
        body: JSON.stringify({ task_slug: slug, messages: next.slice(-10), code, language, mode: chatMode }),
      });
      const job = await pollLlmJob(job_id, (j) => setQueueInfo(queueLine(j)));
      if (job.status !== 'done' || !job.result) throw new Error(job.error || 'Модель не ответила');
      const reply = job.result;
      setChat((c) => [...c, { role: 'assistant', content: reply }]);
    } catch (e: any) {
      setChat((c) => [...c, { role: 'assistant', content: `[ошибка] ${e.message}` }]);
    } finally {
      setBusy(''); setQueueInfo('');
    }
  };

  const queueLine = (j: { status: string; position: number }) =>
    j.status === 'running' ? 'Модель думает…' : `Модель занята — вы №${j.position + 1} в очереди`;

  if (!task) return <div className={error ? 'error-text' : 'center muted'}>{error || 'Загрузка…'}</div>;

  const results = submission?.results || runResult?.results || [];
  const status = submission?.status || runResult?.status;

  return (
    <div>
      <div className="solve-layout">
        <div>
          <div className="card">
            <div style={{ display: 'flex', justifyContent: 'space-between', gap: 10, alignItems: 'flex-start' }}>
              <h2 style={{ margin: 0 }}>{task.title}</h2>
              <div style={{ display: 'flex', gap: 6, flexShrink: 0 }}>
                <span className={`badge ${task.level}`}>{LEVEL_LABELS[task.level]}</span>
                {task.solved && <span className="badge ok">✓</span>}
              </div>
            </div>
            <p className="muted" style={{ marginTop: 4 }}>Паттерн: {PATTERN_LABELS[task.pattern] || task.pattern}</p>
            <div className="legend-box">{task.legend}</div>
            {(() => {
              const sample = task.tests.find((t) => t.sample) ?? task.tests[0];
              return sample ? (
                <>
                  <h4 style={{ marginBottom: 6 }}>Пример</h4>
                  <pre className="code-block">Ввод:\n{sample.stdin}\nОжидаемый вывод:\n{sample.expected_stdout}</pre>
                </>
              ) : null;
            })()}
            {task.hints.length > 0 && (
              <>
                <button className="btn ghost small" style={{ marginTop: 8 }} onClick={() => setHintsOpen(!hintsOpen)}>
                  {hintsOpen ? 'Скрыть подсказки' : `Показать подсказки (${task.hints.length})`}
                </button>
                {hintsOpen && (
                  <ul className="muted">{task.hints.map((h, i) => <li key={i}>{h}</li>)}</ul>
                )}
              </>
            )}
            <button className="btn ghost small" style={{ marginTop: 8 }} onClick={retitle} disabled={busy !== ''}>
              {busy === 'retitle' ? 'ИИ придумывает новую легенду…' : '🎲 Новая легенда от ИИ'}
            </button>
          </div>

          <div className="card chat">
            <h3 style={{ margin: '0 0 10px' }}>
              ИИ-помощник{' '}
              <select className="input" style={{ width: 'auto', display: 'inline-block', padding: '2px 8px', fontSize: 12 }} value={chatMode} onChange={(e) => setChatMode(e.target.value as any)}>
                <option value="hint">наводящие подсказки</option>
                <option value="explain">объяснение ошибок</option>
              </select>
            </h3>
            <div className="chat-messages">
              {chat.length === 0 && <p className="muted">Спросите что-нибудь про задачу — помощник не даст готовое решение, но направит.</p>}
              {chat.map((m, i) => (
                <div key={i} className={`chat-msg ${m.role}`}>{m.content}</div>
              ))}
              <div ref={chatEndRef} />
            </div>
            {queueInfo && busy === 'chat' && <p className="muted" style={{ fontSize: 12, margin: '6px 0 0' }}>{queueInfo}</p>}
            <div className="chat-input">
              <input className="input" value={chatInput} placeholder="Ваш вопрос…" onChange={(e) => setChatInput(e.target.value)} onKeyDown={(e) => e.key === 'Enter' && sendChat()} />
              <button className="btn" onClick={sendChat} disabled={busy !== ''}>➤</button>
            </div>
          </div>
        </div>

        <div>
          <div className="card editor-card">
            <div className="editor-toolbar">
              <select className="input" value={language} onChange={(e) => changeLanguage(e.target.value)}>
                {Object.entries(LANGUAGES).map(([k, v]) => (
                  <option key={k} value={k}>{v.label}</option>
                ))}
              </select>
              <button className="btn" onClick={run} disabled={busy !== ''}
                title="Проверяет код только на примерах из условия. Результат не засчитывается в статистику и прогресс.">
                ▶ Запуск (тесты из условия)
              </button>
              <button className="btn green" onClick={submit} disabled={busy !== ''}
                title="Запускает ВСЕ тесты, включая скрытые. Результат засчитывается в прогресс и статистику; при провале — разбор от ИИ-помощника.">
                ✓ Отправить на проверку
              </button>
              {status && (
                <span className={`badge ${status === 'accepted' ? 'ok' : 'fail'}`}>
                  {STATUS_LABELS[status] || status} · {(submission?.passed_count ?? runResult?.passed_count)}/{(submission?.total_count ?? runResult?.total_count)} · {runResult?.time_ms ?? submission?.time_ms} мс
                </span>
              )}
            </div>
            <p className="muted" style={{ fontSize: 12, margin: '6px 0 8px' }}>
              «Запуск (тесты из условия)» проверяет код только на примерах из условия — для быстрой отладки, в статистику не идёт.
              «Отправить на проверку» запускает все тесты, включая скрытые: результат засчитывается в прогресс и статистику, при провале даётся разбор от ИИ-помощника.
            </p>
            <div className="editor-host">
              <Editor language={LANGUAGES[language].monaco} theme="vs-dark" value={code} onChange={(v) => setCode(v || '')} options={{ fontSize: 14, minimap: { enabled: false }, autoIndent: 'full' }} />
            </div>
          </div>

          {queueInfo && busy !== 'chat' && <p className="muted" style={{ fontSize: 12 }}>{queueInfo}</p>}
          {error && <div className="error-text">{error}</div>}

          {results.length > 0 && (
            <div className="card results-list">
              <h3 style={{ marginTop: 0 }}>Результаты тестов</h3>
              {results.map((r) => (
                <div key={r.name} className="test-row">
                  <div className="test-row-head" onClick={() => setOpenTest(openTest === r.name ? '' : r.name)}>
                    <span className={`badge ${r.passed ? 'ok' : 'fail'}`}>{r.passed ? '✓ passed' : STATUS_LABELS[r.status] || r.status}</span>
                    <span>{r.name}</span>
                    <span className="muted" style={{ marginLeft: 'auto' }}>{r.time_ms} мс</span>
                  </div>
                  {openTest === r.name && !r.passed && (
                    <div className="test-row-body">
                      {r.got_stdout && <>Получено:\n{r.got_stdout}\n</>}
                      {r.stderr && <>\nstderr:\n{r.stderr}</>}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {submission?.ai_feedback && (
            <div className="card">
              <h3 style={{ marginTop: 0 }}>💬 Разбор от ИИ-помощника</h3>
              <div className="feedback-box">{submission.ai_feedback}</div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
