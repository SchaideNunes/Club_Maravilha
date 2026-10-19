/**
 * Feature 5 - Dashboard operacional (`src/admin/pages/DashboardPage.tsx`, rota índice /admin).
 *
 * Contratos:
 * - Exporta `DashboardPage` e `DASHBOARD_REFETCH_INTERVAL_MS = 15000` (polling via react-query
 *   `refetchInterval`) aplicado a GET /dashboard/resumo e GET /dashboard/atividades.
 * - 5 cards (cada um com data-testid e o título visível):
 *     card-total-associados    "Total de Associados"     -> total_associados
 *     card-pagas-mes           "Pagas no Mês"            -> faturas_pagas_mes
 *     card-pendentes-atrasadas "Pendentes / Atrasadas"   -> faturas_pendentes_mes e faturas_atrasadas
 *     card-disparos-hoje       "Disparos Hoje"           -> disparos_hoje e "<n> com erro" (disparos_erro_hoje)
 *     card-whatsapp-status     "Status WhatsApp"         -> "Conectado" | "Desconectado" | "Aguardando QR Code"
 * - Lista <ul aria-label="Atividades recentes"> com um <li> por atividade: selo "Disparo" ou "Baixa",
 *   descrição, nome do associado (quando houver), data/hora "dd/mm/aaaa HH:mm" (fuso do clube) e,
 *   para disparos com status ERRO, o selo "Erro".
 * - Estados: carregando (texto "Carregando..."), erro (role="alert" com "Não foi possível carregar..."),
 *   vazio ("Nenhuma atividade recente").
 */
import { act, screen, waitFor, within } from '@testing-library/react';
import { delay, http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { DASHBOARD_REFETCH_INTERVAL_MS } from './DashboardPage';
import { server } from '../../test/server';
import { API, RESUMO_PADRAO } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const ATIVIDADES = [
  {
    tipo: 'DISPARO',
    data: '2026-10-15T13:00:00Z',
    descricao: 'Lembrete D-3 enviado',
    associado_nome: 'Maria Souza',
    status: 'SUCESSO',
  },
  {
    tipo: 'DISPARO',
    data: '2026-10-15T12:00:00Z',
    descricao: 'Lembrete D0 não enviado',
    associado_nome: 'João Lima',
    status: 'ERRO',
  },
  {
    tipo: 'BAIXA',
    data: '2026-10-14T18:45:00Z',
    descricao: 'Mensalidade 2026-10 quitada via PIX',
    associado_nome: 'Ana Costa',
    status: 'PAGO',
  },
];

function contarRequisicoes(resumo = RESUMO_PADRAO, atividades: unknown = ATIVIDADES) {
  const contagem = { resumo: 0, atividades: 0 };
  server.use(
    http.get(`${API}/dashboard/resumo`, () => {
      contagem.resumo += 1;
      return HttpResponse.json(resumo);
    }),
    http.get(`${API}/dashboard/atividades`, () => {
      contagem.atividades += 1;
      return HttpResponse.json(atividades);
    }),
  );
  return contagem;
}

describe('DashboardPage - cards', () => {
  it('exibe os 5 cards com os valores do resumo', async () => {
    contarRequisicoes();
    renderAdmin({ route: '/admin' });

    const total = await screen.findByTestId('card-total-associados');
    expect(within(total).getByText('Total de Associados')).toBeInTheDocument();
    expect(total).toHaveTextContent('312');

    const pagas = screen.getByTestId('card-pagas-mes');
    expect(within(pagas).getByText('Pagas no Mês')).toBeInTheDocument();
    expect(pagas).toHaveTextContent('120');

    const pendentes = screen.getByTestId('card-pendentes-atrasadas');
    expect(within(pendentes).getByText('Pendentes / Atrasadas')).toBeInTheDocument();
    expect(pendentes).toHaveTextContent('45');
    expect(pendentes).toHaveTextContent('12');

    const disparos = screen.getByTestId('card-disparos-hoje');
    expect(within(disparos).getByText('Disparos Hoje')).toBeInTheDocument();
    expect(disparos).toHaveTextContent('30');
    expect(disparos).toHaveTextContent(/2 com erro/i);

    const whatsapp = screen.getByTestId('card-whatsapp-status');
    expect(within(whatsapp).getByText('Status WhatsApp')).toBeInTheDocument();
    expect(within(whatsapp).getByText('Conectado')).toBeInTheDocument();
  });

  it.each([
    ['CONECTADO', 'Conectado'],
    ['DESCONECTADO', 'Desconectado'],
    ['AGUARDANDO_QRCODE', 'Aguardando QR Code'],
  ])('card de WhatsApp: %s -> %s', async (status, rotulo) => {
    contarRequisicoes({ ...RESUMO_PADRAO, whatsapp_status: status });
    renderAdmin({ route: '/admin' });

    const card = await screen.findByTestId('card-whatsapp-status');
    expect(within(card).getByText(rotulo)).toBeInTheDocument();
  });

  it('mostra carregando enquanto o resumo não chega', async () => {
    server.use(
      http.get(`${API}/dashboard/resumo`, async () => {
        await delay('infinite');
        return HttpResponse.json(RESUMO_PADRAO);
      }),
      http.get(`${API}/dashboard/atividades`, async () => {
        await delay('infinite');
        return HttpResponse.json([]);
      }),
    );
    renderAdmin({ route: '/admin' });

    expect((await screen.findAllByText(/carregando/i)).length).toBeGreaterThan(0);
    expect(screen.queryByText('312')).not.toBeInTheDocument();
  });

  it('mostra erro quando o resumo falha', async () => {
    server.use(
      http.get(`${API}/dashboard/resumo`, () => HttpResponse.json({ detail: 'erro' }, { status: 500 })),
      http.get(`${API}/dashboard/atividades`, () => HttpResponse.json([])),
    );
    renderAdmin({ route: '/admin' });

    const alerta = await screen.findByRole('alert');
    expect(alerta).toHaveTextContent(/não foi possível carregar/i);
  });
});

describe('DashboardPage - atividades recentes', () => {
  it('lista disparos e baixas com selo, associado e data pt-BR', async () => {
    contarRequisicoes();
    renderAdmin({ route: '/admin' });

    const lista = await screen.findByRole('list', { name: 'Atividades recentes' });
    const itens = await within(lista).findAllByRole('listitem');
    expect(itens).toHaveLength(3);

    expect(itens[0]).toHaveTextContent('Lembrete D-3 enviado');
    expect(itens[0]).toHaveTextContent('Maria Souza');
    expect(itens[0]).toHaveTextContent('15/10/2026 10:00');
    expect(within(itens[0]).getByText('Disparo')).toBeInTheDocument();

    expect(within(itens[1]).getByText('Erro')).toBeInTheDocument();
    expect(within(itens[0]).queryByText('Erro')).not.toBeInTheDocument();

    expect(within(itens[2]).getByText('Baixa')).toBeInTheDocument();
    expect(itens[2]).toHaveTextContent('Ana Costa');
    expect(itens[2]).toHaveTextContent('14/10/2026 15:45');
  });

  it('estado vazio', async () => {
    contarRequisicoes(RESUMO_PADRAO, []);
    renderAdmin({ route: '/admin' });

    expect(await screen.findByText('Nenhuma atividade recente')).toBeInTheDocument();
  });
});

describe('DashboardPage - polling', () => {
  it('intervalo de atualização é de 15 segundos', () => {
    expect(DASHBOARD_REFETCH_INTERVAL_MS).toBe(15000);
  });

  it('recarrega resumo e atividades a cada 15 s', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const contagem = contarRequisicoes();
    renderAdmin({ route: '/admin' });

    await screen.findByTestId('card-total-associados');
    await waitFor(() => {
      expect(contagem.resumo).toBe(1);
      expect(contagem.atividades).toBe(1);
    });

    await act(async () => {
      await vi.advanceTimersByTimeAsync(10_000);
    });
    expect(contagem.resumo).toBe(1);

    await act(async () => {
      await vi.advanceTimersByTimeAsync(DASHBOARD_REFETCH_INTERVAL_MS);
    });
    await waitFor(() => {
      expect(contagem.resumo).toBeGreaterThanOrEqual(2);
      expect(contagem.atividades).toBeGreaterThanOrEqual(2);
    });
  });
});
