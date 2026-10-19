/**
 * Feature 6 - Polling da seção "Conexão" da `WhatsAppConfigPage` (react-query `refetchInterval`).
 *
 * Contratos:
 * - `WHATSAPP_STATUS_POLL_MS = 5000`: GET /whatsapp/status é refeito a cada 5 s enquanto a página
 *   estiver aberta (independente do polling de 15 s do indicador do AdminLayout).
 * - `WHATSAPP_QRCODE_POLL_MS = 2000`: enquanto status = AGUARDANDO_QRCODE, GET /whatsapp/qrcode é
 *   refeito a cada 2 s e a <img alt="QR Code do WhatsApp"> passa a mostrar o QR mais recente.
 * - Quando o status muda para CONECTADO (detectado pelo polling), o QR some e deixa de ser consultado.
 */
import { act, screen, waitFor } from '@testing-library/react';
import { http, HttpResponse } from 'msw';
import { describe, expect, it, vi } from 'vitest';
import { WHATSAPP_QRCODE_POLL_MS, WHATSAPP_STATUS_POLL_MS } from './WhatsAppConfigPage';
import { server } from '../../test/server';
import { API } from '../../test/handlers';
import { renderAdmin } from '../../test/utils';

const QR_1 = 'data:image/png;base64,QRCODE-UM';
const QR_2 = 'data:image/png;base64,QRCODE-DOIS';

function backendPolling(statusInicial: string) {
  let status = statusInicial;
  const contagem = { status: 0, qrcode: 0 };
  server.use(
    http.get(`${API}/whatsapp/status`, () => {
      contagem.status += 1;
      return HttpResponse.json({ status });
    }),
    http.get(`${API}/whatsapp/qrcode`, () => {
      contagem.qrcode += 1;
      const qrcode = status === 'AGUARDANDO_QRCODE' ? (contagem.qrcode === 1 ? QR_1 : QR_2) : null;
      return HttpResponse.json({ status, qrcode });
    }),
  );
  return {
    contagem,
    setStatus: (novo: string) => {
      status = novo;
    },
  };
}

async function avancar(ms: number) {
  await act(async () => {
    await vi.advanceTimersByTimeAsync(ms);
  });
}

describe('WhatsAppConfigPage - polling', () => {
  it('intervalos exportados', () => {
    expect(WHATSAPP_STATUS_POLL_MS).toBe(5000);
    expect(WHATSAPP_QRCODE_POLL_MS).toBe(2000);
    expect(WHATSAPP_QRCODE_POLL_MS).toBeLessThan(WHATSAPP_STATUS_POLL_MS);
  });

  it('recarrega o status a cada 5 s', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const backend = backendPolling('CONECTADO');
    renderAdmin({ route: '/admin/whatsapp' });

    await screen.findByTestId('whatsapp-connection-status');
    await avancar(100);
    const inicial = backend.contagem.status;
    expect(inicial).toBeGreaterThanOrEqual(1);

    await avancar(3000);
    expect(backend.contagem.status).toBe(inicial);

    await avancar(WHATSAPP_STATUS_POLL_MS);
    await waitFor(() => expect(backend.contagem.status).toBeGreaterThan(inicial));
  });

  it('aguardando QR: recarrega o QR a cada 2 s e atualiza a imagem', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const backend = backendPolling('AGUARDANDO_QRCODE');
    renderAdmin({ route: '/admin/whatsapp' });

    const img = await screen.findByRole('img', { name: 'QR Code do WhatsApp' });
    expect(img).toHaveAttribute('src', QR_1);
    const inicial = backend.contagem.qrcode;

    await avancar(WHATSAPP_QRCODE_POLL_MS + 100);

    await waitFor(() => expect(backend.contagem.qrcode).toBeGreaterThan(inicial));
    await waitFor(() =>
      expect(screen.getByRole('img', { name: 'QR Code do WhatsApp' })).toHaveAttribute('src', QR_2),
    );
  });

  it('ao conectar, o QR some e deixa de ser consultado', async () => {
    vi.useFakeTimers({ shouldAdvanceTime: true });
    const backend = backendPolling('AGUARDANDO_QRCODE');
    renderAdmin({ route: '/admin/whatsapp' });

    await screen.findByRole('img', { name: 'QR Code do WhatsApp' });
    backend.setStatus('CONECTADO');

    await avancar(WHATSAPP_STATUS_POLL_MS + 100);
    await waitFor(() => expect(screen.getByTestId('whatsapp-connection-status')).toHaveTextContent('Conectado'));
    await waitFor(() => expect(screen.queryByRole('img', { name: 'QR Code do WhatsApp' })).not.toBeInTheDocument());

    const consultas = backend.contagem.qrcode;
    await avancar(WHATSAPP_QRCODE_POLL_MS * 3);
    expect(backend.contagem.qrcode).toBe(consultas);
  });
});
