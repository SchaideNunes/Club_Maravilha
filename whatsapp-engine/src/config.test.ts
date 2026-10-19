/**
 * Contrato (src/config.ts):
 * loadConfig(env) -> { port: number, apiKey: string, authDir: string, logLevel: string }
 * - PORT (padrão 3001; inválido lança erro), API_KEY obrigatório (vazio/ausente lança erro citando API_KEY),
 *   AUTH_DIR (padrão "./auth"), WHATSAPP_LOG_LEVEL (padrão "silent").
 */
import { describe, expect, it } from 'vitest';
import { loadConfig } from './config.js';

describe('loadConfig', () => {
  it('aplica os padrões quando só a API_KEY é informada', () => {
    expect(loadConfig({ API_KEY: 'segredo' })).toEqual({
      port: 3001,
      apiKey: 'segredo',
      authDir: './auth',
      logLevel: 'silent',
    });
  });

  it('lê PORT, AUTH_DIR e WHATSAPP_LOG_LEVEL do ambiente', () => {
    const config = loadConfig({
      API_KEY: 'k',
      PORT: '4000',
      AUTH_DIR: '/app/auth',
      WHATSAPP_LOG_LEVEL: 'info',
    });
    expect(config).toEqual({ port: 4000, apiKey: 'k', authDir: '/app/auth', logLevel: 'info' });
  });

  it.each([undefined, '', '   '])('exige API_KEY (valor %j)', (valor) => {
    expect(() => loadConfig({ API_KEY: valor })).toThrow(/API_KEY/);
  });

  it.each(['abc', '0', '70000'])('rejeita PORT inválida %j', (porta) => {
    expect(() => loadConfig({ API_KEY: 'k', PORT: porta })).toThrow(/PORT/);
  });
});
