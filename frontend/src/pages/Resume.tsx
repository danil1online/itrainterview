import { useEffect, useState } from 'react';
import {
  api, downloadFile, ResumeData, ResumeResponse, SkillsSummary, TechStackItem,
} from '../api';

const CATEGORY_LABELS: Record<string, string> = {
  language: 'Языки',
  framework: 'Фреймворки и библиотеки',
  database: 'Базы данных',
  tool: 'Инструменты (Tools)',
};

// Поля с фиктивными значениями (152-ФЗ): не редактируются, в DOCX выделены красным —
// студент заменяет их реальными данными уже в скачанном файле.
const FIXED_PERSONAL = {
  last_name: 'Иванов',
  city: 'Новочеркасск',
  phone: '+7 901 111-11-11',
  birth_day: '01',
  birth_month: '01',
  birth_year: '2005',
  citizenship: 'Российская Федерация',
  work_permit: 'Не требуется',
};

const FIXED_EDU = {
  university: 'Южно-Российский государственный политехнический университет (НПИ) имени М.И. Платова',
  faculty: 'Факультет информационных технологий и управления',
};

function FixedInput({ value }: { value: string }) {
  return <input className="input" value={value} readOnly style={{ background: '#f4f4f4', color: '#777' }} />;
}

function Hint({ children }: { children: React.ReactNode }) {
  return <p className="muted" style={{ fontSize: 12, margin: '4px 0 0' }}>{children}</p>;
}

function Field({ label, hint, children }: { label: string; hint?: string; children: React.ReactNode }) {
  return (
    <div className="form-row">
      <label>{label}</label>
      {children}
      {hint && <Hint>{hint}</Hint>}
    </div>
  );
}

function CheckGroup({ options, values, onChange }: { options: string[]; values: string[]; onChange: (v: string[]) => void }) {
  const toggle = (name: string) =>
    onChange(values.includes(name) ? values.filter((x) => x !== name) : [...values, name]);
  return (
    <div className="check-group">
      {options.map((o) => (
        <label key={o} className="check-item">
          <input type="checkbox" checked={values.includes(o)} onChange={() => toggle(o)} /> {o}
        </label>
      ))}
    </div>
  );
}

function TechStackPicker({ tech, values, onChange }: { tech: TechStackItem[]; values: string[]; onChange: (v: string[]) => void }) {
  if (!tech.length) return null;
  return (
    <div className="form-row">
      <label>Стек технологий (отметьте галочками)</label>
      {(['language', 'framework', 'database', 'tool'] as const).map((cat) => {
        const opts = tech.filter((t) => t.category === cat).map((t) => t.name);
        if (!opts.length) return null;
        return (
          <div key={cat} style={{ marginBottom: 8 }}>
            <p className="muted" style={{ fontSize: 12, margin: '4px 0' }}>{CATEGORY_LABELS[cat]}</p>
            <CheckGroup options={opts} values={values} onChange={onChange} />
          </div>
        );
      })}
    </div>
  );
}

function ItemCard({ onRemove, children }: { onRemove: () => void; children: React.ReactNode }) {
  return (
    <div className="item-card">
      <button type="button" className="btn danger small item-remove" onClick={onRemove}>✕</button>
      {children}
    </div>
  );
}

const LIST_KEYS = ['projects', 'labs', 'internships', 'courses', 'hackathons'] as const;
type ListKey = (typeof LIST_KEYS)[number];

export default function Resume() {
  const [data, setData] = useState<ResumeData | null>(null);
  const [skills, setSkills] = useState<SkillsSummary | null>(null);
  const [missing, setMissing] = useState<string[]>([]);
  const [tech, setTech] = useState<TechStackItem[]>([]);
  const [error, setError] = useState('');
  const [saved, setSaved] = useState(false);
  const [busy, setBusy] = useState(false);

  const load = () => {
    Promise.all([api<ResumeResponse>('/api/resume'), api<TechStackItem[]>('/api/resume/tech-stack')])
      .then(([res, techList]) => {
        setData({ ...res.data, ...FIXED_PERSONAL, ...FIXED_EDU });
        setSkills(res.skills);
        setMissing(res.completion.missing);
        setTech(techList);
      })
      .catch((e) => setError(e.message));
  };

  useEffect(() => { load(); }, []);

  const save = async () => {
    if (!data) return;
    setBusy(true);
    setError('');
    try {
      await api('/api/resume', { method: 'PUT', body: JSON.stringify(data) });
      setSaved(true);
      setTimeout(() => setSaved(false), 2500);
      const res = await api<ResumeResponse>('/api/resume');
      setSkills(res.skills);
      setMissing(res.completion.missing);
    } catch (e: any) {
      setError(e.message);
    } finally {
      setBusy(false);
    }
  };

  const exportDocx = async () => {
    setError('');
    try {
      await downloadFile('/api/resume/export.docx', 'resume.docx');
    } catch (e: any) {
      setError(e.message);
    }
  };

  if (!data) {
    return <div className="card">{error ? <div className="error-text">{error}</div> : <p className="muted">Загрузка…</p>}</div>;
  }

  const set = (patch: Partial<ResumeData>) => setData((d) => ({ ...d!, ...patch }));
  const updItem = (key: ListKey, idx: number, patch: Record<string, unknown>) =>
    setData((d) => {
      const arr = [...(d![key] as object[])];
      arr[idx] = { ...(arr[idx] as object), ...patch };
      return { ...d!, [key]: arr } as ResumeData;
    });
  const addItem = (key: ListKey, item: unknown) =>
    setData((d) => ({ ...d!, [key]: [...(d![key] as unknown[]), item] }) as ResumeData);
  const delItem = (key: ListKey, idx: number) =>
    setData((d) => ({ ...d!, [key]: (d![key] as unknown[]).filter((_, i) => i !== idx) }) as ResumeData);

  return (
    <div>
      <div className="card" style={{ display: 'flex', gap: 10, alignItems: 'center', flexWrap: 'wrap' }}>
        <h2 style={{ margin: 0, flex: 1 }}>Резюме</h2>
        <button className="btn green" onClick={save} disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
        {saved && <span className="badge ok">сохранено</span>}
        <button className="btn" onClick={exportDocx}>⬇ Скачать DOCX</button>
      </div>

      {error && <div className="error-text">{error}</div>}

      {!missing.length ? (
        <div className="card"><span className="badge ok">Резюме заполнено — скрининг с рекрутером доступен во вкладке «Рекрутёр»</span></div>
      ) : (
        <div className="card">
          <p style={{ margin: 0 }}>Для скрининга с рекрутером осталось заполнить:</p>
          <ul style={{ margin: '6px 0 0' }}>{missing.map((m) => <li key={m}>{m}</li>)}</ul>
        </div>
      )}

      {skills && (
        <div className="card">
          <h3 style={{ marginTop: 0 }}>Рекомендация системы</h3>
          <p style={{ margin: '4px 0' }}>
            Рекомендуемая должность: <b>{skills.position.position}</b>
            {skills.position.reasons.length > 0 && <span className="muted"> (по навыкам: {skills.position.reasons.join(', ')})</span>}
          </p>
          {skills.hard_skills.length > 0 && <p style={{ margin: '4px 0' }}>Hard Skills: {skills.hard_skills.join(', ')}</p>}
          {skills.tools.length > 0 && <p style={{ margin: '4px 0' }}>Tools: {skills.tools.join(', ')}</p>}
          {skills.algorithms.length > 0 && (
            <p style={{ margin: '4px 0' }}>Алгоритмы, применяемые на практике (по решённым задачам): {skills.algorithms.join(', ')}</p>
          )}
          <Hint>Навыки обобщаются из отмеченных стеков во всех разделах и из задач, решённых вами на платформе.</Hint>
        </div>
      )}

      {/* 1.0 Основная информация */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>1. Основная информация</h3>
        <Hint>Мы не храним персональные данные, поэтому часть сведений Вы можете заполнить только после выгрузки docx</Hint>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 1, minWidth: 140 }}><label>Фамилия</label><FixedInput value={data.last_name} /></div>
          <div className="form-row" style={{ flex: 1, minWidth: 140 }}><label>Имя</label><input className="input" value={data.first_name} onChange={(e) => set({ first_name: e.target.value })} /></div>
          <div className="form-row" style={{ flex: 1, minWidth: 140 }}><label>Отчество</label><input className="input" value={data.middle_name} onChange={(e) => set({ middle_name: e.target.value })} /></div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 1, minWidth: 140 }}>
            <label>Пол</label>
            <select className="input" value={data.gender} onChange={(e) => set({ gender: e.target.value })}>
              <option value="">—</option><option value="male">мужской</option><option value="female">женский</option>
            </select>
          </div>
          <div className="form-row" style={{ flex: 2, minWidth: 200 }}>
            <label>Город проживания</label>
            <FixedInput value={data.city} />
          </div>
          <div className="form-row" style={{ flex: 2, minWidth: 200 }}>
            <label>Номер телефона</label>
            <FixedInput value={data.phone} />
          </div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ minWidth: 90 }}><label>Дата рождения — день</label><FixedInput value={data.birth_day} /></div>
          <div className="form-row" style={{ minWidth: 90 }}><label>месяц</label><FixedInput value={data.birth_month} /></div>
          <div className="form-row" style={{ minWidth: 110 }}><label>год</label><FixedInput value={data.birth_year} /></div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 1, minWidth: 180 }}>
            <label>Гражданство</label>
            <FixedInput value={data.citizenship} />
          </div>
          <div className="form-row" style={{ flex: 2, minWidth: 220 }}>
            <label>Разрешение на работу</label>
            <FixedInput value={data.work_permit} />
          </div>
        </div>
      </div>

      {/* Образование */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Учебное заведение</h3>
        <Hint>Эти данные попадут в раздел «Образование» файла резюме. Источник — студенческий билет / приложение к диплому.</Hint>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 3, minWidth: 260 }}><label>ВУЗ</label><FixedInput value={data.university} /></div>
          <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>Факультет</label><FixedInput value={data.faculty} /></div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 2, minWidth: 220 }}><label>Кафедра</label><input className="input" value={data.department} onChange={(e) => set({ department: e.target.value })} placeholder="например, Кафедра программирования и информационных технологий" /></div>
        </div>
        <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
          <div className="form-row" style={{ flex: 2, minWidth: 220 }}><label>Специальность / направление</label><input className="input" value={data.major} onChange={(e) => set({ major: e.target.value })} /></div>
          <div className="form-row" style={{ flex: 1, minWidth: 180 }}>
            <label>Год окончания</label>
            <input className="input" value={data.graduation_year} onChange={(e) => set({ graduation_year: e.target.value })} placeholder="2027 или «окончание ожидается в 2027»" />
          </div>
        </div>
      </div>

      {/* Ссылки */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>Ссылки на профили</h3>
        <Hint>Полная ссылка на профиль (https://…). Если аккаунта ещё нет — создайте до отправки резюме; пустые поля не попадут в файл.</Hint>
        <div className="form-row"><label>GitHub</label><input className="input" value={data.github} onChange={(e) => set({ github: e.target.value })} placeholder="https://github.com/…" /></div>
        <div className="form-row"><label>GitVerse</label><input className="input" value={data.gitverse} onChange={(e) => set({ gitverse: e.target.value })} placeholder="https://gitverse.ru/…" /></div>
        <div className="form-row"><label>GitFlic</label><input className="input" value={data.gitflic} onChange={(e) => set({ gitflic: e.target.value })} placeholder="https://gitflic.ru/…" /></div>
      </div>

      {/* 1.1.1 Проекты */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>2. Курсовые и дипломные проекты</h3>
        <Hint>Отчёты по курсовым работам и выпускная квалификационная работа (ВКР). Ищите титульные листы, раздел «Цель работы» и презентации.</Hint>
        {data.projects.map((p, i) => (
          <ItemCard key={i} onRemove={() => delItem('projects', i)}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 2, minWidth: 220 }}><label>Название</label><input className="input" value={p.name} onChange={(e) => updItem('projects', i, { name: e.target.value })} placeholder="Например: «Веб-портал записи на занятия в спортивную секцию»" /></div>
            </div>
            <Field label="Решённая задача" hint="1–2 предложения: что построено и для кого, какую проблему решает.">
              <textarea className="input" rows={2} value={p.problem} onChange={(e) => updItem('projects', i, { problem: e.target.value })} />
            </Field>
            <TechStackPicker tech={tech} values={p.tech_stack} onChange={(v) => updItem('projects', i, { tech_stack: v })} />
          </ItemCard>
        ))}
        <button className="btn ghost" onClick={() => addItem('projects', { name: '', problem: '', tech_stack: [] })}>+ Добавить проект</button>
      </div>

      {/* 1.1.2 Лабораторные */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>3. Лабораторные и практические работы</h3>
        <Hint>Самые содержательные лабораторные по профильным предметам (программирование, БД, сети, ОС). Цель работы берётся из учебно-методического указания.</Hint>
        {data.labs.map((l, i) => (
          <ItemCard key={i} onRemove={() => delItem('labs', i)}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 1, minWidth: 180 }}><label>Предмет</label><input className="input" value={l.subject} onChange={(e) => updItem('labs', i, { subject: e.target.value })} placeholder="Например: «Программирование»" /></div>
              <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>Название работы</label><input className="input" value={l.work_name} onChange={(e) => updItem('labs', i, { work_name: e.target.value })} placeholder="Лаб. работа №5: «Двусвязный список»" /></div>
            </div>
            <Field label="Цель работы" hint="Формулировка из раздела «Цель работы» учебно-методического указания.">
              <textarea className="input" rows={2} value={l.goal} onChange={(e) => updItem('labs', i, { goal: e.target.value })} />
            </Field>
            <TechStackPicker tech={tech} values={l.tech_stack} onChange={(v) => updItem('labs', i, { tech_stack: v })} />
          </ItemCard>
        ))}
        <button className="btn ghost" onClick={() => addItem('labs', { subject: '', work_name: '', goal: '', tech_stack: [] })}>+ Добавить работу</button>
      </div>

      {/* 1.2 Практика */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>4. Практика и стажировки</h3>
        <Hint>Производственная/преддипломная практика, летние стажировки. Источник — практика дневник, справка, отчёт.</Hint>
        {data.internships.map((it, i) => (
          <ItemCard key={i} onRemove={() => delItem('internships', i)}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 1, minWidth: 160 }}><label>Город</label><input className="input" value={it.city} onChange={(e) => updItem('internships', i, { city: e.target.value })} /></div>
              <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>Предприятие / организация</label><input className="input" value={it.organization} onChange={(e) => updItem('internships', i, { organization: e.target.value })} /></div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 1, minWidth: 180 }}><label>Сроки</label><input className="input" value={it.period} onChange={(e) => updItem('internships', i, { period: e.target.value })} placeholder="сентябрь 2025 — январь 2026" /></div>
            </div>
            <Field label="Цель практики / ваши задачи">
              <textarea className="input" rows={2} value={it.goal} onChange={(e) => updItem('internships', i, { goal: e.target.value })} />
            </Field>
          </ItemCard>
        ))}
        <button className="btn ghost" onClick={() => addItem('internships', { city: '', organization: '', period: '', goal: '' })}>+ Добавить практику</button>
      </div>

      {/* 1.4 Курсы */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>5. Курсы дополнительного обучения</h3>
        <Hint>Онлайн-курсы и сертификаты (Stepik, Coursera, Яндекс.Практикум и т.п.). Источник — сертификат или страница о прохождении.</Hint>
        {data.courses.map((c, i) => (
          <ItemCard key={i} onRemove={() => delItem('courses', i)}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 1, minWidth: 160 }}><label>Месяц и год</label><input className="input" value={c.month_year} onChange={(e) => updItem('courses', i, { month_year: e.target.value })} placeholder="март 2026" /></div>
              <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>Название курса</label><input className="input" value={c.name} onChange={(e) => updItem('courses', i, { name: e.target.value })} placeholder="«Python для анализа данных» (Stepik)" /></div>
            </div>
            <TechStackPicker tech={tech} values={c.tech_stack} onChange={(v) => updItem('courses', i, { tech_stack: v })} />
          </ItemCard>
        ))}
        <button className="btn ghost" onClick={() => addItem('courses', { month_year: '', name: '', tech_stack: [] })}>+ Добавить курс</button>
      </div>

      {/* 1.5.1 Хакатоны */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>6. Хакатоны и олимпиады</h3>
        <Hint>Университетские и городские хакатоны, олимпиады по программированию (ИТ-куб, Яндекс.Куб, региональные этапы).</Hint>
        {data.hackathons.map((h, i) => (
          <ItemCard key={i} onRemove={() => delItem('hackathons', i)}>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>Название</label><input className="input" value={h.name} onChange={(e) => updItem('hackathons', i, { name: e.target.value })} /></div>
              <div className="form-row" style={{ flex: 1, minWidth: 160 }}><label>Организатор</label><input className="input" value={h.organizer} onChange={(e) => updItem('hackathons', i, { organizer: e.target.value })} /></div>
            </div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 1, minWidth: 160 }}><label>Место проведения</label><input className="input" value={h.location} onChange={(e) => updItem('hackathons', i, { location: e.target.value })} /></div>
              <div className="form-row" style={{ flex: 1, minWidth: 140 }}><label>Месяц и год</label><input className="input" value={h.month_year} onChange={(e) => updItem('hackathons', i, { month_year: e.target.value })} placeholder="апрель 2026" /></div>
              <div className="form-row" style={{ flex: 1, minWidth: 140 }}>
                <label>Роль в команде</label>
                <select className="input" value={h.role} onChange={(e) => updItem('hackathons', i, { role: e.target.value })}>
                  <option value="">—</option><option value="frontend">frontend</option><option value="backend">backend</option><option value="QA">QA</option><option value="fullstack">fullstack</option>
                </select>
              </div>
            </div>
            <TechStackPicker tech={tech} values={h.tech_stack} onChange={(v) => updItem('hackathons', i, { tech_stack: v })} />
          </ItemCard>
        ))}
        <button className="btn ghost" onClick={() => addItem('hackathons', { name: '', organizer: '', location: '', month_year: '', role: '', tech_stack: [] })}>+ Добавить мероприятие</button>
      </div>

      {/* 1.5.2/1.5.3 НИЛ */}
      <div className="card">
        <h3 style={{ marginTop: 0 }}>7. Научно-исследовательская лаборатория (НИЛ)</h3>
        <Hint>Если вы член студенческой научно-исследовательской лаборатории — заполните; иначе раздел можно пропустить.</Hint>
        {data.lab_membership ? (
          <div>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <div className="form-row" style={{ flex: 2, minWidth: 200 }}><label>ВУЗ</label><input className="input" value={data.lab_membership.university} onChange={(e) => set({ lab_membership: { ...data.lab_membership!, university: e.target.value } })} /></div>
              <div className="form-row" style={{ flex: 1, minWidth: 160 }}><label>Кафедра</label><input className="input" value={data.lab_membership.department} onChange={(e) => set({ lab_membership: { ...data.lab_membership!, department: e.target.value } })} /></div>
            </div>
            <div className="form-row"><label>Ссылка на страницу кафедры на сайте ВУЗа</label><input className="input" value={data.lab_membership.department_url} onChange={(e) => set({ lab_membership: { ...data.lab_membership!, department_url: e.target.value } })} /></div>
            <div className="form-row"><label>ФИО руководителя лаборатории</label><input className="input" value={data.lab_membership.supervisor} onChange={(e) => set({ lab_membership: { ...data.lab_membership!, supervisor: e.target.value } })} /></div>
            <div className="form-row"><label>Ваш личный проект</label><input className="input" value={data.lab_membership.own_project} onChange={(e) => set({ lab_membership: { ...data.lab_membership!, own_project: e.target.value } })} /></div>
            <div className="form-row">
              <label>Проекты других студентов лаборатории</label>
              {data.lab_membership.other_projects.map((p, i) => (
                <input key={i} className="input" style={{ marginBottom: 6 }} value={p}
                  onChange={(e) => set({ lab_membership: { ...data.lab_membership!, other_projects: data.lab_membership!.other_projects.map((x, j) => (j === i ? e.target.value : x)) } })} />
              ))}
              <button className="btn ghost small" onClick={() => set({ lab_membership: { ...data.lab_membership!, other_projects: [...data.lab_membership!.other_projects, ''] } })}>+ Добавить проект</button>
            </div>
          </div>
        ) : (
          <button className="btn ghost" onClick={() => set({ lab_membership: { university: '', department: '', department_url: '', supervisor: '', own_project: '', other_projects: [] } })}>+ Указать членство в НИЛ</button>
        )}
      </div>

      <div className="card" style={{ display: 'flex', gap: 10, alignItems: 'center' }}>
        <button className="btn green" onClick={save} disabled={busy}>{busy ? 'Сохраняем…' : 'Сохранить'}</button>
        {saved && <span className="badge ok">сохранено</span>}
        <button className="btn" onClick={exportDocx}>⬇ Скачать DOCX</button>
      </div>
    </div>
  );
}
