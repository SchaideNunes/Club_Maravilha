import request from 'supertest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp } from './app.js';
import { IWhatsAppGateway } from './services/whatsapp-gateway.interface.js';

const API_KEY = 'chave-secreta-club-maravilha-12345';

function createFakeGateway(): IWhatsAppGateway {
  return {
    checkInstanceStatus: vi.fn().mockResolvedValue({ state: 'open' }),
    getQrCode: vi.fn().mockResolvedValue({ state: 'open', qrcode: null }),
    sendText: vi.fn().mockResolvedValue({ id: 'ID1', jid: '5575999990001@s.whatsapp.net' }),
    numberExists: vi.fn().mockResolvedValue(true),
    logout: vi.fn().mockResolvedValue(undefined),
    restart: vi.fn().mockResolvedValue(undefined),
  };
}

describe('app.ts - Correções de Code Review', () => {
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    app = createApp({
      gateway: createFakeGateway(),
      apiKey: API_KEY,
    });
  });

  // ---------------------------------------------------------------------------
  // Item 13: Autenticação via timingSafeEqual com SHA-256 e rejeição de não-string
  // ---------------------------------------------------------------------------
  describe('Item 13: Autenticação segura via x-api-key', () => {
    it('chave com tamanho diferente da esperada retorna 401 sem lançar erro de comparação de buffer', async () => {
      // Chave curta (comprimento diferente da API_KEY)
      const resCurta = await request(app)
        .get('/status')
        .set('x-api-key', 'curta');

      expect(resCurta.status).toBe(401);
      expect(resCurta.body).toEqual({
        error: 'Não autorizado: x-api-key inválida ou ausente.',
      });

      // Chave excessivamente longa (comprimento diferente)
      const resLonga = await request(app)
        .get('/status')
        .set('x-api-key', 'chave-muito-mais-longa-que-o-esperado-para-o-teste-de-tamanho-diferente');

      expect(resLonga.status).toBe(401);
    });

    it('chave correta com tamanho idêntico retorna 200', async () => {
      const res = await request(app)
        .get('/status')
        .set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state: 'open' });
    });

    it('requisição sem o header x-api-key retorna 401', async () => {
      const res = await request(app).get('/status');
      expect(res.status).toBe(401);
    });
  });
});
