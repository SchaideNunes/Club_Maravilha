import 'dotenv/config';
import { createApp } from './app.js';
import { loadConfig } from './config.js';
import { BaileysService } from './services/baileys.service.js';
import {
  clearAuthDir,
  createBaileysSocketFactory,
  hasRegisteredSession,
} from './services/baileys.socket-factory.js';

import { createShutdownHandler } from './shutdown.js';

function bootstrap(): void {
  process.on('unhandledRejection', (err) => {
    console.error('[whatsapp-engine] unhandledRejection:', err);
  });

  const config = loadConfig(process.env);

  const socketFactory = createBaileysSocketFactory(config.authDir, config.logLevel);

  const service = new BaileysService({
    createSocket: socketFactory,
    clearAuth: () => clearAuthDir(config.authDir),
    hasSession: () => hasRegisteredSession(config.authDir),
    log: (msg) => console.log(`[whatsapp-engine] ${msg}`),
  });

  if (hasRegisteredSession(config.authDir)) {
    console.log('[whatsapp-engine] Sessão registrada encontrada. Iniciando conexão Baileys...');
    void service.start();
  } else {
    console.log('[whatsapp-engine] Nenhuma sessão registrada encontrada. Aguardando pareamento via QR Code.');
  }

  const app = createApp({
    gateway: service,
    apiKey: config.apiKey,
  });

  const server = app.listen(config.port, () => {
    console.log(`[whatsapp-engine] Servidor rodando na porta ${config.port}`);
  });

  const shutdown = createShutdownHandler(service, server, (code) => process.exit(code ?? 0));

  process.on('SIGINT', () => void shutdown());
  process.on('SIGTERM', () => void shutdown());
}

bootstrap();
