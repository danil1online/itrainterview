import { Link, Navigate, Route, Routes } from 'react-router-dom';
import { useAuth } from './auth';
import Login from './pages/Login';
import Dashboard from './pages/Dashboard';
import Solve from './pages/Solve';
import MyStats from './pages/MyStats';
import Theory from './pages/Theory';
import VibeCoding from './pages/VibeCoding';
import Resume from './pages/Resume';
import Recruiter from './pages/Recruiter';
import Admin from './pages/Admin';

function Shell({ children }: { children: React.ReactNode }) {
  const { user, logout } = useAuth();
  return (
    <div className="shell">
      <header className="topbar">
        <Link to="/" className="brand">
          IT<span>Interview</span>
        </Link>
        <nav>
          <Link to="/theory">Теория</Link>
          <Link to="/">Задачи</Link>
          <Link to="/stats">Мой прогресс</Link>
          <Link to="/vibe">Вайб-Кодинг</Link>
          <Link to="/resume">Резюме</Link>
          <Link to="/recruiter">Рекрутёр</Link>
          {user?.role === 'admin' && <Link to="/admin">Администрирование</Link>}
        </nav>
        <div className="topbar-user">
          <span>{user?.username}</span>
          <button className="btn ghost" onClick={logout}>
            Выйти
          </button>
        </div>
      </header>
      <main>{children}</main>
    </div>
  );
}

function Protected({ children, admin }: { children: React.ReactNode; admin?: boolean }) {
  const { user, loading } = useAuth();
  if (loading) return <div className="center muted">Загрузка…</div>;
  if (!user) return <Navigate to="/login" replace />;
  if (admin && user.role !== 'admin') return <Navigate to="/" replace />;
  return <Shell>{children}</Shell>;
}

export default function App() {
  const { user, loading } = useAuth();
  return (
    <Routes>
      <Route path="/login" element={!loading && user ? <Navigate to="/" /> : <Login />} />
      <Route
        path="/"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/solve/:slug"
        element={
          <Protected>
            <Solve />
          </Protected>
        }
      />
      <Route
        path="/stats"
        element={
          <Protected>
            <MyStats />
          </Protected>
        }
      />
      <Route
        path="/theory"
        element={
          <Protected>
            <Theory />
          </Protected>
        }
      />
      <Route
        path="/vibe"
        element={
          <Protected>
            <VibeCoding />
          </Protected>
        }
      />
      <Route
        path="/resume"
        element={
          <Protected>
            <Resume />
          </Protected>
        }
      />
      <Route
        path="/recruiter"
        element={
          <Protected>
            <Recruiter />
          </Protected>
        }
      />
      <Route
        path="/admin/*"
        element={
          <Protected admin>
            <Admin />
          </Protected>
        }
      />
      <Route path="*" element={<Navigate to="/" />} />
    </Routes>
  );
}
