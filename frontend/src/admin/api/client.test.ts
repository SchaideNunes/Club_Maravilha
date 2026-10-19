/**
 * Feature 5 - Cliente HTTP do painel admin (`src/admin/api/client.ts`).
 *
 * Contrato:
 * - `apiClient`: instância axios com baseURL `${import.meta.env.VITE_API_URL}/api/v1`
 *   (fallback http://localhost:8000 quando a env não existe).
 * - Sessão no localStorage: `TOKEN_STORAGE_KEY` (JWT em texto) e `USER_STORAGE_KEY` (JSON {id,nome,email}).
 *   Helpers: `getToken()`, `getStoredUser()`, `setSession(token, usuario)`, `clearSession()`.
 * - Interceptor de request: injeta `Authorization: Bearer <token>` quando há token salvo (e não envia o
 *   header quando não há).
 * - Interceptor de response: 401 em qualquer rota EXCETO `/auth/login` limpa a sessão e notifica os
 *   ouvintes registrados com `onUnauthorized(listener)` (retorna função para cancelar a inscrição);
 *   a promise continua rejeitando com o erro original. Outros status (403/500) não deslogam.
 */
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import {
  TOKEN_STORAGE_KEY,
  USER_STORAGE_KEY,
  apiClient,
  clearSession,
  getStoredUser,
  getToken,
  onUnauthorized,
  setSession,
} from './client';
import { server } from '../../test/server';
import { ADMIN_TESTE, API } from '../../test/handlers';

describe('apiClient', () => {
  it('usa VITE_API_URL + /api/v1 como baseURL', () => {
    expect(apiClient.defaults.baseURL).toBe(`${import.meta.env.VITE_API_URL}/api/v1`);
    expect(apiClient.defaults.baseURL).toBe(API);
  });

  it('injeta Authorization Bearer com o token salvo', async () => {
    let auth: string | null = 'nao-chamado';
    server.use(
      http.get(`${API}/associados/`, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ items: [], total: 0, page: 1, page_size: 20, total_pages: 0 });
      }),
    );
    setSession('meu.jwt.token', ADMIN_TESTE);

    await apiClient.get('/associados/');

    expect(auth).toBe('Bearer meu.jwt.token');
  });

  it('não envia Authorization sem sessão', async () => {
    let auth: string | null = 'nao-chamado';
    server.use(
      http.get(`${API}/associados/`, ({ request }) => {
        auth = request.headers.get('authorization');
        return HttpResponse.json({ items: [] });
      }),
    );

    await apiClient.get('/associados/');

    expect(auth).toBeNull();
  });

  it('setSession/getToken/getStoredUser/clearSession usam o localStorage', () => {
    setSession('abc', ADMIN_TESTE);
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('abc');
    expect(JSON.parse(window.localStorage.getItem(USER_STORAGE_KEY)!)).toEqual(ADMIN_TESTE);
    expect(getToken()).toBe('abc');
    expect(getStoredUser()).toEqual(ADMIN_TESTE);

    clearSession();
    expect(getToken()).toBeNull();
    expect(getStoredUser()).toBeNull();
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
  });

  it('getStoredUser tolera JSON corrompido', () => {
    window.localStorage.setItem(USER_STORAGE_KEY, '{nao-e-json');
    expect(getStoredUser()).toBeNull();
  });

  it('401 limpa a sessão, notifica os ouvintes e rejeita a promise', async () => {
    server.use(http.get(`${API}/faturas/`, () => HttpResponse.json({ detail: 'Não autenticado' }, { status: 401 })));
    setSession('expirado', ADMIN_TESTE);
    const ouvinte = vi.fn();
    const cancelar = onUnauthorized(ouvinte);

    await expect(apiClient.get('/faturas/')).rejects.toMatchObject({ response: { status: 401 } });

    expect(ouvinte).toHaveBeenCalledTimes(1);
    expect(getToken()).toBeNull();
    expect(getStoredUser()).toBeNull();
    cancelar();
  });

  it('cancelar a inscrição para de notificar', async () => {
    server.use(http.get(`${API}/faturas/`, () => HttpResponse.json({ detail: 'x' }, { status: 401 })));
    const ouvinte = vi.fn();
    const cancelar = onUnauthorized(ouvinte);
    cancelar();

    await expect(apiClient.get('/faturas/')).rejects.toBeTruthy();

    expect(ouvinte).not.toHaveBeenCalled();
  });

  it('401 do próprio login não dispara logout global', async () => {
    server.use(
      http.post(`${API}/auth/login`, () => HttpResponse.json({ detail: 'Credenciais inválidas' }, { status: 401 })),
    );
    setSession('token-anterior', ADMIN_TESTE);
    const ouvinte = vi.fn();
    const cancelar = onUnauthorized(ouvinte);

    await expect(apiClient.post('/auth/login', { email: 'a@b.com', senha: 'x' })).rejects.toMatchObject({
      response: { status: 401 },
    });

    expect(ouvinte).not.toHaveBeenCalled();
    expect(getToken()).toBe('token-anterior');
    cancelar();
  });

  it.each([403, 500])('status %i não desloga', async (status) => {
    server.use(http.get(`${API}/faturas/`, () => HttpResponse.json({ detail: 'erro' }, { status })));
    setSession('valido', ADMIN_TESTE);
    const ouvinte = vi.fn();
    const cancelar = onUnauthorized(ouvinte);

    await expect(apiClient.get('/faturas/')).rejects.toBeTruthy();

    expect(ouvinte).not.toHaveBeenCalled();
    expect(getToken()).toBe('valido');
    cancelar();
  });
});
