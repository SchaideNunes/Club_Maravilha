import React, { createContext, useContext, useEffect, useState, useMemo } from 'react';
import {
  AdminUser,
  clearSession,
  getStoredUser,
  getToken,
  onUnauthorized,
  setSession,
  apiClient,
} from '../api/client';

export type AuthContextValue = {
  usuario: AdminUser | null;
  token: string | null;
  isAuthenticated: boolean;
  login: (email: string, senha: string) => Promise<void>;
  logout: () => void;
};

const AuthContext = createContext<AuthContextValue | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }): React.ReactElement {
  const [token, setTokenState] = useState<string | null>(() => getToken());
  const [usuario, setUsuarioState] = useState<AdminUser | null>(() => getStoredUser());

  const logout = React.useCallback(() => {
    clearSession();
    setTokenState(null);
    setUsuarioState(null);
  }, []);

  useEffect(() => {
    const unsubscribe = onUnauthorized(() => {
      logout();
    });
    return unsubscribe;
  }, [logout]);

  const login = React.useCallback(async (email: string, senha: string) => {
    const response = await apiClient.post<{
      access_token: string;
      token_type: string;
      usuario: AdminUser;
    }>('/auth/login', { email, senha });

    const { access_token, usuario: user } = response.data;
    setSession(access_token, user);
    setTokenState(access_token);
    setUsuarioState(user);
  }, []);

  const value = useMemo<AuthContextValue>(
    () => ({
      usuario,
      token,
      isAuthenticated: Boolean(token && usuario),
      login,
      logout,
    }),
    [usuario, token, login, logout],
  );

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>;
}

export function useAuth(): AuthContextValue {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth deve ser utilizado dentro de um AuthProvider.');
  }
  return context;
}
