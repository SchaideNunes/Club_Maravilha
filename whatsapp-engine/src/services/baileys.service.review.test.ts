import { describe, expect, it, vi, beforeEach } from 'vitest';
import {
  BaileysService,
  ConnectionUpdate,
  WASocketLike,
} from './baileys.service.js';
import {
  NumeroSemWhatsAppError,
  WhatsAppDesconectadoError,
} from './whatsapp-gateway.interface.js';

interface FakeSocket {
  ev: {
    on: ReturnType<typeof vi.fn>;
  };
  sendMessage: ReturnType<typeof vi.fn>;
  sendPresenceUpdate: ReturnType<typeof vi.fn>;
  presenceSubscribe: ReturnType<typeof vi.fn>;
  onWhatsApp: ReturnType<typeof vi.fn>;
  logout: ReturnType<typeof vi.fn>;
  end: ReturnType<typeof vi.fn>;
  emit: (update: ConnectionUpdate) => void;
}

function createFakeSocket(): FakeSocket {
  let updateListener: ((u: ConnectionUpdate) => void) | undefined;
  return {
    ev: {
      on: vi.fn((event: string, listener: (u: ConnectionUpdate) => void) => {
        if (event === 'connection.update') {
          updateListener = listener;
        }
      }),
    },
    sendMessage: vi.fn().mockResolvedValue({ key: { id: 'MSG-REV-1' } }),
    sendPresenceUpdate: vi.fn().mockResolvedValue(undefined),
    presenceSubscribe: vi.fn().mockResolvedValue(undefined),
    onWhatsApp: vi.fn().mockResolvedValue([{ jid: '5575999990001@s.whatsapp.net', exists: true }]),
    logout: vi.fn().mockResolvedValue(undefined),
    end: vi.fn(),
    emit: (update: ConnectionUpdate) => updateListener?.(update),
  };
}

describe('BaileysService - Correções de Code Review', () => {
  beforeEach(() => {
    vi.useFakeTimers();
  });

  // ---------------------------------------------------------------------------
  // Item 1: Corrida connect × stop/logout/restart
  // ---------------------------------------------------------------------------
  describe('Item 1: Corrida connect x stop / logout', () => {
    it('start() seguido de stop() antes do socket resolver chama end() no socket novo, mantém close e recusa envio', async () => {
      let resolveSocket!: (s: WASocketLike) => void;
      const socketPromise = new Promise<WASocketLike>((res) => {
        resolveSocket = res;
      });

      const fakeSocket = createFakeSocket();
      const createSocket = vi.fn().mockReturnValue(socketPromise);
      const clearAuth = vi.fn();
      const hasSession = vi.fn().mockReturnValue(true);

      const service = new BaileysService({
        createSocket,
        clearAuth,
        hasSession,
        sleep: async () => {},
        log: () => {},
      });

      // Dispara start() mas createSocket ainda está pendente
      const startPromise = service.start();
      expect(createSocket).toHaveBeenCalledTimes(1);

      // Usuário decide parar o serviço
      service.stop();
      expect((await service.checkInstanceStatus()).state).toBe('close');

      // Agora o socket que estava pendente resolve
      resolveSocket(fakeSocket as unknown as WASocketLike);
      await startPromise;

      // Socket criado tardiamente deve ter seu end() invocado imediatamente
      expect(fakeSocket.end).toHaveBeenCalledTimes(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');

      // Tentativa de envio deve falhar com WhatsAppDesconectadoError
      await expect(service.sendText('75999990001', 'teste')).rejects.toThrow(
        WhatsAppDesconectadoError
      );
    });

    it('start() seguido de logout() aguarda inicialização, chama end() e mantém close', async () => {
      let resolveSocket!: (s: WASocketLike) => void;
      const socketPromise = new Promise<WASocketLike>((res) => {
        resolveSocket = res;
      });

      const fakeSocket = createFakeSocket();
      const createSocket = vi.fn().mockReturnValue(socketPromise);
      let sessionActive = true;
      const clearAuth = vi.fn(() => {
        sessionActive = false;
      });
      const hasSession = vi.fn(() => sessionActive);

      const service = new BaileysService({
        createSocket,
        clearAuth,
        hasSession,
        sleep: async () => {},
        log: () => {},
      });

      // Dispara conexão inicial pendente
      const startPromise = service.start();

      // Logout disparado enquanto connect() ainda espera createSocket
      const logoutPromise = service.logout();

      // Resolve o socket pendente
      resolveSocket(fakeSocket as unknown as WASocketLike);
      await startPromise;
      await logoutPromise;

      expect(fakeSocket.end).toHaveBeenCalledTimes(1);
      expect(clearAuth).toHaveBeenCalledTimes(1);
      expect((await service.checkInstanceStatus()).state).toBe('close');
      await expect(service.sendText('75999990001', 'ola')).rejects.toThrow(
        WhatsAppDesconectadoError
      );
    });
  });

  // ---------------------------------------------------------------------------
  // Item 2: GET /qr contorna o backoff
  // ---------------------------------------------------------------------------
  describe('Item 2: GET /qr não contorna o backoff de reconexão', () => {
    it('após close 428 com reconnectBaseMs=60000, getQrCode() não chama createSocket de novo e timer segue pendente', async () => {
      const socket1 = createFakeSocket();
      const socket2 = createFakeSocket();
      const createSocket = vi
        .fn()
        .mockResolvedValueOnce(socket1)
        .mockResolvedValueOnce(socket2);

      const service = new BaileysService({
        createSocket,
        clearAuth: vi.fn(),
        hasSession: () => true,
        reconnectBaseMs: 60000,
        reconnectMaxMs: 120000,
        random: () => 0.5,
        sleep: async () => {},
        log: () => {},
      });

      await service.start();
      expect(createSocket).toHaveBeenCalledTimes(1);

      // Simula desconexão com código 428 (Connection Closed)
      socket1.emit({
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 428 } } },
      });

      expect((await service.checkInstanceStatus()).state).toBe('close');

      // Enquanto o timer de reconexão estiver agendado, getQrCode não pode disparar novo socket
      const qrRes = await service.getQrCode();
      expect(qrRes.qrcode).toBeNull();
      expect(createSocket).toHaveBeenCalledTimes(1); // Não chamou socket2!

      // Após o tempo de reconexão expirar, o timer dispara a reconexão
      await vi.advanceTimersByTimeAsync(65000);
      expect(createSocket).toHaveBeenCalledTimes(2);
    });
  });

  // ---------------------------------------------------------------------------
  // Item 3: 403 e 411 reconectam para sempre
  // ---------------------------------------------------------------------------
  describe('Item 3: Erros terminais 403 e 411 não reconectam', () => {
    it.each([403, 411])(
      'código %i é terminal: sem segundo createSocket após advanceTimersByTime',
      async (code) => {
        const socket = createFakeSocket();
        const createSocket = vi.fn().mockResolvedValue(socket);
        const clearAuth = vi.fn();

        const service = new BaileysService({
          createSocket,
          clearAuth,
          hasSession: () => true,
          reconnectBaseMs: 1000,
          reconnectMaxMs: 5000,
          random: () => 0.5,
          sleep: async () => {},
          log: () => {},
        });

        await service.start();
        expect(createSocket).toHaveBeenCalledTimes(1);

        // Dispara fechamento com código terminal
        socket.emit({
          connection: 'close',
          lastDisconnect: { error: { output: { statusCode: code } } },
        });

        expect((await service.checkInstanceStatus()).state).toBe('close');
        expect(clearAuth).not.toHaveBeenCalled(); // Não apaga sessão em 403/411

        // Avança tempo superior a 2x o reconnectMaxMs
        await vi.advanceTimersByTimeAsync(15000);

        // Continua com exatamente 1 chamada a createSocket (sem loop infinito de reconexão)
        expect(createSocket).toHaveBeenCalledTimes(1);
      }
    );

    it('código 500 continua reconectando normalmente', async () => {
      const socket1 = createFakeSocket();
      const socket2 = createFakeSocket();
      const createSocket = vi
        .fn()
        .mockResolvedValueOnce(socket1)
        .mockResolvedValueOnce(socket2);

      const service = new BaileysService({
        createSocket,
        clearAuth: vi.fn(),
        hasSession: () => true,
        reconnectBaseMs: 1000,
        reconnectMaxMs: 5000,
        random: () => 0.5,
        sleep: async () => {},
        log: () => {},
      });

      await service.start();
      socket1.emit({
        connection: 'close',
        lastDisconnect: { error: { output: { statusCode: 500 } } },
      });

      await vi.advanceTimersByTimeAsync(2000);
      expect(createSocket).toHaveBeenCalledTimes(2);
    });
  });

  // ---------------------------------------------------------------------------
  // Item 4: Cache de JID
  // ---------------------------------------------------------------------------
  describe('Item 4: Cache de JID (undefined transitório e cache negativo TTL 30m)', () => {
    it('onWhatsApp retornando undefined não cacheia e lança erro transitório; segunda chamada envia', async () => {
      const socket = createFakeSocket();
      socket.onWhatsApp
        .mockResolvedValueOnce(undefined) // 1ª chamada falha transitória
        .mockResolvedValueOnce([{ jid: '5575999990001@s.whatsapp.net', exists: true }]); // 2ª chamada sucesso

      const service = new BaileysService({
        createSocket: vi.fn().mockResolvedValue(socket),
        clearAuth: vi.fn(),
        hasSession: () => true,
        sleep: async () => {},
        log: () => {},
      });

      await service.start();
      socket.emit({ connection: 'open' });

      // 1ª chamada: undefined lança erro transitório
      await expect(service.sendText('75999990001', 'msg1')).rejects.toThrow(
        /Falha transitória/
      );
      expect(socket.onWhatsApp).toHaveBeenCalledTimes(1);
      expect(socket.sendMessage).not.toHaveBeenCalled();

      // 2ª chamada: não pegou cache de erro, consulta de novo e envia com sucesso
      const res = await service.sendText('75999990001', 'msg2');
      expect(res.id).toBe('MSG-REV-1');
      expect(socket.onWhatsApp).toHaveBeenCalledTimes(2);
      expect(socket.sendMessage).toHaveBeenCalledTimes(1);
    });

    it('onWhatsApp retornando [] aplica cache negativo por 30m e consulta de novo após TTL', async () => {
      const socket = createFakeSocket();
      socket.onWhatsApp
        .mockResolvedValueOnce([]) // 1ª consulta: número inexistente
        .mockResolvedValueOnce([{ jid: '5575999990002@s.whatsapp.net', exists: true }]); // após TTL: número passou a existir

      const service = new BaileysService({
        createSocket: vi.fn().mockResolvedValue(socket),
        clearAuth: vi.fn(),
        hasSession: () => true,
        sleep: async () => {},
        log: () => {},
      });

      await service.start();
      socket.emit({ connection: 'open' });

      // 1ª chamada: lança NumeroSemWhatsAppError
      await expect(service.sendText('75999990002', 'msg1')).rejects.toThrow(
        NumeroSemWhatsAppError
      );
      expect(socket.onWhatsApp).toHaveBeenCalledTimes(1);

      // Chamada imediata (dentro do TTL de 30 min): usa cache negativo sem chamar onWhatsApp
      await expect(service.sendText('75999990002', 'msg2')).rejects.toThrow(
        NumeroSemWhatsAppError
      );
      expect(socket.onWhatsApp).toHaveBeenCalledTimes(1);

      // Avança 31 minutos no tempo (expirando o TTL negativo de 30m)
      vi.advanceTimersByTime(31 * 60 * 1000);

      // Nova consulta após TTL negativo: agora consulta onWhatsApp novamente
      const res = await service.sendText('75999990002', 'msg3');
      expect(res.id).toBe('MSG-REV-1');
      expect(socket.onWhatsApp).toHaveBeenCalledTimes(2);
    });
  });

  // ---------------------------------------------------------------------------
  // Item 12: Rajadas que contornam a fila (Mutex e MIN_SEND_INTERVAL_MS)
  // ---------------------------------------------------------------------------
  describe('Item 12: Mutex em sendText com intervalo mínimo e sem sobreposição', () => {
    it('dois sendText concorrentes executam em fila e o segundo só após sleep(minInterval), nunca sobrepostos', async () => {
      const socket = createFakeSocket();
      let activeSends = 0;
      let maxConcurrentSends = 0;
      const sleepDurations: number[] = [];

      socket.sendMessage.mockImplementation(async () => {
        activeSends += 1;
        maxConcurrentSends = Math.max(maxConcurrentSends, activeSends);
        // Simula pequena latência assíncrona
        await new Promise((r) => setTimeout(r, 50));
        activeSends -= 1;
        return { key: { id: 'MSG-MUTEX' } };
      });

      const sleepMock = vi.fn().mockImplementation(async (ms: number) => {
        sleepDurations.push(ms);
      });

      const service = new BaileysService({
        createSocket: vi.fn().mockResolvedValue(socket),
        clearAuth: vi.fn(),
        hasSession: () => true,
        minSendIntervalMs: 4000,
        random: () => 0.5, // 0.8 + 0.5 * 0.4 = 1.0 -> 4000ms cravados
        typingMs: 0,
        sleep: sleepMock,
        log: () => {},
      });

      await service.start();
      socket.emit({ connection: 'open' });

      // Dispara 2 envios simultâneos
      const p1 = service.sendText('75999990001', 'msg1');
      const p2 = service.sendText('75999990002', 'msg2');

      await vi.advanceTimersByTimeAsync(50);
      await p1;

      await vi.advanceTimersByTimeAsync(50);
      await p2;

      // Nunca deve ter ocorrido concorrência real entre os sends
      expect(maxConcurrentSends).toBe(1);
      expect(socket.sendMessage).toHaveBeenCalledTimes(2);

      // O segundo sendText teve que aguardar o intervalo mínimo de 4000ms
      expect(sleepDurations).toContain(4000);
    });
  });

  // ---------------------------------------------------------------------------
  // Opcional: Boom 428 mapeado para WhatsAppDesconectadoError
  // ---------------------------------------------------------------------------
  describe('Opcional: Boom 428 no sendMessage mapeia para WhatsAppDesconectadoError', () => {
    it('quando sock.sendMessage lança 428, mapeia para WhatsAppDesconectadoError', async () => {
      const socket = createFakeSocket();
      socket.sendMessage.mockRejectedValue({
        output: { statusCode: 428 },
        message: 'Connection Lost',
      });

      const service = new BaileysService({
        createSocket: vi.fn().mockResolvedValue(socket),
        clearAuth: vi.fn(),
        hasSession: () => true,
        sleep: async () => {},
        log: () => {},
      });

      await service.start();
      socket.emit({ connection: 'open' });

      await expect(service.sendText('75999990001', 'teste')).rejects.toThrow(
        WhatsAppDesconectadoError
      );
    });
  });
});
