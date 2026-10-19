import express, { Express, Request, Response, NextFunction } from 'express';
import {
  IWhatsAppGateway,
  NumeroSemWhatsAppError,
  WhatsAppDesconectadoError,
} from './services/whatsapp-gateway.interface.js';
import { NumeroInvalidoError } from './utils/phone.js';

export interface AppOptions {
  gateway: IWhatsAppGateway;
  apiKey: string;
}

export function createApp(options: AppOptions): Express {
  const { gateway, apiKey } = options;

  if (!apiKey || !apiKey.trim()) {
    throw new Error('A API_KEY é obrigatória para inicializar a aplicação.');
  }

  const app = express();

  // Parsing JSON com tratamento de erro de sintaxe
  app.use(express.json());
  app.use((err: unknown, _req: Request, res: Response, next: NextFunction) => {
    if (err instanceof SyntaxError && 'body' in err) {
      res.status(400).json({ error: 'JSON malformado' });
      return;
    }
    next(err);
  });

  // Rota de health check pública
  app.get('/health', (_req: Request, res: Response) => {
    res.status(200).json({ status: 'ok' });
  });

  // Middleware de autenticação obrigatória via header x-api-key
  app.use((req: Request, res: Response, next: NextFunction) => {
    const key = req.headers['x-api-key'];
    if (!key || key !== apiKey) {
      res.status(401).json({ error: 'Não autorizado: x-api-key inválida ou ausente.' });
      return;
    }
    next();
  });

  // GET /status
  app.get('/status', async (_req: Request, res: Response) => {
    try {
      const status = await gateway.checkInstanceStatus();
      res.status(200).json({ state: status.state });
    } catch (err: unknown) {
      const error = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error });
    }
  });

  // GET /qr
  app.get('/qr', async (_req: Request, res: Response) => {
    try {
      const qrResult = await gateway.getQrCode();
      res.status(200).json({
        state: qrResult.state,
        qrcode: qrResult.qrcode ?? null,
      });
    } catch (err: unknown) {
      const error = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error });
    }
  });

  // POST /send
  app.post('/send', async (req: Request, res: Response) => {
    const body = req.body;
    if (!body || typeof body !== 'object') {
      res.status(400).json({ error: 'Payload inválido', code: 'PAYLOAD_INVALIDO' });
      return;
    }

    const { numero, mensagem } = body as Record<string, unknown>;

    if (
      typeof numero !== 'string' ||
      !numero.trim() ||
      typeof mensagem !== 'string' ||
      !mensagem.trim() ||
      mensagem.length > 4096
    ) {
      res.status(400).json({ error: 'Payload inválido', code: 'PAYLOAD_INVALIDO' });
      return;
    }

    try {
      const result = await gateway.sendText(numero, mensagem);
      res.status(200).json(result);
    } catch (err: unknown) {
      if (err instanceof NumeroInvalidoError) {
        res.status(400).json({ error: err.message, code: 'NUMERO_INVALIDO' });
        return;
      }
      if (err instanceof NumeroSemWhatsAppError) {
        res.status(422).json({ error: err.message, code: 'NUMERO_SEM_WHATSAPP' });
        return;
      }
      if (err instanceof WhatsAppDesconectadoError) {
        res.status(503).json({ error: err.message, code: 'WHATSAPP_DESCONECTADO' });
        return;
      }
      const error = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error });
    }
  });

  // POST /logout
  app.post('/logout', async (_req: Request, res: Response) => {
    try {
      await gateway.logout();
      const status = await gateway.checkInstanceStatus();
      res.status(200).json({ state: status.state });
    } catch (err: unknown) {
      const error = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error });
    }
  });

  // POST /restart
  app.post('/restart', async (_req: Request, res: Response) => {
    try {
      await gateway.restart();
      const status = await gateway.checkInstanceStatus();
      res.status(200).json({ state: status.state });
    } catch (err: unknown) {
      const error = err instanceof Error ? err.message : String(err);
      res.status(500).json({ error });
    }
  });

  // 404 para rotas não mapeadas
  app.use((_req: Request, res: Response) => {
    res.status(404).json({ error: 'Rota não encontrada' });
  });

  // Middleware de erro genérico
  app.use((err: unknown, _req: Request, res: Response, _next: NextFunction) => {
    const error = err instanceof Error ? err.message : 'Erro interno no servidor';
    res.status(500).json({ error });
  });

  return app;
}
