/**
 * Utilitários de higienização e formatação de números de telefone para o padrão do WhatsApp/Baileys.
 */

export class NumeroInvalidoError extends Error {
  constructor(whatsapp: string) {
    super(`Número de WhatsApp inválido: ${whatsapp}`);
    this.name = 'NumeroInvalidoError';
  }
}

/**
 * Normaliza um número para o padrão Baileys (apenas dígitos com DDI 55).
 * - Números com 10 ou 11 dígitos (DDD + número) recebem o prefixo 55.
 * - Números com 12 ou 13 dígitos iniciados por 55 são mantidos.
 * - Qualquer outro formato lança NumeroInvalidoError.
 */
export function normalizeWhatsAppNumber(value: string): string {
  if (!value || typeof value !== 'string') {
    throw new NumeroInvalidoError(String(value));
  }

  const digits = value.replace(/\D/g, '');

  if (digits.length === 10 || digits.length === 11) {
    return `55${digits}`;
  }

  if ((digits.length === 12 || digits.length === 13) && digits.startsWith('55')) {
    return digits;
  }

  throw new NumeroInvalidoError(value);
}

/**
 * Converte um número de telefone em um JID de usuário do WhatsApp (@s.whatsapp.net).
 */
export function toWhatsAppJid(value: string): string {
  const normalized = normalizeWhatsAppNumber(value);
  return `${normalized}@s.whatsapp.net`;
}
