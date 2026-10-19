import axios, { AxiosError, InternalAxiosRequestConfig } from 'axios';

export const TOKEN_STORAGE_KEY = 'club_maravilha_admin_token';
export const USER_STORAGE_KEY = 'club_maravilha_admin_user';

export type AdminUser = {
  id: string;
  nome: string;
  email: string;
};

const baseURL = `${import.meta.env.VITE_API_URL || 'http://localhost:8000'}/api/v1`;

export const apiClient = axios.create({
  baseURL,
});

export function getToken(): string | null {
  return window.localStorage.getItem(TOKEN_STORAGE_KEY);
}

export function getStoredUser(): AdminUser | null {
  const item = window.localStorage.getItem(USER_STORAGE_KEY);
  if (!item) return null;
  try {
    return JSON.parse(item) as AdminUser;
  } catch {
    return null;
  }
}

export function setSession(token: string, usuario: AdminUser): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(usuario));
}

export function clearSession(): void {
  window.localStorage.removeItem(TOKEN_STORAGE_KEY);
  window.localStorage.removeItem(USER_STORAGE_KEY);
}

type UnauthorizedListener = () => void;
const unauthorizedListeners = new Set<UnauthorizedListener>();

export function onUnauthorized(listener: UnauthorizedListener): () => void {
  unauthorizedListeners.add(listener);
  return () => {
    unauthorizedListeners.delete(listener);
  };
}

function notifyUnauthorized(): void {
  unauthorizedListeners.forEach((fn) => {
    try {
      fn();
    } catch (err) {
      console.error('[apiClient] Erro ao notificar ouvinte 401', err);
    }
  });
}

apiClient.interceptors.request.use((config: InternalAxiosRequestConfig) => {
  const token = getToken();
  if (token) {
    config.headers.set('Authorization', `Bearer ${token}`);
  }
  return config;
});

apiClient.interceptors.response.use(
  (response) => response,
  (error: AxiosError) => {
    if (error.response?.status === 401) {
      const url = error.config?.url || '';
      const isLogin = url.includes('/auth/login');
      if (!isLogin) {
        clearSession();
        notifyUnauthorized();
      }
    }
    return Promise.reject(error);
  },
);
