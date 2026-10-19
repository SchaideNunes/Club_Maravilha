import { describe, expect, it, vi } from 'vitest';
import axios, { AxiosError, AxiosHeaders } from 'axios';
import { extrairMensagemErro } from './errors';

describe('client baseURL em produção (Item 11)', () => {
  it('com VITE_API_URL indefinida e DEV=false, baseURL deve ser /api/v1', async () => {
    vi.resetModules();
    vi.stubEnv('VITE_API_URL', undefined as unknown as string);
    vi.stubEnv('DEV', false);

    const module = await import('./client');
    expect(module.apiClient.defaults.baseURL).toBe('/api/v1');

    vi.unstubAllEnvs();
  });
});

describe('extrairMensagemErro (Item 12)', () => {
  it('retorna mensagem para erro 413 Payload Too Large', () => {
    const err = new AxiosError('Payload too large', '413', undefined, undefined, {
      status: 413,
      statusText: 'Payload Too Large',
      data: {},
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(extrairMensagemErro(err, 'Fallback')).toBe(
      'O arquivo enviado excede o limite máximo permitido pelo servidor.'
    );
  });

  it('retorna mensagem para erro 429 Too Many Requests', () => {
    const err = new AxiosError('Too many requests', '429', undefined, undefined, {
      status: 429,
      statusText: 'Too Many Requests',
      data: {},
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(extrairMensagemErro(err, 'Fallback')).toBe(
      'Muitas tentativas em pouco tempo. Por favor, aguarde alguns instantes.'
    );
  });

  it('extrai detail string do corpo da resposta', () => {
    const err = new AxiosError('Erro', '400', undefined, undefined, {
      status: 400,
      statusText: 'Bad Request',
      data: { detail: 'Associado já possui fatura em aberto' },
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(extrairMensagemErro(err, 'Fallback')).toBe('Associado já possui fatura em aberto');
  });

  it('extrai e concatena mensagens de lista de validação do Pydantic v2', () => {
    const err = new AxiosError('Unprocessable Entity', '422', undefined, undefined, {
      status: 422,
      statusText: 'Unprocessable Content',
      data: {
        detail: [
          { loc: ['body', 'nome'], msg: 'Nome é obrigatório', type: 'value_error' },
          { loc: ['body', 'cpf'], msg: 'CPF inválido', type: 'value_error' },
        ],
      },
      headers: {},
      config: { headers: new AxiosHeaders() },
    });
    expect(extrairMensagemErro(err, 'Fallback')).toBe('Nome é obrigatório, CPF inválido');
  });

  it('retorna mensagem de Error nativo ou fallback padrão', () => {
    expect(extrairMensagemErro(new Error('Falha de conexão'), 'Fallback')).toBe('Falha de conexão');
    expect(extrairMensagemErro(null, 'Fallback padrão')).toBe('Fallback padrão');
  });
});
