/**
 * Feature 5 - Roteamento do painel admin (react-router-dom v6) e layout base.
 *
 * Contratos:
 * - `src/admin/AdminRoutes.tsx` exporta `AdminRoutes` (apenas <Routes>, caminhos absolutos):
 *     /admin/login          -> LoginPage (pública)
 *     /admin                -> ProtectedRoute + AdminLayout (com <Outlet/>), índice = DashboardPage
 *     /admin/associados     -> AssociadosPage
 *     /admin/mensalidades   -> MensalidadesPage com <h1>"Mensalidades"</h1> (Feature 6; substituiu o placeholder)
 *     /admin/whatsapp       -> WhatsAppConfigPage com <h1>"WhatsApp & Configurações"</h1> (Feature 6; idem)
 *     /admin/<desconhecida> -> redireciona para /admin
 * - `src/admin/AdminApp.tsx` exporta `AdminApp`: QueryClientProvider + BrowserRouter + AuthProvider + AdminRoutes.
 * - `src/admin/layout/AdminLayout.tsx` exporta `AdminLayout` (sidebar desktop-first):
 *     <nav aria-label="Menu principal"> com links (ícone lucide <svg> em cada um):
 *       "Dashboard" (/admin), "Associados" (/admin/associados), "Mensalidades" (/admin/mensalidades),
 *       "WhatsApp & Configurações" (/admin/whatsapp); link ativo com aria-current="page".
 *     Nome do usuário logado, botão "Sair" e indicador data-testid="whatsapp-indicator" com o rótulo do
 *     GET /whatsapp/status ("Conectado" | "Desconectado" | "Aguardando QR Code"; falha -> "Desconectado").
 */
import { screen, waitFor, within } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it } from 'vitest';
import { server } from '../test/server';
import { ADMIN_TESTE, API, RESUMO_PADRAO } from '../test/handlers';
import { renderAdmin } from '../test/utils';

const LINKS = [
  ['Dashboard', '/admin'],
  ['Associados', '/admin/associados'],
  ['Mensalidades', '/admin/mensalidades'],
  ['WhatsApp & Configurações', '/admin/whatsapp'],
] as const;

describe('rotas do admin', () => {
  // Feature 6: os placeholders deram lugar às páginas reais (MensalidadesPage e WhatsAppConfigPage).
  it('/admin/mensalidades renderiza a MensalidadesPage dentro do layout', async () => {
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByRole('heading', { level: 1, name: 'Mensalidades' })).toBeInTheDocument();
    expect(screen.getByRole('navigation', { name: 'Menu principal' })).toBeInTheDocument();
    expect(await screen.findByRole('button', { name: 'Gerar faturas do mês' })).toBeInTheDocument();
    expect(screen.queryByText(/em desenvolvimento/i)).not.toBeInTheDocument();
  });

  it('/admin/whatsapp renderiza a WhatsAppConfigPage dentro do layout', async () => {
    renderAdmin({ route: '/admin/whatsapp' });

    expect(await screen.findByRole('heading', { level: 1, name: 'WhatsApp & Configurações' })).toBeInTheDocument();
    expect(await screen.findByRole('region', { name: 'Conexão' })).toBeInTheDocument();
    expect(screen.queryByText(/em desenvolvimento/i)).not.toBeInTheDocument();
  });

  it('rota desconhecida do admin volta para /admin', async () => {
    server.use(
      http.get(`${API}/dashboard/resumo`, () => HttpResponse.json(RESUMO_PADRAO)),
      http.get(`${API}/dashboard/atividades`, () => HttpResponse.json([])),
    );
    renderAdmin({ route: '/admin/nao-existe' });

    await waitFor(() => expect(screen.getByTestId('location')).toHaveTextContent(/^\/admin$/));
  });
});

describe('AdminLayout', () => {
  it('sidebar com os 4 itens de navegação, ícones e links corretos', async () => {
    renderAdmin({ route: '/admin/mensalidades' });

    const nav = await screen.findByRole('navigation', { name: 'Menu principal' });
    for (const [nome, href] of LINKS) {
      const link = within(nav).getByRole('link', { name: nome });
      expect(link).toHaveAttribute('href', href);
      expect(link.querySelector('svg')).not.toBeNull();
    }
  });

  it('marca o item ativo com aria-current="page"', async () => {
    renderAdmin({ route: '/admin/mensalidades' });

    const nav = await screen.findByRole('navigation', { name: 'Menu principal' });
    expect(within(nav).getByRole('link', { name: 'Mensalidades' })).toHaveAttribute('aria-current', 'page');
    expect(within(nav).getByRole('link', { name: 'Dashboard' })).not.toHaveAttribute('aria-current', 'page');
  });

  it('navega pela sidebar', async () => {
    const { user } = renderAdmin({ route: '/admin/mensalidades' });

    const nav = await screen.findByRole('navigation', { name: 'Menu principal' });
    await user.click(within(nav).getByRole('link', { name: 'WhatsApp & Configurações' }));

    expect(await screen.findByRole('heading', { level: 1, name: 'WhatsApp & Configurações' })).toBeInTheDocument();
    expect(screen.getByTestId('location')).toHaveTextContent('/admin/whatsapp');
  });

  it('exibe nome do usuário logado e botão Sair', async () => {
    renderAdmin({ route: '/admin/mensalidades' });

    expect(await screen.findByText(ADMIN_TESTE.nome)).toBeInTheDocument();
    expect(screen.getByRole('button', { name: 'Sair' })).toBeInTheDocument();
  });

  it.each([
    ['CONECTADO', 'Conectado'],
    ['DESCONECTADO', 'Desconectado'],
    ['AGUARDANDO_QRCODE', 'Aguardando QR Code'],
  ])('indicador do WhatsApp: %s -> %s', async (status, rotulo) => {
    server.use(http.get(`${API}/whatsapp/status`, () => HttpResponse.json({ status })));
    renderAdmin({ route: '/admin/mensalidades' });

    const indicador = await screen.findByTestId('whatsapp-indicator');
    await waitFor(() => expect(indicador).toHaveTextContent(rotulo));
    if (rotulo === 'Conectado') expect(indicador).not.toHaveTextContent('Desconectado');
  });

  it('indicador do WhatsApp mostra Desconectado quando o status falha', async () => {
    server.use(http.get(`${API}/whatsapp/status`, () => HttpResponse.json({ detail: 'erro' }, { status: 502 })));
    renderAdmin({ route: '/admin/mensalidades' });

    const indicador = await screen.findByTestId('whatsapp-indicator');
    await waitFor(() => expect(indicador).toHaveTextContent('Desconectado'));
  });
});
