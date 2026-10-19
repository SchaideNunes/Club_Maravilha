import { setupServer } from 'msw/node';
import { defaultHandlers } from './handlers';

/** Servidor MSW compartilhado pelos testes; use `server.use(...)` para sobrescrever handlers. */
export const server = setupServer(...defaultHandlers);
