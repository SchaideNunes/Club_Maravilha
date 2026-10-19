/**
 * Contrato (src/utils/phone.ts):
 * - normalizeWhatsAppNumber(value): só dígitos no padrão Baileys (DDI 55).
 *   10/11 dígitos (DDD + número) recebem o prefixo 55 (inclusive DDD 55);
 *   12/13 dígitos iniciados por 55 são mantidos. Qualquer outro formato lança NumeroInvalidoError.
 * - toWhatsAppJid(value): número normalizado + "@s.whatsapp.net".
 */
import { describe, expect, it } from 'vitest';
import { NumeroInvalidoError, normalizeWhatsAppNumber, toWhatsAppJid } from './phone.js';

describe('normalizeWhatsAppNumber', () => {
  it('remove pontuação e mantém o DDI 55 já informado', () => {
    expect(normalizeWhatsAppNumber('+55 (75) 99999-9999')).toBe('5575999999999');
    expect(normalizeWhatsAppNumber('5575999999999')).toBe('5575999999999');
    expect(normalizeWhatsAppNumber('557533334444')).toBe('557533334444');
  });

  it('prefixa 55 em números com 10 ou 11 dígitos (DDD + número)', () => {
    expect(normalizeWhatsAppNumber('(75) 99999-9999')).toBe('5575999999999');
    expect(normalizeWhatsAppNumber('75999999999')).toBe('5575999999999');
    expect(normalizeWhatsAppNumber('7533334444')).toBe('557533334444');
  });

  it('não confunde o DDD 55 com o DDI', () => {
    expect(normalizeWhatsAppNumber('(55) 99999-8888')).toBe('5555999998888');
  });

  it.each(['', '   ', '12345', '999999999999999', '447911123456', 'abc'])(
    'rejeita valor inválido %j com NumeroInvalidoError',
    (valor) => {
      expect(() => normalizeWhatsAppNumber(valor)).toThrow(NumeroInvalidoError);
    },
  );
});

describe('toWhatsAppJid', () => {
  it('monta o JID de usuário @s.whatsapp.net a partir do número normalizado', () => {
    expect(toWhatsAppJid('(75) 99999-9999')).toBe('5575999999999@s.whatsapp.net');
    expect(toWhatsAppJid('5575999999999')).toBe('5575999999999@s.whatsapp.net');
  });

  it('propaga NumeroInvalidoError para números inválidos', () => {
    expect(() => toWhatsAppJid('123')).toThrow(NumeroInvalidoError);
  });
});
