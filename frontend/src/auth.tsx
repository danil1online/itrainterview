import { createContext, useContext, useEffect, useState, ReactNode } from 'react';
import { api, getTokens, setTokens, UserInfo } from './api';

interface AuthState {
  user: UserInfo | null;
  loading: boolean;
  login: (login: string, password: string) => Promise<void>;
  register: (email: string, username: string, password: string) => Promise<void>;
  logout: () => void;
}

const AuthContext = createContext<AuthState>(null as unknown as AuthState);

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    if (!getTokens()) {
      setLoading(false);
      return;
    }
    api<UserInfo>('/api/auth/me')
      .then(setUser)
      .catch(() => setTokens(null))
      .finally(() => setLoading(false));
  }, []);

  const login = async (loginStr: string, password: string) => {
    const tokens = await api<{ access_token: string; refresh_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ login: loginStr, password }),
    });
    setTokens(tokens);
    setUser(await api<UserInfo>('/api/auth/me'));
  };

  const register = async (email: string, username: string, password: string) => {
    const tokens = await api<{ access_token: string; refresh_token: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, username, password }),
    });
    setTokens(tokens);
    setUser(await api<UserInfo>('/api/auth/me'));
  };

  const logout = () => {
    setTokens(null);
    setUser(null);
  };

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  );
}

export const useAuth = () => useContext(AuthContext);
