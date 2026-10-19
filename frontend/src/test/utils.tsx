/**
 * Utilitários de renderização do painel admin para os testes.
 *
 * Contratos de produção exigidos (Feature 5):
 * - `src/admin/api/client.ts` exporta TOKEN_STORAGE_KEY e USER_STORAGE_KEY (chaves do localStorage
 *   onde a sessão fica salva: token JWT em texto e usuário {id,nome,email} em JSON).
 * - `src/admin/auth/AuthProvider.tsx` exporta `AuthProvider` (lê a sessão salva no mount).
 * - `src/admin/AdminRoutes.tsx` exporta `AdminRoutes`: somente as <Routes> do admin (sem Router e
 *   sem QueryClientProvider), para os testes montarem com MemoryRouter + QueryClient de teste.
 * Páginas/componentes NÃO podem criar o próprio QueryClient (usam o do provider).
 */
import { ReactElement, ReactNode } from 'react';
import { render } from '@testing-library/react';
import userEvent from '@testing-library/user-event';
import { QueryClient, QueryClientProvider } from '@tanstack/react-query';
import { MemoryRouter, useLocation } from 'react-router-dom';
import { TOKEN_STORAGE_KEY, USER_STORAGE_KEY } from '../admin/api/client';
import { AuthProvider } from '../admin/auth/AuthProvider';
import { AdminRoutes } from '../admin/AdminRoutes';
import { ADMIN_TESTE, TOKEN_TESTE } from './handlers';

export function createTestQueryClient(): QueryClient {
  return new QueryClient({
    defaultOptions: {
      queries: { retry: false, gcTime: Infinity },
      mutations: { retry: false },
    },
  });
}

/** Simula sessão já autenticada (token + usuário salvos), como após um login bem-sucedido. */
export function loginComo(usuario = ADMIN_TESTE, token = TOKEN_TESTE): void {
  window.localStorage.setItem(TOKEN_STORAGE_KEY, token);
  window.localStorage.setItem(USER_STORAGE_KEY, JSON.stringify(usuario));
}

/** Exibe o pathname atual do MemoryRouter em data-testid="location" (para checar redirecionamentos). */
export function LocationDisplay(): ReactElement {
  const location = useLocation();
  return <div data-testid="location">{location.pathname}</div>;
}

type Opcoes = { route?: string; autenticado?: boolean; queryClient?: QueryClient };

function Providers({ children, route, queryClient }: { children: ReactNode; route: string; queryClient: QueryClient }) {
  return (
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={[route]}>
        <AuthProvider>
          {children}
          <LocationDisplay />
        </AuthProvider>
      </MemoryRouter>
    </QueryClientProvider>
  );
}

/** Renderiza a árvore de rotas completa do admin (`AdminRoutes`) na rota indicada. */
export function renderAdmin({ route = '/admin', autenticado = true, queryClient = createTestQueryClient() }: Opcoes = {}) {
  if (autenticado) loginComo();
  const user = userEvent.setup();
  const utils = render(
    <Providers route={route} queryClient={queryClient}>
      <AdminRoutes />
    </Providers>,
  );
  return { user, queryClient, ...utils };
}

/** Renderiza um componente isolado com QueryClient, MemoryRouter e AuthProvider. */
export function renderWithProviders(
  ui: ReactElement,
  { route = '/admin', autenticado = true, queryClient = createTestQueryClient() }: Opcoes = {},
) {
  if (autenticado) loginComo();
  const user = userEvent.setup();
  const utils = render(
    <Providers route={route} queryClient={queryClient}>
      {ui}
    </Providers>,
  );
  return { user, queryClient, ...utils };
}
