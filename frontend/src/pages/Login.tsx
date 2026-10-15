// Страница входа/регистрации; после успеха — редирект на /.
import { FormEvent, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { useAuth } from '../auth';

export default function Login() {
  const { login, register } = useAuth();
  const navigate = useNavigate();
  const [mode, setMode] = useState<'login' | 'register'>('login');
  const [email, setEmail] = useState('');
  const [username, setUsername] = useState('');
  const [password, setPassword] = useState('');
  const [error, setError] = useState('');
  const [busy, setBusy] = useState(false);

  const submit = async (e: FormEvent) => {
    e.preventDefault();
    setError('');
    setBusy(true);
    try {
      if (mode === 'login') await login(email.trim(), password);
      else await register(email.trim(), username.trim(), password);
      navigate('/');
    } catch (err: any) {
      setError(err.message);
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="login-wrap">
      <h1>
        IT<span style={{ color: 'var(--accent)' }}>Interview</span>
      </h1>
      <p className="muted">Тренажёр алгоритмических собеседований</p>
      <div className="tabs">
        <button className={mode === 'login' ? 'active' : ''} onClick={() => setMode('login')}>
          Вход
        </button>
        <button className={mode === 'register' ? 'active' : ''} onClick={() => setMode('register')}>
          Регистрация
        </button>
      </div>
      <form className="card" onSubmit={submit}>
        <div className="form-row">
          <label>{mode === 'login' ? 'Email или имя пользователя' : 'Email'}</label>
          <input className="input" value={email} onChange={(e) => setEmail(e.target.value)} required autoFocus />
        </div>
        {mode === 'register' && (
          <div className="form-row">
            <label>Имя пользователя</label>
            <input className="input" value={username} onChange={(e) => setUsername(e.target.value)} minLength={2} required />
          </div>
        )}
        <div className="form-row">
          <label>Пароль</label>
          <input className="input" type="password" value={password} onChange={(e) => setPassword(e.target.value)} minLength={6} required />
        </div>
        {error && <div className="error-text">{error}</div>}
        <button className="btn" style={{ width: '100%' }} disabled={busy}>
          {busy ? 'Подождите…' : mode === 'login' ? 'Войти' : 'Создать аккаунт'}
        </button>
      </form>
    </div>
  );
}
