/**
 * API-клиент и общие типы приложения.
 * Единая обёртка fetch: Bearer-авторизация, авто-рефреш токена при 401, разбор ошибок FastAPI.
 */
// ---------- Типы ответов API ----------

export interface UserInfo {
  id: number;
  email: string;
  username: string;
  role: 'student' | 'admin';
  is_active: boolean;
  created_at: string;
}

export interface TaskListItem {
  slug: string;
  title: string;
  pattern: string;
  level: string;
  solved: boolean;
}

export interface SampleTest {
  name: string;
  stdin: string;
  expected_stdout: string;
  sample: boolean;
}

export interface TaskDetail {
  slug: string;
  title: string;
  legend: string;
  pattern: string;
  level: string;
  hints: string[];
  tests: SampleTest[];
  solved: boolean | null;
}

export interface TestResult {
  name: string;
  passed: boolean;
  status: string;
  expected_stdout: string;
  got_stdout: string;
  stderr: string;
  time_ms: number;
}

export interface RunResponse {
  status: string;
  passed_count: number;
  total_count: number;
  time_ms: number;
  results: TestResult[];
}

export interface Submission {
  id: number;
  task_id: number;
  task_slug?: string | null;
  language: string;
  code: string;
  status: string;
  passed_count: number;
  total_count: number;
  results: TestResult[];
  time_ms: number;
  ai_feedback: string | null;
  feedback_job_id?: number | null;
  created_at: string;
}

export interface AdminUser {
  id: number;
  email: string;
  username: string;
  role: string;
  is_active: boolean;
  created_at: string;
  submissions: number;
  solved_tasks: number;
}

// ---------- Токены и HTTP-клиент ----------

const TOKEN_KEY = 'itraint.tokens';

export function getTokens(): { access_token: string; refresh_token: string } | null {
  const raw = localStorage.getItem(TOKEN_KEY);
  return raw ? JSON.parse(raw) : null;
}

export function setTokens(tokens: { access_token: string; refresh_token: string } | null) {
  if (tokens) localStorage.setItem(TOKEN_KEY, JSON.stringify(tokens));
  else localStorage.removeItem(TOKEN_KEY);
}

// Базовый fetch: подставляет Bearer-токен и Content-Type для строкового тела.
async function rawRequest(path: string, opts: RequestInit = {}, token?: string) {
  const headers: Record<string, string> = { ...(opts.headers as Record<string, string>) };
  if (token) headers['Authorization'] = `Bearer ${token}`;
  if (opts.body && typeof opts.body === 'string') headers['Content-Type'] = 'application/json';
  return fetch(path, { ...opts, headers });
}

// Single-flight refresh: параллельные 401 дают ОДИН запрос обновления токена.
let refreshing: Promise<boolean> | null = null;

async function tryRefresh(): Promise<boolean> {
  const tokens = getTokens();
  if (!tokens?.refresh_token) return false;
  if (!refreshing) {
    refreshing = (async () => {
      try {
        const rr = await rawRequest('/api/auth/refresh', {
          method: 'POST',
          body: JSON.stringify({ refresh_token: tokens.refresh_token }),
        });
        if (rr.ok) {
          setTokens(await rr.json());
          return true;
        }
        return false;
      } finally {
        refreshing = null;
      }
    })();
  }
  return refreshing;
}

// Запрос с авторизацией: при 401 обновляет токен (single-flight) и повторяет;
// если обновление не удалось, а пользователь был авторизован — сброс токенов и редирект на /login.
async function authFetch(path: string, opts: RequestInit): Promise<Response> {
  let resp = await rawRequest(path, opts, getTokens()?.access_token);
  if (resp.status === 401) {
    const wasAuthed = !!getTokens()?.access_token;
    const ok = await tryRefresh();
    if (ok) {
      resp = await rawRequest(path, opts, getTokens()?.access_token);
    } else if (wasAuthed) {
      setTokens(null);
      window.location.assign('/login');
    }
  }
  return resp;
}

/**
 * Запрос с авторизацией: при 401 один раз пробует обновить токен (refresh) и повторяет запрос.
 * При ошибке бросает Error с detail из ответа (строка / массив / Pydantic issues).
 */
export async function api<T = unknown>(path: string, opts: RequestInit = {}): Promise<T> {
  const resp = await authFetch(path, opts);
  if (!resp.ok) {
    let detail = `HTTP ${resp.status}`;
    try {
      const data = await resp.json();
      if (typeof data.detail === 'string') detail = data.detail;
      else if (Array.isArray(data.detail)) detail = data.detail.map((d: any) => d.msg).join('; ');
      else if (data.detail && typeof data.detail === 'object' && Array.isArray(data.detail.issues))
        detail = data.detail.issues.join('; ');
    } catch {
      /* ignore */
    }
    throw new Error(detail);
  }
  if (resp.status === 204) return undefined as T;
  return resp.json();
}

// ---------- Справочники (языки, уровни, паттерны, статусы) ----------

export const LANGUAGES: Record<string, { monaco: string; label: string; template: string }> = {
  python: {
    monaco: 'python',
    label: 'Python 3',
    template: `import sys

def main():
    data = sys.stdin.read().split()
    # TODO: решить задачу
    pass

main()
`,
  },
  java: {
    monaco: 'java',
    label: 'Java 17',
    template: `import java.util.*;

public class Main {
    public static void main(String[] args) {
        Scanner sc = new Scanner(System.in);
        // TODO: решить задачу
    }
}
`,
  },
  cpp: {
    monaco: 'cpp',
    label: 'C++17',
    template: `#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // TODO: решить задачу
    return 0;
}
`,
  },
  javascript: {
    monaco: 'javascript',
    label: 'JavaScript (Node 20)',
    template: `const data = require('fs').readFileSync(0, 'utf8').split(/\\s+/).filter(Boolean);

// TODO: решить задачу
`,
  },
};

export const LEVEL_LABELS: Record<string, string> = {
  junior: 'Junior',
  middle: 'Middle',
  senior: 'Senior',
};

export const PATTERN_LABELS: Record<string, string> = {
  two_pointers: 'Два указателя',
  sliding_window: 'Скользящее окно',
  prefix_sum: 'Префиксная сумма',
  binary_search: 'Бинарный поиск',
  sorting: 'Сортировки / D&C',
  dfs: 'DFS / Графы',
  bfs: 'BFS',
  dp: 'Динамическое программирование',
  greedy: 'Жадные алгоритмы',
  heap: 'Куча / Priority Queue',
  trie: 'Префиксное дерево',
  math: 'Математика (Евклид)',
  linked_list: 'Связные списки (Флойд)',
};

export const STATUS_LABELS: Record<string, string> = {
  accepted: 'Принято',
  wrong_answer: 'Неверный ответ',
  runtime_error: 'Ошибка выполнения',
  compile_error: 'Ошибка компиляции',
  timeout: 'Таймаут / память',
  internal_error: 'Внутренняя ошибка',
  pending: 'В очереди',
};

// ---------- Резюме ----------

export interface TechStackItem {
  name: string;
  category: 'language' | 'framework' | 'database' | 'tool';
}

export interface ResumeProjectItem { name: string; problem: string; tech_stack: string[] }
export interface ResumeLabItem { subject: string; work_name: string; goal: string; tech_stack: string[] }
export interface ResumeInternshipItem { city: string; organization: string; period: string; goal: string }
export interface ResumeCourseItem { month_year: string; name: string; tech_stack: string[] }
export interface ResumeHackathonItem { name: string; organizer: string; location: string; month_year: string; role: string; tech_stack: string[] }
export interface ResumeLabMembership {
  university: string; department: string; department_url: string; supervisor: string;
  own_project: string; other_projects: string[];
}

export interface ResumeData {
  last_name: string; first_name: string; middle_name: string; gender: string;
  city: string; phone: string; birth_day: string; birth_month: string; birth_year: string;
  citizenship: string; work_permit: string;
  university: string; faculty: string; department: string; major: string; graduation_year: string;
  github: string; gitverse: string; gitflic: string;
  projects: ResumeProjectItem[]; labs: ResumeLabItem[]; internships: ResumeInternshipItem[];
  courses: ResumeCourseItem[]; hackathons: ResumeHackathonItem[];
  lab_membership: ResumeLabMembership | null;
}

export interface SkillsSummary {
  hard_skills: string[]; tools: string[]; algorithms: string[];
  position: { position: string; reasons: string[] };
}

export interface ResumeResponse {
  data: ResumeData;
  completion: { ready: boolean; missing: string[] };
  skills: SkillsSummary;
  solved: { count: number; tasks: { title: string; pattern_ru: string; level: string }[] };
  updated_at: string | null;
}

export const EMPTY_RESUME: ResumeData = {
  last_name: '', first_name: '', middle_name: '', gender: '',
  city: '', phone: '', birth_day: '', birth_month: '', birth_year: '',
  citizenship: '', work_permit: '',
  university: '', faculty: '', department: '', major: '', graduation_year: '',
  github: '', gitverse: '', gitflic: '',
  projects: [], labs: [], internships: [], courses: [], hackathons: [],
  lab_membership: null,
};

// Скачивает файл как blob и запускает сохранение через временный <a>.
export async function downloadFile(path: string, filename: string): Promise<void> {
  const resp = await authFetch(path, {});
  if (!resp.ok) throw new Error(`HTTP ${resp.status}`);
  const blob = await resp.blob();
  const url = URL.createObjectURL(blob);
  const aEl = document.createElement('a');
  aEl.href = url;
  aEl.download = filename;
  aEl.click();
  URL.revokeObjectURL(url);
}


// ---------- LLM-очередь (job + поллинг) ----------

export interface LLMJob {
  id: number;
  kind: string;
  status: 'pending' | 'running' | 'done' | 'error' | 'cancelled';
  position: number;
  result: string | null;
  error: string | null;
}

export interface LLMJobSubmit {
  kind: string;
  messages?: { role: string; content: string }[];
  temperature?: number;
  max_tokens?: number;
  meta?: Record<string, unknown>;
}

export async function submitLlmJob(payload: LLMJobSubmit): Promise<LLMJob> {
  return api<LLMJob>('/api/llm/jobs', { method: 'POST', body: JSON.stringify(payload) });
}

export async function getLlmJob(id: number): Promise<LLMJob> {
  return api<LLMJob>(`/api/llm/jobs/${id}`);
}

export async function getLlmJobs(ids: number[]): Promise<LLMJob[]> {
  return api<LLMJob[]>(`/api/llm/jobs?ids=${ids.join(',')}`);
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

/** Поллинг job'а до завершения. onProgress — обновления статуса/позиции для UI. */
export async function pollLlmJob(
  id: number,
  onProgress?: (job: LLMJob) => void,
  intervalMs = 3000,
): Promise<LLMJob> {
  for (;;) {
    const job = await getLlmJob(id);
    onProgress?.(job);
    if (job.status === 'done' || job.status === 'error' || job.status === 'cancelled') return job;
    await sleep(intervalMs);
  }
}

/** Пакетный поллинг до завершения всех job'ов. */
export async function pollLlmJobs(
  ids: number[],
  onProgress?: (jobs: LLMJob[]) => void,
  intervalMs = 3000,
): Promise<LLMJob[]> {
  for (;;) {
    const jobs = await getLlmJobs(ids);
    onProgress?.(jobs);
    if (jobs.length === ids.length && jobs.every((j) => j.status !== 'pending' && j.status !== 'running')) return jobs;
    await sleep(intervalMs);
  }
}

// ---------- Вайб-кодинг ----------

export interface VibeTaskListItem {
  id: number; slug: string; task_type: string; title: string;
  status: string | null; score: number | null;
}

export interface VibeSession {
  id: number; task_id: number; slug: string; task_type: string; title: string;
  description_md: string; initial_code: string; status: string;
  messages: { role: string; content: string }[];
  code: string; prompts_count: number; run_count: number;
  last_run: any; score: number | null;
}

export interface VibeRunResult {
  status: string;
  results: { name: string; passed: boolean; detail?: string }[];
  mutation: any | null;
  passed: boolean;
  score: number;
  breakdown: Record<string, number | string>;
}

export interface VibeAdminTask {
  id: number; slug: string; task_type: string; title: string; description_md: string;
  initial_code: string; hidden_tests: any[]; reference_solution: string;
  mutants: any[]; min_mutants_caught: number; enabled: boolean;
}
