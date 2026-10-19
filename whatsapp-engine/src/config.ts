/**
 * Configurações do microsserviço whatsapp-engine carregadas a partir de variáveis de ambiente.
 */

export interface EngineConfig {
  port: number;
  apiKey: string;
  authDir: string;
  logLevel: string;
}

export function loadConfig(env: NodeJS.ProcessEnv | Record<string, string | undefined> = process.env): EngineConfig {
  const apiKey = env.API_KEY?.trim();
  if (!apiKey) {
    throw new Error('A variável de ambiente API_KEY é obrigatória e não pode estar vazia.');
  }

  let port = 3001;
  if (env.PORT !== undefined) {
    const parsed = Number(env.PORT);
    if (!Number.isInteger(parsed) || parsed < 1 || parsed > 65535) {
      throw new Error(`PORT inválida: "${env.PORT}". Deve ser um número inteiro entre 1 e 65535.`);
    }
    port = parsed;
  }

  const authDir = env.AUTH_DIR?.trim() || './auth';
  const logLevel = env.WHATSAPP_LOG_LEVEL?.trim() || 'silent';

  return {
    port,
    apiKey,
    authDir,
    logLevel,
  };
}
