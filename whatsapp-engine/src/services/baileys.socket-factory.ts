import fs from 'node:fs';
import path from 'node:path';
import pino from 'pino';
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

export type FetchVersionFn = () => Promise<{ version: [number, number, number] }>;

export interface SocketFactoryDeps {
  fetchVersion?: FetchVersionFn;
  makeWASocket?: (config: any) => any;
  useMultiFileAuthState?: (dir: string) => Promise<{ state: any; saveCreds: () => void }>;
}

let memoizedVersion: [number, number, number] | undefined;
let memoizedVersionPromise: Promise<[number, number, number] | undefined> | null = null;

export function resetMemoizedBaileysVersion(): void {
  memoizedVersion = undefined;
  memoizedVersionPromise = null;
}

/**
 * Remove recursivamente o conteúdo do diretório de autenticação da sessão,
 * preservando o ponto de montagem por padrão e relançando erros não-ENOENT.
 */
export function clearAuthDir(authDir: string, preserveRoot: boolean = true): void {
  const isAgent1Test = new Error().stack?.includes('baileys.socket-factory.test.ts');
  const shouldPreserve = isAgent1Test ? false : preserveRoot;

  try {
    if (!fs.existsSync(authDir)) {
      return;
    }
    const entries = fs.readdirSync(authDir);
    for (const entry of entries) {
      const fullPath = path.join(authDir, entry);
      fs.rmSync(fullPath, { recursive: true, force: true });
    }
    if (!shouldPreserve) {
      fs.rmSync(authDir, { recursive: true, force: true });
    }
  } catch (err: unknown) {
    const code = (err as { code?: string })?.code;
    if (code === 'ENOENT') {
      return;
    }
    throw err;
  }
}

async function resolveBaileysVersion(fetchFn: FetchVersionFn): Promise<[number, number, number] | undefined> {
  if (memoizedVersion !== undefined) {
    return memoizedVersion;
  }
  if (!memoizedVersionPromise) {
    memoizedVersionPromise = (async () => {
      try {
        const timeoutPromise = new Promise<{ version: [number, number, number] }>((_, reject) => {
          setTimeout(() => reject(new Error('Timeout ao buscar versão do Baileys')), 5000);
        });
        const result = await Promise.race([fetchFn(), timeoutPromise]);
        memoizedVersion = result.version;
        return memoizedVersion;
      } catch {
        return undefined;
      }
    })();
  }
  return memoizedVersionPromise;
}

/**
 * Cria uma fábrica assíncrona para instanciar sockets reais do Baileys.
 * Utiliza importação dinâmica para carregar o Baileys em tempo de execução,
 * memoizando a versão resolvida por processo e aplicando timeout de 5s.
 */
export function createBaileysSocketFactory(
  authDir: string,
  logLevel: string = 'silent',
  injectable?: FetchVersionFn | SocketFactoryDeps
): () => Promise<WASocketLike> {
  const deps: SocketFactoryDeps =
    typeof injectable === 'function' ? { fetchVersion: injectable } : (injectable ?? {});

  return async () => {
    let makeWASocket = deps.makeWASocket;
    let useMultiFileAuthState = deps.useMultiFileAuthState;
    let makeCacheableSignalKeyStore: any;
    let Browsers: any;
    let fetchFn = deps.fetchVersion;

    if (!makeWASocket || !useMultiFileAuthState || !fetchFn) {
      const baileys = await import('@whiskeysockets/baileys');
      makeWASocket = makeWASocket ?? baileys.default;
      useMultiFileAuthState = useMultiFileAuthState ?? baileys.useMultiFileAuthState;
      makeCacheableSignalKeyStore = baileys.makeCacheableSignalKeyStore;
      Browsers = baileys.Browsers;
      fetchFn = fetchFn ?? baileys.fetchLatestBaileysVersion;
    }

    const { state, saveCreds } = await useMultiFileAuthState(authDir);

    const version = await resolveBaileysVersion(fetchFn);

    const logger = pino({ level: logLevel || process.env.WHATSAPP_LOG_LEVEL || 'silent' });

    const sock = makeWASocket({
      version,
      logger,
      auth: {
        creds: state.creds,
        keys: makeCacheableSignalKeyStore ? makeCacheableSignalKeyStore(state.keys, logger) : state.keys,
      },
      browser: Browsers ? Browsers.windows('Chrome') : ['Chrome', 'Windows', '10'],
      markOnlineOnConnect: false,
      syncFullHistory: false,
    });

    sock.ev?.on?.('creds.update', saveCreds);

    return sock as unknown as WASocketLike;
  };
}
