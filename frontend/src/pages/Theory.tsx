// Раздел «Теория»: карточки паттернов (идея, разделы, примеры с кодом) и список литературы.
import { useState } from 'react';
import { THEORY_PART1 } from '../theory/data1';
import { THEORY_PART2 } from '../theory/data2';
import { LITERATURE } from '../theory/literature';
import type { TheoryPattern } from '../theory/data1';

const ALL: TheoryPattern[] = [...THEORY_PART1, ...THEORY_PART2];

export default function Theory() {
  const [activeId, setActiveId] = useState(ALL[0].id);
  const [example, setExample] = useState(0);
  const [langIdx, setLangIdx] = useState(0);
  const isLit = activeId === 'literature';
  const pattern = ALL.find((p) => p.id === activeId);
  const ex = pattern ? pattern.examples[Math.min(example, pattern.examples.length - 1)] : undefined;

  return (
    <div className="theory-layout">
      <aside className="card theory-side">
        <h3 style={{ marginTop: 0 }}>Методы и подходы</h3>
        {ALL.map((p) => (
          <button
            key={p.id}
            className={`theory-item ${p.id === activeId ? 'active' : ''}`}
            onClick={() => { setActiveId(p.id); setExample(0); setLangIdx(0); }}
          >
            {p.name}
          </button>
        ))}
        <button
          className={`theory-item ${isLit ? 'active' : ''}`}
          onClick={() => setActiveId('literature')}
        >
          Литература
        </button>
      </aside>

      <div>
        {!pattern || !ex ? (
          <div className="card">
            <h2 style={{ marginTop: 0 }}>Литература</h2>
            <p className="muted">Учебники и справочники по алгоритмам — от классики до практических сборников.</p>
            <ul className="literature-list">
              {LITERATURE.map((l) => (
                <li key={l.url}>
                  <a href={l.url} target="_blank" rel="noreferrer">{l.label}</a>
                </li>
              ))}
            </ul>
          </div>
        ) : (
          <>
            <div className="card">
              <h2 style={{ marginTop: 0 }}>{pattern.name}</h2>
              <p className="theory-idea">{pattern.idea}</p>
              {pattern.sections?.map((s) => (
                <div key={s.title} className="theory-section">
                  <h4>{s.title}</h4>
                  <p className="theory-body">{s.body}</p>
                </div>
              ))}
            </div>

            {pattern.examples.length > 1 && (
              <div style={{ display: 'flex', gap: 8, margin: '0 0 12px' }}>
                {pattern.examples.map((e, i) => (
                  <button key={i} className={`btn small ${i === example ? '' : 'ghost'}`} onClick={() => setExample(i)}>
                    Пример {i + 1}
                  </button>
                ))}
              </div>
            )}

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Пример. {ex.title}</h3>
              <p className="muted" style={{ marginTop: 4 }}>{ex.statement}</p>
              <div className="tabs">
                {ex.solutions.map((s, j) => (
                  <button key={j} className={j === langIdx ? 'active' : ''} onClick={() => setLangIdx(j)}>
                    {s.lang}
                  </button>
                ))}
              </div>
              <pre className="code-block">{ex.solutions[langIdx].code}</pre>
              <p className="muted" style={{ marginBottom: 0 }}>Сложность: {ex.complexity}</p>
            </div>

            <div className="card">
              <h3 style={{ marginTop: 0 }}>Для дальнейшего изучения</h3>
              <ul>
                {pattern.links.map((l) => (
                  <li key={l.url}>
                    <a href={l.url} target="_blank" rel="noreferrer">{l.label}</a>
                  </li>
                ))}
              </ul>
            </div>
          </>
        )}
      </div>
    </div>
  );
}
