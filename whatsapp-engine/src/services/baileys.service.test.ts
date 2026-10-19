/**
 * Contrato (src/services/baileys.service.ts + src/services/whatsapp-gateway.interface.ts),
 * portado de Flow-Zap/backend/src/services/baileys.service.ts:
 *
 * new BaileysService({ createSocket, clearAuth, hasSession, qrToDataUrl?, random?, reconnectBaseMs?,
 *   reconnectMaxMs?, qrWaitMs?, typingMs?, sleep?, log? }) implements IWhatsAppGateway
 * - start(): idempotente (um único socket); estado 'connecting' até o WhatsApp confirmar 'open'.
 * - stop(): encerra o socket (end), cancela reconexão agendada; estado 'close'.
 * - logout(): sock.logout() (falha tolerada) + clearAuth(); estado 'close'; não reconecta.
 * - restart(): encerra o socket atual (sem apagar sessão) e abre um novo.
 * - checkInstanceStatus() -> { state }.
 * - getQrCode() -> { state: 'open', qrcode: null } se conectado; senão inicia e aguarda o QR até qrWaitMs:
 *   { state, qrcode: dataUrl | null }.
 * - Close: 401 apaga sessão e não reconecta; 440 não reconecta; 515 reabre na hora; demais códigos
 *   com sessão registrada -> backoff exponencial base*2^n (limitado a max) * jitter (0.8 + random*0.4);
 *   sem sessão registrada -> não reconecta. Eventos de sockets antigos são ignorados.
 * - sendText(numero, texto) -> { id, jid }: normaliza (NumeroInvalidoError), resolve JID via onWhatsApp
 *   (cache por número), NumeroSemWhatsAppError se não existir, simula digitação
 *   (presenceSubscribe + sendPresenceUpdate('composing', jid) + sleep(typingMs)) ANTES do sendMessage;
 *   desconectado -> WhatsAppDesconectadoError (mensagem contém "desconectado").
 */
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { BaileysService, BaileysServiceConfig, ConnectionUpdate, WASocketLike } from './baileys.service.js';
import { NumeroSemWhatsAppError, WhatsAppDesconectadoError } from './whatsapp-gateway.interface.js';
import { NumeroInvalidoError } from '../utils/phone.js';

type Listener = (update: ConnectionUpdate) => void;

interface FakeSocket extends WASocketLike {
  emit: (update: ConnectionUpdate) => void;
  sendMessage: ReturnType<typeof vi.fn>;
  sendPresenceUpdate: ReturnType<typeof vi.fn>;
  presenceSubscribe: ReturnType<typeof vi.fn>;
  onWhatsApp: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  end: ReturnType<typeof vi.fn>;
}

function createFakeSocket(): FakeSocket {
  let listener: Listener | null = null;
  return {
    ev: {
      on: (_event: 'connection.update', cb: Listener) => {
        listener = cb;
      },
    },
    emit: (update) => listener?.(update),
    sendMessage: vi.fn().mockResolvedValue({ key: { id: 'MSG123' } }),
    sendPresenceUpdate: vi.fn().mockResolvedValue(undefined),
    presenceSubscribe: vi.fn().mockResolvedValue(undefined),
    onWhatsApp: vi.fn().mockResolvedValue([{ jid: '5575999999999@s.whatsapp.net', exists: true }]),
    logout: vi.fn().mockResolvedValue(undefined),
    end: vi.fn(),
  };
}

const closeWith = (statusCode: number): ConnectionUpdate => ({
  connection: 'close',
  lastDisconnect: { error: { output: { statusCode } } },
});

describe('BaileysService', () => {
  let sockets: FakeSocket[];
  let createSocket: ReturnType<typeof vi.fn>;
  let clearAuth: ReturnType<typeof vi.fn>;
  let hasSession: ReturnType<typeof vi.fn>;
  let sleep: ReturnType<typeof vi.fn>;
  let service: BaileysService;

  const build = (overrides: Partial<BaileysServiceConfig> = {}) =>
    new BaileysService({
      createSocket: createSocket as unknown as BaileysServiceConfig['createSocket'],
      clearAuth: clearAuth as unknown as BaileysServiceConfig['clearAuth'],
      hasSession: hasSession as unknown as BaileysServiceConfig['hasSession'],
      qrToDataUrl: async (qr: string) => `data:image/png;base64,QR(${qr})`,
      random: () => 0.5, // jitter neutro (fator 1.0)
      reconnectBaseMs: 2000,
      reconnectMaxMs: 60000,
      qrWaitMs: 1000,
      typingMs: 1200,
      sleep: sleep as unknown as BaileysServiceConfig['sleep'],
      log: () => {},
      ...overrides,
    });

  beforeEach(() => {
    vi.useFakeTimers();
    sockets = [];
    createSocket = vi.fn().mockImplementation(async () => {
      const s = createFakeSocket();
      sockets.push(s);
      return s;
    });
    clearAuth = vi.fn();
    hasSession = vi.fn().mockReturnValue(true);
    sleep = vi.fn().mockResolvedValue(undefined);
    service = build();
  });

  afterEach(() => {
    service.stop();
    vi.useRealTimers();
  });

  describe('estado da conexão', () => {
    it('informa "close" enquanto nunca foi iniciado', async () => {
      expect(await service.checkInstanceStatus()).toEqual({ state: 'close' });
      expect(createSocket).not.toHaveBeenCalled();
    });

    it('fica "connecting" ao iniciar e "open" quando o WhatsApp confirma', async () => {
      await service.start();
      expect(await service.checkInstanceStatus()).toEqual({ state: 'connecting' });

      sockets[0].emit({ connection: 'open' });
      expect(await service.checkInstanceStatus()).toEqual({ state: 'open' });
    });

    it('start() é idempotente, inclusive com chamadas concorrentes', async () => {
      await Promise.all([service.start(), service.start()]);
      await service.start();
      expect(createSocket).toHaveBeenCalledTimes(1);
    });

    it('ignora eventos de sockets antigos', async () => {
      await service.start();
      sockets[0].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(2000);
      expect(sockets).toHaveLength(2);

      sockets[0].emit({ connection: 'open' }); // socket velho
      expect((await service.checkInstanceStatus()).state).toBe('connecting');
    });

    it('falha ao criar o socket deixa o estado "close" e agenda nova tentativa', async () => {
      createSocket.mockRejectedValueOnce(new Error('sem rede'));
      await service.start();
      expect((await service.checkInstanceStatus()).state).toBe('close');

      await vi.advanceTimersByTimeAsync(2001);
      expect(createSocket).toHaveBeenCalledTimes(2);
    });
  });

  describe('QR Code', () => {
    it('QR recebido -> estado connecting e getQrCode devolve data URL', async () => {
      await service.start();
      sockets[0].emit({ qr: 'RAW-QR-1' });

      expect((await service.checkInstanceStatus()).state).toBe('connecting');
      const result = await service.getQrCode();

      expect(result.state).toBe('connecting');
      expect(result.qrcode).toBe('data:image/png;base64,QR(RAW-QR-1)');
    });

    it('inicia a conexão sozinho e aguarda o QR chegar', async () => {
      const pending = service.getQrCode();
      await vi.advanceTimersByTimeAsync(0);
      expect(createSocket).toHaveBeenCalledTimes(1);

      sockets[0].emit({ qr: 'QR-TARDIO' });
      const result = await pending;

      expect(result.qrcode).toBe('data:image/png;base64,QR(QR-TARDIO)');
    });

    it('devolve qrcode nulo quando o QR não chega dentro do prazo', async () => {
      const pending = service.getQrCode();
      await vi.advanceTimersByTimeAsync(1500);
      const result = await pending;

      expect(result.qrcode).toBeNull();
      expect(result.state).toBe('connecting');
    });

    it('não cria nova conexão nem QR quando já está conectado', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });

      const result = await service.getQrCode();

      expect(result.state).toBe('open');
      expect(result.qrcode ?? null).toBeNull();
      expect(createSocket).toHaveBeenCalledTimes(1);
    });

    it('descarta o QR depois de conectar', async () => {
      await service.start();
      sockets[0].emit({ qr: 'QR' });
      sockets[0].emit({ connection: 'open' });
      sockets[0].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(2000);

      const pending = service.getQrCode();
      await vi.advanceTimersByTimeAsync(1500);
      expect((await pending).qrcode).toBeNull();
    });
  });

  describe('reconexão', () => {
    it('open zera as tentativas e reconecta com espera crescente após queda', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });

      sockets[0].emit(closeWith(428));
      expect((await service.checkInstanceStatus()).state).toBe('close');
      await vi.advanceTimersByTimeAsync(1999);
      expect(sockets).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(2);
      expect(sockets).toHaveLength(2); // 1ª tentativa após 2s

      sockets[1].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(3999);
      expect(sockets).toHaveLength(2);
      await vi.advanceTimersByTimeAsync(2);
      expect(sockets).toHaveLength(3); // 2ª tentativa após 4s

      sockets[2].emit({ connection: 'open' });
      sockets[2].emit(closeWith(500));
      await vi.advanceTimersByTimeAsync(2001);
      expect(sockets).toHaveLength(4); // voltou a esperar 2s depois de conectar
    });

    it('aplica jitter de 0.8x a 1.2x sobre a espera', async () => {
      service.stop();
      service = build({ random: () => 0 }); // fator 0.8 -> 1600ms
      await service.start();
      sockets[0].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(1599);
      expect(sockets).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(2);
      expect(sockets).toHaveLength(2);

      service.stop();
      sockets = [];
      service = build({ random: () => 1 }); // fator 1.2 -> 2400ms
      await service.start();
      sockets[0].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(2399);
      expect(sockets).toHaveLength(1);
      await vi.advanceTimersByTimeAsync(2);
      expect(sockets).toHaveLength(2);
    });

    it('limita a espera ao máximo configurado', async () => {
      service.stop();
      service = build({ reconnectBaseMs: 1000, reconnectMaxMs: 3000 });
      await service.start();

      for (let i = 0; i < 4; i++) {
        sockets[i].emit(closeWith(428));
        await vi.advanceTimersByTimeAsync(3001);
      }
      expect(sockets).toHaveLength(5); // 1 + 4 reconexões, nenhuma espera passou de 3s
    });

    it('515 (restart required) reabre a conexão imediatamente', async () => {
      await service.start();
      sockets[0].emit(closeWith(515));
      await vi.advanceTimersByTimeAsync(0);
      expect(sockets).toHaveLength(2);
      expect(clearAuth).not.toHaveBeenCalled();
    });

    it('401 (logged out) apaga a sessão e não reconecta', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });
      sockets[0].emit(closeWith(401));
      await vi.advanceTimersByTimeAsync(120000);

      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect(sockets).toHaveLength(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
    });

    it('440 (connection replaced) não reconecta nem apaga a sessão', async () => {
      await service.start();
      sockets[0].emit(closeWith(440));
      await vi.advanceTimersByTimeAsync(120000);

      expect(clearAuth).not.toHaveBeenCalled();
      expect(sockets).toHaveLength(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
    });

    it('sem sessão registrada (QR expirou) não reconecta', async () => {
      hasSession.mockReturnValue(false);
      await service.start();
      sockets[0].emit(closeWith(408));
      await vi.advanceTimersByTimeAsync(120000);

      expect(sockets).toHaveLength(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
    });

    it('stop() encerra o socket ativo e ignora eventos tardios', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });
      service.stop();
      sockets[0].emit(closeWith(428));
      await vi.advanceTimersByTimeAsync(120000);

      expect(sockets[0].end).toHaveBeenCalled();
      expect(sockets).toHaveLength(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
    });

    it('stop() cancela uma reconexão que já estava agendada', async () => {
      await service.start();
      sockets[0].emit(closeWith(428));
      service.stop();
      await vi.advanceTimersByTimeAsync(120000);

      expect(sockets).toHaveLength(1);
    });
  });

  describe('logout e restart', () => {
    it('logout() desconecta o aparelho, apaga a sessão e não reconecta', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });

      await service.logout();

      expect(sockets[0].logout).toHaveBeenCalledTimes(1);
      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');

      sockets[0].emit(closeWith(401)); // evento que o Baileys emite após o logout
      await vi.advanceTimersByTimeAsync(120000);
      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect(sockets).toHaveLength(1);
    });

    it('logout() apaga a sessão mesmo se o WhatsApp recusar o logout', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });
      sockets[0].logout.mockRejectedValue(new Error('Connection Closed'));

      await expect(service.logout()).resolves.toBeUndefined();

      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
    });

    it('logout() sem conexão aberta apenas apaga a sessão', async () => {
      await service.logout();
      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect(createSocket).not.toHaveBeenCalled();
    });

    it('depois do logout um novo getQrCode() abre conexão nova para parear', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });
      await service.logout();

      const pending = service.getQrCode();
      await vi.advanceTimersByTimeAsync(0);
      expect(sockets).toHaveLength(2);
      sockets[1].emit({ qr: 'NOVO-QR' });

      expect((await pending).qrcode).toBe('data:image/png;base64,QR(NOVO-QR)');
    });

    it('restart() encerra o socket atual e abre outro, preservando a sessão', async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });

      await service.restart();

      expect(sockets[0].end).toHaveBeenCalled();
      expect(sockets).toHaveLength(2);
      expect(clearAuth).not.toHaveBeenCalled();
      expect((await service.checkInstanceStatus()).state).toBe('connecting');

      sockets[0].emit(closeWith(428)); // socket antigo não interfere
      await vi.advanceTimersByTimeAsync(120000);
      expect(sockets).toHaveLength(2);

      sockets[1].emit({ connection: 'open' });
      expect((await service.checkInstanceStatus()).state).toBe('open');
    });

    it('restart() funciona mesmo sem conexão prévia', async () => {
      await service.restart();
      expect(sockets).toHaveLength(1);
      expect((await service.checkInstanceStatus()).state).toBe('connecting');
    });
  });

  describe('envio', () => {
    beforeEach(async () => {
      await service.start();
      sockets[0].emit({ connection: 'open' });
    });

    it('resolve o JID pelo WhatsApp e envia o texto', async () => {
      const result = await service.sendText('+55 (75) 99999-9999', 'Olá!');

      expect(sockets[0].onWhatsApp).toHaveBeenCalledWith('5575999999999');
      expect(sockets[0].sendMessage).toHaveBeenCalledWith('5575999999999@s.whatsapp.net', { text: 'Olá!' });
      expect(result).toEqual({ id: 'MSG123', jid: '5575999999999@s.whatsapp.net' });
    });

    it('usa o JID devolvido pelo WhatsApp (números antigos sem o 9º dígito)', async () => {
      sockets[0].onWhatsApp.mockResolvedValue([{ jid: '557588887777@s.whatsapp.net', exists: true }]);

      const result = await service.sendText('5575988887777', 'Oi');

      expect(sockets[0].sendMessage).toHaveBeenCalledWith('557588887777@s.whatsapp.net', { text: 'Oi' });
      expect(result.jid).toBe('557588887777@s.whatsapp.net');
    });

    it('guarda o JID em cache: onWhatsApp é consultado uma vez por número', async () => {
      await service.sendText('5575999999999', 'Oi 1');
      await service.sendText('+55 (75) 99999-9999', 'Oi 2');
      expect(await service.numberExists('75999999999')).toBe(true);

      expect(sockets[0].onWhatsApp).toHaveBeenCalledTimes(1);
      expect(sockets[0].sendMessage).toHaveBeenCalledTimes(2);
    });

    it('número sem WhatsApp lança NumeroSemWhatsAppError e não envia', async () => {
      sockets[0].onWhatsApp.mockResolvedValue([{ jid: '5575000000000@s.whatsapp.net', exists: false }]);

      await expect(service.sendText('5575000000000', 'Oi')).rejects.toBeInstanceOf(NumeroSemWhatsAppError);
      expect(sockets[0].sendMessage).not.toHaveBeenCalled();
    });

    it('resposta vazia do WhatsApp é tratada como número inexistente', async () => {
      sockets[0].onWhatsApp.mockResolvedValue([]);
      await expect(service.sendText('5575000000000', 'Oi')).rejects.toBeInstanceOf(NumeroSemWhatsAppError);
      expect(await service.numberExists('5575000000000')).toBe(false);
    });

    it('número inválido lança NumeroInvalidoError sem consultar o WhatsApp', async () => {
      await expect(service.sendText('123', 'Oi')).rejects.toBeInstanceOf(NumeroInvalidoError);
      expect(sockets[0].onWhatsApp).not.toHaveBeenCalled();
    });

    it('simula digitação (presenceSubscribe + composing + pausa) antes do sendMessage', async () => {
      await service.sendText('5575999999999', 'Oi');

      const jid = '5575999999999@s.whatsapp.net';
      expect(sockets[0].presenceSubscribe).toHaveBeenCalledWith(jid);
      expect(sockets[0].sendPresenceUpdate).toHaveBeenCalledWith('composing', jid);
      expect(sleep).toHaveBeenCalledWith(1200);

      const composingIndex = sockets[0].sendPresenceUpdate.mock.calls.findIndex(
        (call: unknown[]) => call[0] === 'composing',
      );
      const subscribeOrder = sockets[0].presenceSubscribe.mock.invocationCallOrder[0];
      const composingOrder = sockets[0].sendPresenceUpdate.mock.invocationCallOrder[composingIndex];
      const sleepOrder = sleep.mock.invocationCallOrder[0];
      const sendOrder = sockets[0].sendMessage.mock.invocationCallOrder[0];
      expect(subscribeOrder).toBeLessThan(composingOrder);
      expect(composingOrder).toBeLessThan(sleepOrder);
      expect(sleepOrder).toBeLessThan(sendOrder);
    });

    it('falha na simulação de digitação não impede o envio', async () => {
      sockets[0].sendPresenceUpdate.mockRejectedValue(new Error('boom'));

      const result = await service.sendText('5575999999999', 'Oi');

      expect(result.id).toBe('MSG123');
      expect(sockets[0].sendMessage).toHaveBeenCalledTimes(1);
    });

    it('recusa enviar quando está desconectado com WhatsAppDesconectadoError', async () => {
      sockets[0].emit(closeWith(428));

      await expect(service.sendText('5575999999999', 'Oi')).rejects.toBeInstanceOf(WhatsAppDesconectadoError);
      await expect(service.sendText('5575999999999', 'Oi')).rejects.toThrow(/desconectado/i);
      expect(sockets[0].sendMessage).not.toHaveBeenCalled();
    });

    it('recusa enviar enquanto ainda está aguardando o QR (connecting)', async () => {
      service.stop();
      sockets = [];
      service = build();
      await service.start();
      sockets[0].emit({ qr: 'QR' });

      await expect(service.sendText('5575999999999', 'Oi')).rejects.toBeInstanceOf(WhatsAppDesconectadoError);
    });

    it('devolve id nulo quando o WhatsApp não informa a chave da mensagem', async () => {
      sockets[0].sendMessage.mockResolvedValue(undefined);
      expect(await service.sendText('5575999999999', 'Oi')).toEqual({
        id: null,
        jid: '5575999999999@s.whatsapp.net',
      });
    });
  });
});
