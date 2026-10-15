/**
 * Скрининг-собеседование с «рекрутером» (LLM), доступно после заполнения резюме.
 * Диалог идёт через LLM-очередь (pollLlmJob); рекомендации устаревают после нового диалога.
 */
import { useEffect, useRef, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ResumeResponse, pollLlmJob } from '../api';

interface Msg {
  id?: number;
  role: 'user' | 'assistant';
  content: string;
}

export default function Recruiter() {
  const [ready, setReady] = useState<boolean | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [messages, setMessages] = useState<Msg[]>([]);
  const [input, setInput] = useState('');
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState('');
  const [recommendation, setRecommendation] = useState<{ reply: string; fresh: boolean } | null>(null);
  const [recBusy, setRecBusy] = useState(false);
  const [queueInfo, setQueueInfo] = useState('');
  const [resetBusy, setResetBusy] = useState(false);
  const endRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    api<ResumeResponse>('/api/resume')
      .then((res) => {
        setReady(res.completion.ready);
        setMissing(res.completion.missing);
        if (res.completion.ready) {
          return Promise.all([
            api<Msg[]>('/api/recruiter/history').then(setMessages).catch(() => undefined),
            api<{ reply: string; fresh: boolean }>('/api/recruiter/recommendation')
              .then((r) => setRecommendation(r))
              .catch(() => undefined), // 404 — рекомендаций ещё нет
          ]);
        }
      })
      .catch((e) => setError(e.message));
  }, []);

  useEffect(() => {
    endRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages, recommendation]);

  const queueLine = (j: { status: string; position: number }) =>
    j.status === 'running' ? 'Модель думает…' : `Модель занята — вы №${j.position + 1} в очереди`;

  // Отправляет реплику (модель получает последние 10 сообщений) и ждёт ответ поллингом; при ошибке откатывает своё сообщение.
  const send = async () => {
    const text = input.trim();
    if (!text || busy) return;
    setBusy(true);
    setError('');
    const next: Msg[] = [...messages, { role: 'user', content: text }];
    setMessages(next);
    setInput('');
    try {
      const { job_id } = await api<{ job_id: number }>('/api/recruiter/chat', {
        method: 'POST',
        body: JSON.stringify({ messages: next.slice(-10) }),
      });
      const job = await pollLlmJob(job_id, (j) => setQueueInfo(queueLine(j)));
      if (job.status !== 'done' || !job.result) throw new Error(job.error || 'Модель не ответила');
      setMessages((m) => [...m, { role: 'assistant', content: job.result as string }]);
      // новый диалог устаревает старые рекомендации — кнопка перегенерации оживает
      setRecommendation((r) => (r ? { ...r, fresh: false } : r));
    } catch (e: any) {
      setError(e.message);
      setMessages((m) => m.slice(0, -1));
    } finally {
      setBusy(false);
      setQueueInfo('');
    }
  };

  // Генерация рекомендаций по итогам диалога: job в LLM-очереди, результат помечается fresh=true.
  const getRecommendation = async () => {
    setRecBusy(true);
    setError('');
    try {
      const { job_id } = await api<{ job_id: number }>('/api/recruiter/recommendations', { method: 'POST' });
      const job = await pollLlmJob(job_id, (j) => setQueueInfo(queueLine(j)));
      if (job.status !== 'done' || !job.result) throw new Error(job.error || 'Генерация не удалась');
      setRecommendation({ reply: job.result, fresh: true });
    } catch (e: any) {
      setError(e.message);
    } finally {
      setRecBusy(false);
      setQueueInfo('');
    }
  };

  const resetHistory = async () => {
    if (!confirm('Сбросить историю общения с рекрутёром? Рекомендации тоже будут удалены.')) return;
    setResetBusy(true);
    setError('');
    try {
      await api('/api/recruiter/reset', { method: 'POST' });
      setMessages([]);
      setRecommendation(null);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setResetBusy(false);
    }
  };

  if (error && !ready) return <div className="card"><div className="error-text">{error}</div></div>;
  if (ready === null) return <div className="card"><p className="muted">Загрузка…</p></div>;

  if (!ready) {
    return (
      <div>
        <h2>Скрининг с рекрутером</h2>
        <div className="card">
          <p style={{ marginTop: 0 }}>
            Скрининг-собеседование (15–20 минут) открывается после заполнения резюме. Осталось заполнить:
          </p>
          <ul>{missing.map((m) => <li key={m}>{m}</li>)}</ul>
          <Link className="btn green" to="/resume">Перейти к резюме</Link>
        </div>
      </div>
    );
  }

  return (
    <div>
      <h2>Скрининг с рекрутером</h2>
      <div className="card" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <p className="muted" style={{ flex: 1, margin: 0 }}>
          Собеседование длится 15–20 минут: знакомство, вопросы по вашему опыту из резюме,
          зарплатные ожидания и базовые требования. Алгоритмические задачи здесь не задают.
        </p>
        <button className="btn" onClick={getRecommendation} disabled={recBusy || messages.length === 0 || (recommendation?.fresh ?? false)}>
          {recBusy ? 'Анализируем…' : '📋 Получить рекомендации'}
        </button>
        {(recommendation?.fresh ?? false) && (
          <span className="muted" style={{ fontSize: 12 }}>актуальны — перегенерация после нового диалога</span>
        )}
        <button className="btn ghost" onClick={resetHistory} disabled={resetBusy || messages.length === 0}>
          {resetBusy ? 'Сбрасываем…' : '↺ Сбросить историю общения'}
        </button>
      </div>

      {queueInfo && <p className="muted" style={{ fontSize: 12 }}>{queueInfo}</p>}
      {error && <div className="error-text">{error}</div>}

      <div className="card chat" style={{ height: 560 }}>
        <div className="chat-messages">
          {messages.length === 0 && (
            <p className="muted">Напишите «Здравствуйте» — рекрутёр представится и начнёт собеседование.</p>
          )}
          {messages.map((m, i) => (
            <div key={i} className={`chat-msg ${m.role}`}>{m.content}</div>
          ))}
          <div ref={endRef} />
        </div>
        <div className="chat-input">
          <input
            className="input"
            value={input}
            placeholder="Ваш ответ…"
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && send()}
          />
          <button className="btn" onClick={send} disabled={busy}>{busy ? '…' : '➤'}</button>
        </div>
      </div>

      {recommendation && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Рекомендации по итогам скрининга</h3>
          <p style={{ whiteSpace: 'pre-wrap', margin: 0, lineHeight: 1.6 }}>{recommendation.reply}</p>
        </div>
      )}
    </div>
  );
}
