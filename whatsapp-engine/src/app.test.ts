/**
 * Contrato HTTP do whatsapp-engine (src/app.ts) — consumido pelo backend Python (BaileysWhatsAppProvider).
 *
 * createApp({ gateway: IWhatsAppGateway, apiKey: string }) -> express.Application
 *   (apiKey vazia lança erro: o engine nunca sobe sem autenticação)
 *
 * Autenticação: header `x-api-key` igual a apiKey em TODAS as rotas, exceto GET /health.
 *   Sem header ou com valor errado -> 401 { error }.
 * Erros sempre em JSON: { error: string, code?: string }.
 *
 * | Método | Rota      | Sucesso                                  | Erros                                                   |
 * |--------|-----------|------------------------------------------|---------------------------------------------------------|
 * | GET    | /health   | 200 { status: "ok" } (sem auth)          | -                                                       |
 * | GET    | /status   | 200 { state }                            | 500                                                     |
 * | GET    | /qr       | 200 { state, qrcode: dataUrl | null }    | 500                                                     |
 * | POST   | /send     | 200 { id: string|null, jid }             | 400 { error, code: "PAYLOAD_INVALIDO" | "NUMERO_INVALIDO" }  |
 * |        |           |                                          | 422 { error, code: "NUMERO_SEM_WHATSAPP" }               |
 * |        |           |                                          | 503 { error, code: "WHATSAPP_DESCONECTADO" }             |
 * |        |           |                                          | 500 { error }                                            |
 * | POST   | /logout   | 200 { state } (estado após o logout)     | 500                                                     |
 * | POST   | /restart  | 200 { state } (estado após reiniciar)    | 500                                                     |
 *
 * POST /send body: { numero: string não vazio, mensagem: string não vazia (após trim), até 4096 caracteres }.
 * state ∈ 'open' | 'connecting' | 'close'.
 */
import request from 'supertest';
import { beforeEach, describe, expect, it, vi } from 'vitest';
import { createApp } from './app.js';
import {
  IWhatsAppGateway,
  NumeroSemWhatsAppError,
  WhatsAppDesconectadoError,
} from './services/whatsapp-gateway.interface.js';
import { NumeroInvalidoError } from './utils/phone.js';

const API_KEY = 'chave-de-teste';

type FakeGateway = Record<
  'checkInstanceStatus' | 'getQrCode' | 'sendText' | 'numberExists' | 'logout' | 'restart',
  ReturnType<typeof vi.fn>
>;

function createFakeGateway(): FakeGateway {
  return {
    checkInstanceStatus: vi.fn().mockResolvedValue({ state: 'open' }),
    getQrCode: vi.fn().mockResolvedValue({ state: 'connecting', qrcode: 'data:image/png;base64,QR' }),
    sendText: vi.fn().mockResolvedValue({ id: 'MSG1', jid: '5575999999999@s.whatsapp.net' }),
    numberExists: vi.fn().mockResolvedValue(true),
    logout: vi.fn().mockResolvedValue(undefined),
    restart: vi.fn().mockResolvedValue(undefined),
  };
}

describe('createApp', () => {
  let gateway: FakeGateway;
  let app: ReturnType<typeof createApp>;

  beforeEach(() => {
    gateway = createFakeGateway();
    app = createApp({ gateway: gateway as unknown as IWhatsAppGateway, apiKey: API_KEY });
  });

  it('não aceita apiKey vazia', () => {
    expect(() => createApp({ gateway: gateway as unknown as IWhatsAppGateway, apiKey: '' })).toThrow();
  });

  describe('autenticação x-api-key', () => {
    it('GET /health responde 200 sem autenticação', async () => {
      const res = await request(app).get('/health');
      expect(res.status).toBe(200);
      expect(res.body).toEqual({ status: 'ok' });
    });

    it.each([
      ['get', '/status'],
      ['get', '/qr'],
      ['post', '/send'],
      ['post', '/logout'],
      ['post', '/restart'],
    ] as const)('%s %s sem x-api-key -> 401', async (method, path) => {
      const res = await request(app)[method](path);
      expect(res.status).toBe(401);
      expect(typeof res.body.error).toBe('string');
    });

    it('x-api-key errada -> 401 e o gateway não é acionado', async () => {
      const res = await request(app)
        .post('/send')
        .set('x-api-key', 'errada')
        .send({ numero: '5575999999999', mensagem: 'Oi' });

      expect(res.status).toBe(401);
      expect(gateway.sendText).not.toHaveBeenCalled();
    });
  });

  describe('GET /status', () => {
    it.each(['open', 'connecting', 'close'])('devolve { state: "%s" }', async (state) => {
      gateway.checkInstanceStatus.mockResolvedValue({ state });
      const res = await request(app).get('/status').set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state });
    });

    it('erro inesperado -> 500 com { error }', async () => {
      gateway.checkInstanceStatus.mockRejectedValue(new Error('boom'));
      const res = await request(app).get('/status').set('x-api-key', API_KEY);

      expect(res.status).toBe(500);
      expect(typeof res.body.error).toBe('string');
    });
  });

  describe('GET /qr', () => {
    it('devolve estado e QR em data URL', async () => {
      const res = await request(app).get('/qr').set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state: 'connecting', qrcode: 'data:image/png;base64,QR' });
    });

    it('conectado -> qrcode null', async () => {
      gateway.getQrCode.mockResolvedValue({ state: 'open' });
      const res = await request(app).get('/qr').set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state: 'open', qrcode: null });
    });
  });

  describe('POST /send', () => {
    const enviar = (body: unknown) =>
      request(app).post('/send').set('x-api-key', API_KEY).send(body as object);

    it('envia e devolve 200 { id, jid }', async () => {
      const res = await enviar({ numero: '5575999999999', mensagem: 'Olá, sócio!' });

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ id: 'MSG1', jid: '5575999999999@s.whatsapp.net' });
      expect(gateway.sendText).toHaveBeenCalledWith('5575999999999', 'Olá, sócio!');
    });

    it.each([
      [{}],
      [{ numero: '5575999999999' }],
      [{ mensagem: 'Oi' }],
      [{ numero: '', mensagem: 'Oi' }],
      [{ numero: '5575999999999', mensagem: '   ' }],
      [{ numero: 5575999999999, mensagem: 'Oi' }],
      [{ numero: '5575999999999', mensagem: 123 }],
      [{ numero: '5575999999999', mensagem: 'x'.repeat(4097) }],
    ])('payload inválido %j -> 400 PAYLOAD_INVALIDO', async (body) => {
      const res = await enviar(body);

      expect(res.status).toBe(400);
      expect(res.body.code).toBe('PAYLOAD_INVALIDO');
      expect(typeof res.body.error).toBe('string');
      expect(gateway.sendText).not.toHaveBeenCalled();
    });

    it('JSON malformado -> 400 com corpo JSON', async () => {
      const res = await request(app)
        .post('/send')
        .set('x-api-key', API_KEY)
        .set('Content-Type', 'application/json')
        .send('{"numero": ');

      expect(res.status).toBe(400);
      expect(typeof res.body.error).toBe('string');
    });

    it('número inválido -> 400 NUMERO_INVALIDO', async () => {
      gateway.sendText.mockRejectedValue(new NumeroInvalidoError('123'));
      const res = await enviar({ numero: '123', mensagem: 'Oi' });

      expect(res.status).toBe(400);
      expect(res.body.code).toBe('NUMERO_INVALIDO');
    });

    it('número sem WhatsApp -> 422 NUMERO_SEM_WHATSAPP', async () => {
      gateway.sendText.mockRejectedValue(new NumeroSemWhatsAppError('5575000000000'));
      const res = await enviar({ numero: '5575000000000', mensagem: 'Oi' });

      expect(res.status).toBe(422);
      expect(res.body.code).toBe('NUMERO_SEM_WHATSAPP');
      expect(res.body.error).toMatch(/5575000000000/);
    });

    it('WhatsApp desconectado -> 503 WHATSAPP_DESCONECTADO', async () => {
      gateway.sendText.mockRejectedValue(new WhatsAppDesconectadoError());
      const res = await enviar({ numero: '5575999999999', mensagem: 'Oi' });

      expect(res.status).toBe(503);
      expect(res.body.code).toBe('WHATSAPP_DESCONECTADO');
      expect(res.body.error).toMatch(/desconectado/i);
    });

    it('erro inesperado -> 500', async () => {
      gateway.sendText.mockRejectedValue(new Error('falha interna'));
      const res = await enviar({ numero: '5575999999999', mensagem: 'Oi' });

      expect(res.status).toBe(500);
      expect(typeof res.body.error).toBe('string');
    });
  });

  describe('POST /logout e POST /restart', () => {
    it('logout encerra a sessão e devolve o estado resultante', async () => {
      gateway.checkInstanceStatus.mockResolvedValue({ state: 'close' });
      const res = await request(app).post('/logout').set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state: 'close' });
      expect(gateway.logout).toHaveBeenCalledTimes(1);
    });

    it('restart reabre a conexão e devolve o estado resultante', async () => {
      gateway.checkInstanceStatus.mockResolvedValue({ state: 'connecting' });
      const res = await request(app).post('/restart').set('x-api-key', API_KEY);

      expect(res.status).toBe(200);
      expect(res.body).toEqual({ state: 'connecting' });
      expect(gateway.restart).toHaveBeenCalledTimes(1);
    });

    it('falha no logout -> 500', async () => {
      gateway.logout.mockRejectedValue(new Error('boom'));
      const res = await request(app).post('/logout').set('x-api-key', API_KEY);

      expect(res.status).toBe(500);
    });
  });

  it('rota inexistente autenticada -> 404 em JSON', async () => {
    const res = await request(app).get('/nao-existe').set('x-api-key', API_KEY);
    expect(res.status).toBe(404);
    expect(typeof res.body.error).toBe('string');
  });
});
