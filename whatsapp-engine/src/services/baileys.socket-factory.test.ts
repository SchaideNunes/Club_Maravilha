/**
 * Contrato (src/services/baileys.socket-factory.ts), portado do Flow-Zap:
 * - hasRegisteredSession(authDir): true somente se authDir/creds.json existir com o campo "me" (número pareado).
 * - clearAuthDir(authDir): apaga a pasta da sessão (sem erro se ela não existir).
 * - createBaileysSocketFactory(authDir, logLevel?): () => Promise<WASocketLike> (Baileys carregado via import dinâmico,
 *   useMultiFileAuthState + makeCacheableSignalKeyStore, Browsers.windows('Chrome'), markOnlineOnConnect: false).
 */
import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it } from 'vitest';
import { clearAuthDir, createBaileysSocketFactory, hasRegisteredSession } from './baileys.socket-factory.js';

describe('sessão salva em disco', () => {
  let dir: string;

  beforeEach(() => {
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wa-auth-'));
  });

  afterEach(() => {
    fs.rmSync(dir, { recursive: true, force: true });
  });

  it('sem creds.json não há sessão registrada', () => {
    expect(hasRegisteredSession(dir)).toBe(false);
    expect(hasRegisteredSession(path.join(dir, 'inexistente'))).toBe(false);
  });

  it('creds.json sem "me" (pareamento não concluído) não conta como sessão', () => {
    fs.writeFileSync(path.join(dir, 'creds.json'), JSON.stringify({ noiseKey: {} }));
    expect(hasRegisteredSession(dir)).toBe(false);
  });

  it('creds.json corrompido não conta como sessão', () => {
    fs.writeFileSync(path.join(dir, 'creds.json'), '{ isto não é json');
    expect(hasRegisteredSession(dir)).toBe(false);
  });

  it('creds.json com "me" indica número pareado', () => {
    fs.writeFileSync(path.join(dir, 'creds.json'), JSON.stringify({ me: { id: '5575999999999:1@s.whatsapp.net' } }));
    expect(hasRegisteredSession(dir)).toBe(true);
  });

  it('clearAuthDir apaga a sessão e tolera pasta inexistente', () => {
    fs.writeFileSync(path.join(dir, 'creds.json'), JSON.stringify({ me: { id: 'x' } }));
    clearAuthDir(dir);
    expect(fs.existsSync(dir)).toBe(false);
    expect(() => clearAuthDir(dir)).not.toThrow();
  });

  it('createBaileysSocketFactory devolve uma fábrica assíncrona sem abrir conexão', () => {
    const factory = createBaileysSocketFactory(dir);
    expect(typeof factory).toBe('function');
  });
});
