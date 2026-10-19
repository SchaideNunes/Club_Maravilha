/**
 * Feature 5 - Estratégia de entrada: o painel admin vive em /admin/* sem tocar na landing/portal.
 *
 * Contrato:
 * - `src/Root.tsx` exporta `isAdminPath(pathname)` e `Root` (default e nomeado).
 *   `Root` escolhe pela URL no carregamento: pathname /admin ou /admin/... -> `<AdminApp/>`
 *   (BrowserRouter próprio); qualquer outro caminho -> `<App/>` (landing atual, com hash-routing intacto,
 *   inclusive o demo legado em #/admin).
 * - `src/main.tsx` renderiza `<Root />` (em vez de `<App />`).
 * - Produção: nginx/vercel já fazem fallback SPA para index.html, então /admin/* chega ao Root.
 */
import { render, screen } from '@testing-library/react';
import { afterEach, describe, expect, it, vi } from 'vitest';
import mainSource from './main.tsx?raw';
import Root, { isAdminPath } from './Root';

vi.mock('./App', () => ({ default: () => <div data-testid="landing-app">Landing</div> }));

afterEach(() => {
  window.history.pushState({}, '', '/');
});

describe('isAdminPath', () => {
  it.each([
    ['/admin', true],
    ['/admin/', true],
    ['/admin/login', true],
    ['/admin/associados', true],
    ['/', false],
    ['/administracao', false],
    ['/esportes', false],
  ])('%s -> %s', (caminho, esperado) => {
    expect(isAdminPath(caminho)).toBe(esperado);
  });
});

describe('Root', () => {
  it('em / continua renderizando a landing', () => {
    window.history.pushState({}, '', '/');
    render(<Root />);
    expect(screen.getByTestId('landing-app')).toBeInTheDocument();
  });

  it('o hash legado #/admin continua na landing (demo antigo intacto)', () => {
    window.history.pushState({}, '', '/#/admin');
    render(<Root />);
    expect(screen.getByTestId('landing-app')).toBeInTheDocument();
  });

  it('em /admin/login renderiza o painel admin (tela de login), não a landing', async () => {
    window.history.pushState({}, '', '/admin/login');
    render(<Root />);
    expect(await screen.findByRole('button', { name: 'Entrar' })).toBeInTheDocument();
    expect(screen.queryByTestId('landing-app')).not.toBeInTheDocument();
  });

  it('main.tsx monta o Root', () => {
    expect(mainSource).toMatch(/<Root\s*\/>/);
  });
});
