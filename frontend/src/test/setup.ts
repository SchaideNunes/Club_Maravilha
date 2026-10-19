/**
 * Setup global do Vitest (jsdom): matchers do jest-dom, servidor MSW sem rede e limpeza entre testes.
 *
 * - Toda requisição HTTP precisa de um handler MSW (`onUnhandledRequest: 'error'`): nenhum teste
 *   fala com a rede real. A origem da API nos testes é `http://api.test` (VITE_API_URL no vitest.config.ts).
 * - localStorage/sessionStorage são limpos a cada teste (sessão do admin começa deslogada).
 */
import '@testing-library/jest-dom/vitest';
import { cleanup } from '@testing-library/react';
import { afterAll, afterEach, beforeAll, vi } from 'vitest';
import { File as NodeFile, Blob as NodeBlob } from 'node:buffer';
import { server } from './server';

// O FormData/File/Blob do jsdom não são reconhecidos pelo fetch/Request do Node, que o MSW usa para
// ler o corpo das requisições: um upload multipart chegaria como "[object FormData]". Troca pelas
// implementações nativas do Node (as mesmas do Request/Response globais), preservando o restante do jsdom.
const NodeFormData = (await new Response('a=1', { headers: { 'Content-Type': 'application/x-www-form-urlencoded' } }).formData()).constructor as typeof FormData;
Object.assign(globalThis, { FormData: NodeFormData, File: NodeFile, Blob: NodeBlob });

// jsdom não implementa scrollTo/matchMedia; a landing e alguns componentes os chamam.
Object.defineProperty(window, 'scrollTo', { value: vi.fn(), writable: true });
if (!window.matchMedia) {
  Object.defineProperty(window, 'matchMedia', {
    writable: true,
    value: (query: string) => ({
      matches: false,
      media: query,
      onchange: null,
      addListener: () => {},
      removeListener: () => {},
      addEventListener: () => {},
      removeEventListener: () => {},
      dispatchEvent: () => false,
    }),
  });
}

beforeAll(() => {
  server.listen({ onUnhandledRequest: 'error' });
});

afterEach(() => {
  cleanup();
  server.resetHandlers();
  window.localStorage.clear();
  window.sessionStorage.clear();
  vi.useRealTimers();
});

afterAll(() => {
  server.close();
});
