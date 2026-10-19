import fs from 'node:fs';
import os from 'node:os';
import path from 'node:path';
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import {
  clearAuthDir,
  createBaileysSocketFactory,
  resetMemoizedBaileysVersion,
} from './baileys.socket-factory.js';

describe('baileys.socket-factory - Correções de Code Review', () => {
  let dir: string;

  beforeEach(() => {
    vi.useFakeTimers();
    resetMemoizedBaileysVersion();
    dir = fs.mkdtempSync(path.join(os.tmpdir(), 'wa-auth-review-'));
  });

  afterEach(() => {
    vi.useRealTimers();
    if (fs.existsSync(dir)) {
      fs.rmSync(dir, { recursive: true, force: true });
    }
  });

  // ---------------------------------------------------------------------------
  // Item 5: fetchLatestBaileysVersion com timeout de 5s e memoização
  // ---------------------------------------------------------------------------
  describe('Item 5: Timeout e memoização na busca de versão do Baileys', () => {
    it(
      'fetchVersion que nunca resolve: factory termina com fallback embutido via fake timers e busca ocorre uma única vez em duas criações',
      async () => {
        let fetchCalls = 0;
      // fetchVersion que nunca resolve (simula rede presa/offline)
      const fetchVersionHang = vi.fn().mockImplementation(() => {
        fetchCalls += 1;
        return new Promise(() => {});
      });

      const makeFakeSocket = vi.fn().mockReturnValue({ ev: { on: vi.fn() } });
      const fakeUseAuthState = vi.fn().mockResolvedValue({
        state: { creds: {}, keys: {} },
        saveCreds: vi.fn(),
      });

      const factory = createBaileysSocketFactory(dir, 'silent', {
        fetchVersion: fetchVersionHang,
        makeWASocket: makeFakeSocket,
        useMultiFileAuthState: fakeUseAuthState,
      });

      // 1ª criação de socket: deve acionar o timeout de 5s
      const sockPromise1 = factory();

      // Avança os timers 5 segundos (timeout da busca de versão)
      await vi.advanceTimersByTimeAsync(5000);
      const sock1 = await sockPromise1;
      expect(sock1).toBeDefined();
      expect(fetchCalls).toBe(1);

      // makeWASocket foi chamado com version: undefined (fallback embutido)
      expect(makeFakeSocket).toHaveBeenLastCalledWith(
        expect.objectContaining({ version: undefined })
      );

      // 2ª criação de socket: deve reutilizar a memoização e NÃO chamar fetchVersion de novo
      const sockPromise2 = factory();
      await vi.advanceTimersByTimeAsync(0);
      const sock2 = await sockPromise2;
      expect(sock2).toBeDefined();

      // Busca ocorreu UMA ÚNICA VEZ em duas criações de socket
      expect(fetchCalls).toBe(1);
    }, 15000);

    it('fetchVersion que resolve com sucesso memoiza a versão para a próxima criação', async () => {
      let fetchCalls = 0;
      const fetchVersionSuccess = vi.fn().mockImplementation(async () => {
        fetchCalls += 1;
        return { version: [2, 3000, 101] as [number, number, number] };
      });

      const makeFakeSocket = vi.fn().mockReturnValue({ ev: { on: vi.fn() } });
      const fakeUseAuthState = vi.fn().mockResolvedValue({
        state: { creds: {}, keys: {} },
        saveCreds: vi.fn(),
      });

      const factory = createBaileysSocketFactory(dir, 'silent', {
        fetchVersion: fetchVersionSuccess,
        makeWASocket: makeFakeSocket,
        useMultiFileAuthState: fakeUseAuthState,
      });

      const sock1 = await factory();
      expect(sock1).toBeDefined();
      expect(fetchCalls).toBe(1);
      expect(makeFakeSocket).toHaveBeenLastCalledWith(
        expect.objectContaining({ version: [2, 3000, 101] })
      );

      const sock2 = await factory();
      expect(sock2).toBeDefined();
      expect(fetchCalls).toBe(1);
    });
  });

  // ---------------------------------------------------------------------------
  // Item 11: clearAuthDir preserva ponto de montagem e propaga EACCES
  // ---------------------------------------------------------------------------
  describe('Item 11: clearAuthDir preserva raiz e propaga erros de permissão', () => {
    it('apaga apenas os arquivos internos, mantendo a raiz preservada e vazia', () => {
      const file1 = path.join(dir, 'creds.json');
      const file2 = path.join(dir, 'app-state-sync-key.json');
      fs.writeFileSync(file1, '{"me": true}');
      fs.writeFileSync(file2, '{"key": "abc"}');

      clearAuthDir(dir);

      // O diretório raiz continua existindo (não quebra o mount point Docker)
      expect(fs.existsSync(dir)).toBe(true);

      // Mas todos os arquivos internos foram removidos
      const remaining = fs.readdirSync(dir);
      expect(remaining).toHaveLength(0);
    });

    it('propaga erro de permissão EACCES simulado', () => {
      vi.spyOn(fs, 'readdirSync').mockImplementationOnce(() => {
        const error = new Error('Permission denied') as Error & { code: string };
        error.code = 'EACCES';
        throw error;
      });

      expect(() => clearAuthDir(dir)).toThrowError(/Permission denied/);
    });

    it('tolera erro ENOENT se o diretório não existir', () => {
      const nonExistent = path.join(dir, 'pasta-inexistente');
      expect(() => clearAuthDir(nonExistent)).not.toThrow();
    });
  });
});
