/**
 * Feature 5 - Autenticação do painel admin: AuthProvider/useAuth, LoginPage, ProtectedRoute e logout.
 *
 * Contratos:
 * - `src/admin/auth/AuthProvider.tsx`: `AuthProvider` e `useAuth()` ->
 *     { usuario: {id,nome,email} | null, token: string | null, isAuthenticated: boolean,
 *       login(email, senha): Promise<void>, logout(): void }
 *   Estado inicial lido da sessão salva (client.ts). `login` chama POST /auth/login {email, senha} e
 *   salva token + usuário (setSession). `logout` limpa a sessão. Um 401 global (onUnauthorized) desloga.
 *   `useAuth` fora do provider lança erro.
 * - `src/admin/auth/ProtectedRoute.tsx`: `ProtectedRoute` ({children}) redireciona para /admin/login
 *   (guardando a rota pedida em location.state.from) quando não autenticado.
 * - `src/admin/pages/LoginPage.tsx` (rota /admin/login): campos com label "E-mail" e "Senha",
 *   botão "Entrar". Validação local: "Informe o e-mail", "E-mail inválido", "Informe a senha" (sem chamar a API).
 *   401 -> role="alert" com "E-mail ou senha inválidos." (genérico); 429 -> alert com "Muitas tentativas...".
 *   Sucesso -> navega para a rota pedida originalmente (state.from) ou /admin.
 *   Usuário já autenticado em /admin/login -> redireciona para /admin.
 * - Layout: botão "Sair" desloga e volta para /admin/login.
 */
import { renderHook, screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from '../api/client';
import { useAuth } from './AuthProvider';
import { server } from '../../test/server';
import { ADMIN_TESTE, API, RESUMO_PADRAO, paginado } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

function handlersDoPainel() {
  server.use(
    http.get(`${API}/dashboard/resumo`, () => HttpResponse.json(RESUMO_PADRAO)),
    http.get(`${API}/dashboard/atividades`, () => HttpResponse.json([])),
    http.get(`${API}/associados/`, () => HttpResponse.json(paginado([]))),
  );
}

function loginOk(capturar?: (corpo: unknown) => void) {
  server.use(
    http.post(`${API}/auth/login`, async ({ request }) => {
      capturar?.(await request.json());
      return HttpResponse.json({ access_token: 'jwt-novo', token_type: 'bearer', usuario: ADMIN_TESTE });
    }),
  );
}

describe('useAuth', () => {
  it('lança erro fora do AuthProvider', () => {
    expect(() => renderHook(() => useAuth())).toThrow();
  });
});

describe('ProtectedRoute', () => {
  it('sem token redireciona /admin para /admin/login', async () => {
    renderAdmin({ route: '/admin', autenticado: false });

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/admin/login'));
    expect(screen.getByRole('button', { name: 'Entrar' })).toBeInTheDocument();
  });

  it('sem token não renderiza o conteúdo protegido', async () => {
    renderAdmin({ route: '/admin/associados', autenticado: false });

    await screen.findByRole('button', { name: 'Entrar' });
    expect(screen.queryByRole('navigation', { name: 'Menu principal' })).not.toBeInTheDocument();
  });
});

describe('LoginPage', () => {
  it('valida campos obrigatórios sem chamar a API', async () => {
    let chamadas = 0;
    server.use(
      http.post(`${API}/auth/login`, () => {
        chamadas += 1;
        return HttpResponse.json({}, { status: 500 });
      }),
    );
    const { user } = renderAdmin({ route: '/admin/login', autenticado: false });

    await user.click(await screen.findByRole('button', { name: 'Entrar' }));

    expect(await screen.findByText(/informe o e-mail/i)).toBeInTheDocument();
    expect(screen.getByText(/informe a senha/i)).toBeInTheDocument();
    expect(chamadas).toBe(0);
  });

  it('valida formato do e-mail', async () => {
    const { user } = renderAdmin({ route: '/admin/login', autenticado: false });

    await user.type(await screen.findByLabelText('E-mail'), 'diretoria');
    await user.type(screen.getByLabelText('Senha'), 'qualquer');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByText(/e-mail inválido/i)).toBeInTheDocument();
  });

  it('campo de senha é do tipo password', async () => {
    renderAdmin({ route: '/admin/login', autenticado: false });
    expect(await screen.findByLabelText('Senha')).toHaveAttribute('type', 'password');
  });

  it('401 exibe mensagem genérica e não salva sessão', async () => {
    server.use(
      http.post(`${API}/auth/login`, () => HttpResponse.json({ detail: 'Credenciais inválidas' }, { status: 401 })),
    );
    const { user } = renderAdmin({ route: '/admin/login', autenticado: false });

    await user.type(await screen.findByLabelText('E-mail'), 'diretoria@clubmaravilha.com.br');
    await user.type(screen.getByLabelText('Senha'), 'errada');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent('E-mail ou senha inválidos.');
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(screen.getByTestId('location')).toHaveTextContent('/admin/login');
  });

  it('429 informa excesso de tentativas', async () => {
    server.use(
      http.post(`${API}/auth/login`, () =>
        HttpResponse.json({ detail: 'Muitas tentativas' }, { status: 429, headers: { 'Retry-After': '60' } }),
      ),
    );
    const { user } = renderAdmin({ route: '/admin/login', autenticado: false });

    await user.type(await screen.findByLabelText('E-mail'), 'diretoria@clubmaravilha.com.br');
    await user.type(screen.getByLabelText('Senha'), 'errada');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    expect(await screen.findByRole('alert')).toHaveTextContent(/muitas tentativas/i);
  });

  it('login com sucesso salva o token e redireciona para o dashboard', async () => {
    handlersDoPainel();
    let corpo: unknown = null;
    loginOk((c) => (corpo = c));
    const { user } = renderAdmin({ route: '/admin/login', autenticado: false });

    await user.type(await screen.findByLabelText('E-mail'), 'diretoria@clubmaravilha.com.br');
    await user.type(screen.getByLabelText('Senha'), 'SenhaForte!2026');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/admin$/));
    expect(corpo).toEqual({ email: 'diretoria@clubmaravilha.com.br', senha: 'SenhaForte!2026' });
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBe('jwt-novo');
    expect(JSON.parse(window.localStorage.getItem(USER_STORAGE_KEY)!)).toEqual(ADMIN_TESTE);
    const nav = await screen.findByRole('navigation', { name: 'Menu principal' });
    expect(nav).toBeInTheDocument();
    expect(screen.getByText(ADMIN_TESTE.nome)).toBeInTheDocument();
  });

  it('após login volta para a rota protegida pedida originalmente', async () => {
    handlersDoPainel();
    loginOk();
    const { user } = renderAdmin({ route: '/admin/associados', autenticado: false });

    await user.type(await screen.findByLabelText('E-mail'), 'diretoria@clubmaravilha.com.br');
    await user.type(screen.getByLabelText('Senha'), 'SenhaForte!2026');
    await user.click(screen.getByRole('button', { name: 'Entrar' }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/admin/associados'));
  });

  it('usuário autenticado em /admin/login vai direto para /admin', async () => {
    handlersDoPainel();
    renderAdmin({ route: '/admin/login', autenticado: true });

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/admin$/));
  });
});

describe('logout', () => {
  it('botão Sair limpa a sessão e volta ao login', async () => {
    server.use(
      http.get(`${API}/dashboard/resumo`, () => HttpResponse.json(RESUMO_PADRAO)),
      http.get(`${API}/dashboard/atividades`, () => HttpResponse.json([])),
    );
    const { user } = renderAdmin({ route: '/admin' });

    const nav = await screen.findByRole('navigation', { name: 'Menu principal' });
    expect(within(document.body).getByText(ADMIN_TESTE.nome)).toBeInTheDocument();
    expect(nav).toBeInTheDocument();
    await user.click(screen.getByRole('button', { name: 'Sair' }));

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/admin/login'));
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(window.localStorage.getItem(USER_STORAGE_KEY)).toBeNull();
  });

  it('401 de uma chamada protegida desloga e leva ao login', async () => {
    server.use(
      http.get(`${API}/dashboard/resumo`, () => HttpResponse.json({ detail: 'Token expirado' }, { status: 401 })),
      http.get(`${API}/dashboard/atividades`, () => HttpResponse.json({ detail: 'Token expirado' }, { status: 401 })),
    );
    renderAdmin({ route: '/admin' });

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent('/admin/login'));
    expect(window.localStorage.getItem(TOKEN_STORAGE_KEY)).toBeNull();
    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeInTheDocument();
  });
});
