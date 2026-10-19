import type { Server } from 'node:http';

export interface StoppableService {
  stop: () => void;
}

export interface ShutdownOptions {
  service: StoppableService;
  server?: Pick<Server, 'close'>;
  exit?: (code?: number) => void;
  saveCredsWaitMs?: number;
  forceExitTimeoutMs?: number;
  log?: (message: string) => void;
}

/**
 * Cria um manipulador de encerramento gracioso para o whatsapp-engine.
 * Ordem estrita:
 * 1. service.stop() para encerrar reconexões e o socket
 * 2. server.close() para fechar a porta HTTP
 * 3. aguarda saveCreds pendentes (~1s)
 * 4. exit(0)
 *
 * Inclui timeout de proteção com unref() e proteção contra chamadas concorrentes/duplicadas.
 */
export function createShutdownHandler(
  serviceOrOptions: StoppableService | ShutdownOptions,
  maybeServer?: Pick<Server, 'close'>,
  maybeExit?: (code?: number) => void,
  maybeSaveCredsWaitMs?: number
): () => Promise<void> {
  const options: ShutdownOptions =
    'stop' in serviceOrOptions && typeof serviceOrOptions.stop === 'function'
      ? {
          service: serviceOrOptions,
          server: maybeServer,
          exit: maybeExit,
          saveCredsWaitMs: maybeSaveCredsWaitMs,
        }
      : (serviceOrOptions as ShutdownOptions);

  const {
    service,
    server,
    exit = (code = 0) => process.exit(code),
    saveCredsWaitMs = 1000,
    forceExitTimeoutMs = 8000,
    log = (msg: string) => console.log(`[whatsapp-engine] ${msg}`),
  } = options;

  let shuttingDown = false;

  return async (): Promise<void> => {
    if (shuttingDown) {
      log('Encerramento já em andamento. Ignorando chamada duplicada.');
      return;
    }
    shuttingDown = true;
    log('Encerrando serviço graciosamente...');

    // Timeout de segurança para forçar encerramento caso o ciclo trave
    const forceTimer = setTimeout(() => {
      log('Tempo limite de encerramento excedido (8s). Forçando encerramento.');
      exit(0);
    }, forceExitTimeoutMs);

    if (typeof forceTimer.unref === 'function') {
      forceTimer.unref();
    }

    try {
      // 1. service.stop() PRIMEIRO
      if (typeof service?.stop === 'function') {
        service.stop();
      }

      // 2. server.close()
      if (server && typeof server.close === 'function') {
        await new Promise<void>((resolve) => {
          server.close((err?: unknown) => {
            if (err) {
              log(`Aviso ao fechar servidor HTTP: ${err instanceof Error ? err.message : String(err)}`);
            }
            resolve();
          });
        });
      }

      // 3. Aguardar saveCreds pendentes (~1s)
      if (saveCredsWaitMs > 0) {
        await new Promise((resolve) => setTimeout(resolve, saveCredsWaitMs));
      }
    } finally {
      clearTimeout(forceTimer);
      exit(0);
    }
  };
}
