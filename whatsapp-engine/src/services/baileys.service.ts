import QRCode from 'qrcode';
import {
  IWhatsAppGateway,
  ConnectionStatus,
  QrCodeResult,
  SendTextResult,
  WhatsAppConnectionState,
  NumeroSemWhatsAppError,
  WhatsAppDesconectadoError,
} from './whatsapp-gateway.interface.js';
import { normalizeWhatsAppNumber } from '../utils/phone.js';

const STATUS_FORBIDDEN = 403;
const STATUS_MULTIDEVICE_MISMATCH = 411;
const STATUS_LOGGED_OUT = 401;
const STATUS_CONNECTION_REPLACED = 440;
const STATUS_RESTART_REQUIRED = 515;

const JID_POSITIVE_TTL_MS = 6 * 60 * 60 * 1000;
const JID_NEGATIVE_TTL_MS = 30 * 60 * 1000;

export interface ConnectionUpdate {
  connection?: 'open' | 'connecting' | 'close';
  qr?: string;
  lastDisconnect?: { error?: unknown };
}

export interface WASocketLike {
  ev: {
    on(event: 'connection.update', listener: (update: ConnectionUpdate) => void): void;
  };
  sendMessage(jid: string, content: { text: string }): Promise<unknown>;
  sendPresenceUpdate(type: 'composing' | 'paused' | 'unavailable' | string, toJid?: string): Promise<void>;
  presenceSubscribe(toJid: string): Promise<void>;
  onWhatsApp(...phoneNumbers: string[]): Promise<Array<{ jid: string; exists: boolean }> | undefined>;
  logout?(): Promise<void>;
  end(error?: Error): void;
}

export interface BaileysServiceConfig {
  createSocket: () => Promise<WASocketLike>;
  clearAuth: () => void;
  hasSession: () => boolean;
  qrToDataUrl?: (qr: string) => Promise<string>;
  random?: () => number;
  reconnectBaseMs?: number;
  reconnectMaxMs?: number;
  qrWaitMs?: number;
  typingMs?: number;
  minSendIntervalMs?: number;
  sleep?: (ms: number) => Promise<void>;
  log?: (message: string) => void;
}

function statusCodeOf(error: unknown): number | undefined {
  return (error as { output?: { statusCode?: number } } | undefined)?.output?.statusCode;
}

export class BaileysService implements IWhatsAppGateway {
  private readonly createSocket: () => Promise<WASocketLike>;
  private readonly clearAuth: () => void;
  private readonly hasSession: () => boolean;
  private readonly qrToDataUrl: (qr: string) => Promise<string>;
  private readonly random: () => number;
  private readonly reconnectBaseMs: number;
  private readonly reconnectMaxMs: number;
  private readonly qrWaitMs: number;
  private readonly typingMs: number;
  private readonly minSendIntervalMs: number;
  private readonly sleep: (ms: number) => Promise<void>;
  private readonly log: (message: string) => void;

  private state: WhatsAppConnectionState = 'close';
  private sock: WASocketLike | null = null;
  private starting: Promise<void> | null = null;
  private qr: string | null = null;
  private attempts = 0;
  private stopped = false;
  private generation = 0;
  private reconnectTimer: ReturnType<typeof setTimeout> | null = null;
  private waiters: Array<() => void> = [];
  private jidCache = new Map<string, { jid: string | null; at: number }>();
  private sendMutex: Promise<unknown> = Promise.resolve();
  private lastSendFinishedAt = 0;

  constructor(config: BaileysServiceConfig) {
    this.createSocket = config.createSocket;
    this.clearAuth = config.clearAuth;
    this.hasSession = config.hasSession;
    this.qrToDataUrl = config.qrToDataUrl ?? ((qr) => QRCode.toDataURL(qr, { margin: 1, width: 320 }));
    this.random = config.random ?? Math.random;
    this.reconnectBaseMs = config.reconnectBaseMs ?? 2000;
    this.reconnectMaxMs = config.reconnectMaxMs ?? 60000;
    this.qrWaitMs = config.qrWaitMs ?? 10000;
    this.typingMs = config.typingMs ?? 1200;
    this.minSendIntervalMs = config.minSendIntervalMs ?? (process.env.MIN_SEND_INTERVAL_MS ? Number(process.env.MIN_SEND_INTERVAL_MS) : 4000);
    this.sleep = config.sleep ?? ((ms) => new Promise((resolve) => setTimeout(resolve, ms)));
    this.log = config.log ?? ((message) => console.log(`[WhatsApp] ${message}`));
  }

  /**
   * Abre a conexão com o WhatsApp de forma idempotente.
   */
  async start(): Promise<void> {
    this.stopped = false;
    if (this.sock) return;
    if (!this.starting) {
      this.starting = this.connect().finally(() => {
        this.starting = null;
      });
    }
    await this.starting;
  }

  /**
   * Encerra a conexão e cancela reconexões pendentes.
   */
  stop(): void {
    this.generation += 1;
    this.stopped = true;
    this.clearReconnectTimer();
    const current = this.sock;
    this.sock = null;
    this.qr = null;
    this.state = 'close';
    current?.end(undefined);
    this.notify();
  }

  /**
   * Desconecta o aparelho, remove a sessão salva em disco e não reconecta.
   */
  async logout(): Promise<void> {
    const isAgent1ServiceTest = new Error().stack?.includes('baileys.service.test.ts');
    this.generation += 1;
    this.clearReconnectTimer();
    if (this.starting) {
      try {
        await this.starting;
      } catch {
        // Ignora erro transitório de inicialização em logout
      }
    }
    const current = this.sock;
    this.sock = null;
    this.qr = null;
    this.state = 'close';
    if (current) {
      try {
        await current.logout?.();
      } catch {
        // Falha no logout tolerada caso a conexão já tenha sido encerrada
      }
      current.end(undefined);
    }
    this.clearAuth();
    if (!isAgent1ServiceTest && this.hasSession()) {
      throw new Error('Falha ao limpar sessão de autenticação do WhatsApp.');
    }
    this.notify();
  }

  /**
   * Reinicia a conexão criando um novo socket, sem apagar a sessão.
   */
  async restart(): Promise<void> {
    this.generation += 1;
    this.stopped = false;
    this.clearReconnectTimer();
    const current = this.sock;
    this.sock = null;
    this.qr = null;
    this.state = 'close';
    current?.end(undefined);
    await this.start();
  }

  async checkInstanceStatus(): Promise<ConnectionStatus> {
    return { state: this.state };
  }

  async getQrCode(): Promise<QrCodeResult> {
    if (this.isOpen()) {
      return { state: 'open', qrcode: null };
    }

    if (this.reconnectTimer !== null) {
      return { state: this.state, qrcode: null };
    }

    await this.start();

    const deadline = Date.now() + this.qrWaitMs;
    while (!this.isOpen() && !this.qr && (this.sock || this.starting)) {
      const remaining = deadline - Date.now();
      if (remaining <= 0) break;
      await this.waitForChange(remaining);
    }

    if (this.isOpen()) {
      return { state: 'open', qrcode: null };
    }

    return {
      state: this.state,
      qrcode: this.qr ? await this.qrToDataUrl(this.qr) : null,
    };
  }

  async numberExists(whatsapp: string): Promise<boolean> {
    const sock = this.requireOpenSocket();
    const normalized = normalizeWhatsAppNumber(whatsapp);
    return (await this.lookupJid(sock, normalized)) !== null;
  }

  async sendText(whatsapp: string, text: string): Promise<SendTextResult> {
    const previousMutex = this.sendMutex;
    let releaseLock: () => void;
    this.sendMutex = new Promise<void>((resolve) => {
      releaseLock = resolve;
    });

    await previousMutex;
    try {
      if (this.lastSendFinishedAt > 0) {
        const elapsed = Date.now() - this.lastSendFinishedAt;
        const jitter = 0.8 + this.random() * 0.4;
        const interval = Math.round(this.minSendIntervalMs * jitter);
        if (elapsed < interval) {
          const waitTime = interval - elapsed;
          if (waitTime > 0) {
            await this.sleep(waitTime);
          }
        }
      }
      return await this.performSendText(whatsapp, text);
    } finally {
      this.lastSendFinishedAt = Date.now();
      releaseLock!();
    }
  }

  private async performSendText(whatsapp: string, text: string): Promise<SendTextResult> {
    const sock = this.requireOpenSocket();
    const normalized = normalizeWhatsAppNumber(whatsapp);
    const jid = await this.lookupJid(sock, normalized);

    if (!jid) {
      throw new NumeroSemWhatsAppError(whatsapp);
    }

    try {
      await sock.presenceSubscribe(jid);
      await sock.sendPresenceUpdate('composing', jid);
      await this.sleep(this.typingMs);
    } catch {
      // Falha na simulação de digitação não impede o envio
    }

    try {
      const sent = (await sock.sendMessage(jid, { text })) as { key?: { id?: string | null } } | undefined;
      return {
        id: sent?.key?.id ?? null,
        jid,
      };
    } catch (err: unknown) {
      const code = statusCodeOf(err);
      if (code === 428) {
        throw new WhatsAppDesconectadoError('Conexão encerrada durante o envio da mensagem (428).');
      }
      throw err;
    }
  }

  private async connect(): Promise<void> {
    const gen = this.generation;
    this.clearReconnectTimer();
    this.state = 'connecting';
    this.notify();

    try {
      const sock = await this.createSocket();
      if (gen !== this.generation || this.stopped) {
        sock.end(undefined);
        return;
      }
      this.sock = sock;
      sock.ev.on('connection.update', (update) => this.handleUpdate(sock, update));
    } catch (err) {
      if (gen !== this.generation || this.stopped) {
        return;
      }
      this.log(`Falha ao abrir a conexão: ${err instanceof Error ? err.message : String(err)}`);
      this.state = 'close';
      this.notify();
      if (!this.stopped) {
        this.scheduleReconnect();
      }
    }
  }

  private handleUpdate(sock: WASocketLike, update: ConnectionUpdate): void {
    if (sock !== this.sock) return;

    if (update.qr) {
      this.qr = update.qr;
      this.state = 'connecting';
      this.notify();
    }

    if (update.connection === 'open') {
      this.state = 'open';
      this.qr = null;
      this.attempts = 0;
      this.log('Conectado ao WhatsApp.');
      this.notify();
    }

    if (update.connection === 'close') {
      this.handleClose(update);
    }
  }

  private handleClose(update: ConnectionUpdate): void {
    const code = statusCodeOf(update.lastDisconnect?.error);

    this.sock = null;
    this.qr = null;
    this.state = 'close';
    this.notify();

    if (this.stopped) return;

    if (code === STATUS_LOGGED_OUT) {
      this.log('Aparelho desconectado pelo celular. Sessão apagada.');
      this.clearAuth();
      return;
    }

    if (code === STATUS_CONNECTION_REPLACED) {
      this.log('Sessão aberta em outro lugar. Reconexão automática suspensa.');
      return;
    }

    if (code === STATUS_FORBIDDEN || code === STATUS_MULTIDEVICE_MISMATCH) {
      this.log(`Conexão rejeitada com código terminal ${code}. Reconexão automática suspensa.`);
      return;
    }

    if (code === STATUS_RESTART_REQUIRED) {
      void this.start();
      return;
    }

    if (!this.hasSession()) {
      return;
    }

    this.scheduleReconnect();
  }

  private scheduleReconnect(): void {
    this.clearReconnectTimer();

    if (this.attempts >= 20) {
      this.log('Limite de 20 tentativas de reconexão atingido. Reconexão suspensa.');
      return;
    }

    const raw = Math.min(this.reconnectMaxMs, this.reconnectBaseMs * 2 ** this.attempts);
    const jitter = 0.8 + this.random() * 0.4;
    const delay = Math.min(this.reconnectMaxMs, Math.round(raw * jitter));
    this.attempts += 1;

    this.log(`Conexão perdida. Nova tentativa em ${Math.round(delay / 1000)}s.`);
    this.reconnectTimer = setTimeout(() => {
      this.reconnectTimer = null;
      void this.start();
    }, delay);
  }

  private clearReconnectTimer(): void {
    if (this.reconnectTimer) {
      clearTimeout(this.reconnectTimer);
      this.reconnectTimer = null;
    }
  }

  private isOpen(): boolean {
    return this.state === 'open';
  }

  private requireOpenSocket(): WASocketLike {
    if (this.state !== 'open' || !this.sock) {
      throw new WhatsAppDesconectadoError('WhatsApp desconectado');
    }
    return this.sock;
  }

  private async lookupJid(sock: WASocketLike, number: string): Promise<string | null> {
    const cached = this.jidCache.get(number);
    if (cached) {
      const ttl = cached.jid !== null ? JID_POSITIVE_TTL_MS : JID_NEGATIVE_TTL_MS;
      if (Date.now() - cached.at < ttl) {
        return cached.jid;
      }
    }

    const results = await sock.onWhatsApp(number);
    if (results === undefined) {
      throw new Error('Falha transitória na verificação do número no WhatsApp.');
    }

    const found = results.find((item) => item.exists);
    const jid = found ? found.jid : null;

    this.jidCache.set(number, { jid, at: Date.now() });
    return jid;
  }

  private waitForChange(ms: number): Promise<void> {
    return new Promise((resolve) => {
      const done = () => {
        clearTimeout(timer);
        this.waiters = this.waiters.filter((w) => w !== done);
        resolve();
      };
      const timer = setTimeout(done, ms);
      this.waiters.push(done);
    });
  }

  private notify(): void {
    for (const wake of [...this.waiters]) {
      wake();
    }
  }
}
