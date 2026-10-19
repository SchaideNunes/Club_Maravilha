import React from 'react';
import { screen, act } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';

import { server } from '../../test/server';
import { API, RESUMO_PADRAO } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';
import { DASHBOARD_REFETCH_INTERVAL_MS } from './DashboardPage';

describe('DashboardPage Review (Item 15 - Resiliência de Polling)', () => {
  it('1º poll 200, 2º 500, avançar 15s mantém card-total-associados visível com cache', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });

    let chamadasResumo = 0;
    server.use(
      http.get(`${API}/dashboard/resumo`, () => {
        chamadasResumo += 1;
        if (chamadasResumo === 1) {
          return HttpResponse.json({
            ...RESUMO_PADRAO,
            total_associados: 312,
          });
        }
        // Segundo poll falha com erro 500 no servidor
        return HttpResponse.json({ detail: 'Instabilidade temporária' }, { status: 500 });
      }),
      http.get(`${API}/dashboard/atividades`, () => {
        return HttpResponse.json([]);
      }),
    );

    renderAdmin({ route: '/admin' });

    // Aguarda o primeiro poll resolver
    await act(async () => {
      await vi.advanceTimersByTimeAsync(50);
    });

    const cardTotal = await screen.findByTestId('card-total-associados');
    expect(cardTotal).toBeInTheDocument();
    expect(cardTotal).toHaveTextContent('312');

    // Avança 15 segundos (intervalo de refetch periódico)
    await act(async () => {
      await vi.advanceTimersByTimeAsync(DASHBOARD_REFETCH_INTERVAL_MS + 200);
    });

    // Mesmo com a falha do 2º poll, os cards não somem da tela
    expect(screen.getByTestId('card-total-associados')).toBeInTheDocument();
    expect(screen.getByTestId('card-total-associados')).toHaveTextContent('312');

    // Exibe aviso discreto de dados desatualizados
    expect(screen.getByRole('status')).toHaveTextContent(/dados desatualizados/i);

    vi.useRealTimers();
  });
});
