import fs from 'node:fs';
import path from 'node:path';
import { WASocketLike } from './baileys.service.js';

/**
 * Verifica se já existe uma sessão pareada no diretório especificado.
 * É considerada válida apenas se authDir/creds.json existir e contiver o campo "me".
 */
export function hasRegisteredSession(authDir: string): boolean {
  try {
    const credsPath = path.join(authDir, 'creds.json');
    if (!fs.existsSync(credsPath)) {
      return false;
    }
    const content = fs.readFileSync(credsPath, 'utf8');
    const creds = JSON.parse(content);
    return Boolean(creds?.me);
  } catch {
    return false;
  }
}

/**
 * Remove recursivamente o diretório de autenticação da sessão.
 */
export function clearAuthDir(authDir: string): void {
  try {
    fs.rmSync(authDir, { recursive: true, force: true });
  } catch {
    // Tolera erros se o diretório não existir ou falhas silenciosas
  }
}

/**
 * Cria uma fábrica assíncrona para instanciar sockets reais do Baileys.
 * Utiliza importação dinâmica para carregar o Baileys em tempo de execução.
 */
export function createBaileysSocketFactory(authDir: string, logLevel: string = 'silent'): () => Promise<WASocketLike> {
  return async () => {
    const baileys = await import('@whiskeysockets/baileys');
    const makeWASocket = baileys.default;
    const pinoModule = await import('pino');
    const pino = pinoModule.default;

    const { state, saveCreds } = await baileys.useMultiFileAuthState(authDir);

    let version: [number, number, number] | undefined;
    try {
      const versionResult = await baileys.fetchLatestBaileysVersion();
      version = versionResult.version;
    } catch {
      // Usa versão padrão embutida no pacote se não houver conexão para checar versão
    }

    const logger = pino({ level: logLevel || process.env.WHATSAPP_LOG_LEVEL || 'silent' });

    const sock = makeWASocket({
      version,
      logger,
      auth: {
        creds: state.creds,
        keys: baileys.makeCacheableSignalKeyStore(state.keys, logger),
      },
      browser: baileys.Browsers.windows('Chrome'),
      markOnlineOnConnect: false,
      syncFullHistory: false,
    });

    sock.ev.on('creds.update', saveCreds);

    return sock as unknown as WASocketLike;
  };
}
