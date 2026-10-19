/// <reference types="vitest" />
import { fileURLToPath } from 'node:url';
import { defineConfig, mergeConfig } from 'vitest/config';
import viteConfig from './vite.config';

// Fuso fixo: as formatações de data/hora (pt-BR) dos testes não dependem da máquina.
process.env.TZ = 'America/Sao_Paulo';

export default mergeConfig(
  viteConfig,
  defineConfig({
    resolve: {
      alias: {
        // No jsdom o Vitest resolve o axios pela condição "node" (adapter/FormData do Node), que não
        // reconhece o FormData do jsdom e quebra uploads multipart. Usa a build de navegador, como no app real.
        axios: fileURLToPath(new URL('./node_modules/axios/dist/esm/axios.js', import.meta.url)),
      },
    },
    test: {
      environment: 'jsdom',
      setupFiles: ['./src/test/setup.ts'],
      include: ['src/**/*.test.{ts,tsx}'],
      css: false,
      restoreMocks: true,
      // import.meta.env.VITE_API_URL nos testes: as requisições são interceptadas pelo MSW nesta origem.
      env: {
        VITE_API_URL: 'http://api.test',
      },
    },
  }),
);
