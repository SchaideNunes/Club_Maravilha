import axios from 'axios';

export type PydanticValidationErrorItem = {
  loc?: (string | number)[];
  msg?: string;
  message?: string;
  type?: string;
};

/**
 * Extrai de forma tipada e segura a mensagem amigável de erro de uma resposta Axios ou exceção genérica.
 * Trata respostas com detail string, lista Pydantic v2 e status comuns (413 Payload Too Large, 429 Rate Limit).
 */
export function extrairMensagemErro(err: unknown, fallback: string): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: unknown; message?: unknown } | undefined;
    const detail = data?.detail ?? data?.message;

    if (typeof detail === 'string' && detail.trim().length > 0) {
      return detail;
    }

    if (Array.isArray(detail)) {
      const mensagens = (detail as PydanticValidationErrorItem[])
        .map((d) => d?.msg || d?.message)
        .filter((msg): msg is string => typeof msg === 'string' && msg.trim().length > 0);
      if (mensagens.length > 0) {
        return mensagens.join(', ');
      }
    }

    if (detail && typeof detail === 'object' && 'msg' in detail) {
      return String((detail as { msg: unknown }).msg);
    }

    const status = err.response?.status;
    if (status === 413) {
      return 'O arquivo enviado excede o limite máximo permitido pelo servidor.';
    }
    if (status === 429) {
      return 'Muitas tentativas em pouco tempo. Por favor, aguarde alguns instantes.';
    }

    if (Array.isArray(detail)) {
      const mensagens = (detail as PydanticValidationErrorItem[])
        .map((d) => d?.msg || d?.message)
        .filter((msg): msg is string => typeof msg === 'string' && msg.trim().length > 0);
      if (mensagens.length > 0) {
        return mensagens.join(', ');
      }
    }

    if (detail && typeof detail === 'object' && 'msg' in detail) {
      return String((detail as { msg: unknown }).msg);
    }

    if (err.message && err.message !== 'Network Error' && !err.message.includes('status code')) {
      return err.message;
    }
  }

  if (err instanceof Error && err.message) {
    return err.message;
  }

  return fallback;
}
