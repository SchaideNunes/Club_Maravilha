/**
 * Feature 5 - Formatação pt-BR do painel admin (`src/admin/utils/format.ts`).
 *
 * Contrato (funções puras):
 * - formatBRL(valor: number | string) -> "R$ 1.234,50" (Intl pt-BR/BRL; aceita o Decimal-string da API).
 * - formatDate(iso) -> "dd/mm/aaaa"; datas sem hora ("2026-10-01") NÃO podem "voltar um dia" pelo fuso.
 * - formatDateTime(iso) -> "dd/mm/aaaa HH:mm" no fuso America/Sao_Paulo (sem vírgula).
 * - formatCPF(cpf) -> "000.000.000-00" (idempotente para CPF já formatado).
 * - formatWhatsApp(numero) -> "(DD) 99999-9999" / "(DD) 3333-4444" a partir do padrão Baileys 55DD...;
 *   valores fora do padrão são devolvidos sem alteração.
 * - labelSituacao: EM_DIA -> "Em dia", PENDENTE -> "Pendente", ATRASADO -> "Atrasado".
 * - labelWhatsAppStatus: CONECTADO -> "Conectado", DESCONECTADO -> "Desconectado",
 *   AGUARDANDO_QRCODE -> "Aguardando QR Code"; desconhecido -> "Desconectado".
 */
import { describe, expect, it } from 'vitest';
import {
  formatBRL,
  formatCPF,
  formatDate,
  formatDateTime,
  formatReferencia,
  formatWhatsApp,
  labelSituacao,
  labelWhatsAppStatus,
  mascararCEP,
  valorParaApi,
  valorParaCampo,
} from './format';

const semNbsp = (texto: string) => texto.replace(/ /g, ' ');

describe('formatBRL', () => {
  it.each([
    [35, 'R$ 35,00'],
    ['35.00', 'R$ 35,00'],
    ['1234.5', 'R$ 1.234,50'],
    [0, 'R$ 0,00'],
  ])('%s -> %s', (valor, esperado) => {
    expect(semNbsp(formatBRL(valor))).toBe(esperado);
  });
});

describe('datas', () => {
  it('formatDate não desloca datas sem hora', () => {
    expect(formatDate('2026-10-15')).toBe('15/10/2026');
    expect(formatDate('2026-10-01')).toBe('01/10/2026');
  });

  it('formatDate aceita datetime ISO', () => {
    expect(formatDate('2026-10-15T13:00:00Z')).toBe('15/10/2026');
  });

  it('formatDateTime usa o fuso do clube', () => {
    expect(formatDateTime('2026-10-15T13:00:00Z')).toBe('15/10/2026 10:00');
    expect(formatDateTime('2026-10-16T02:30:00+00:00')).toBe('15/10/2026 23:30');
  });
});

describe('documentos e telefones', () => {
  it('formatCPF', () => {
    expect(formatCPF('52998224725')).toBe('529.982.247-25');
    expect(formatCPF('529.982.247-25')).toBe('529.982.247-25');
  });

  it('formatWhatsApp', () => {
    expect(formatWhatsApp('5575999998888')).toBe('(75) 99999-8888');
    expect(formatWhatsApp('557532211234')).toBe('(75) 3221-1234');
    expect(formatWhatsApp('12345')).toBe('12345');
  });
});

describe('rótulos', () => {
  it('labelSituacao', () => {
    expect(labelSituacao('EM_DIA')).toBe('Em dia');
    expect(labelSituacao('PENDENTE')).toBe('Pendente');
    expect(labelSituacao('ATRASADO')).toBe('Atrasado');
  });

  it('labelWhatsAppStatus', () => {
    expect(labelWhatsAppStatus('CONECTADO')).toBe('Conectado');
    expect(labelWhatsAppStatus('DESCONECTADO')).toBe('Desconectado');
    expect(labelWhatsAppStatus('AGUARDANDO_QRCODE')).toBe('Aguardando QR Code');
    expect(labelWhatsAppStatus('OUTRO')).toBe('Desconectado');
  });
});

describe('helpers do cadastro de sócios', () => {
  it('formatReferencia converte AAAA-MM em MM/AAAA', () => {
    expect(formatReferencia('2026-11')).toBe('11/2026');
    expect(formatReferencia('inválido')).toBe('inválido');
  });

  it.each([
    ['44001000', '44001-000'],
    ['44001', '44001'],
    ['44.001-0009', '44001-000'],
    ['', ''],
  ])('mascararCEP(%s) -> %s', (entrada, esperado) => {
    expect(mascararCEP(entrada)).toBe(esperado);
  });

  it.each([
    ['150', '150.00'],
    ['150,5', '150.50'],
    ['1.234,56', '1234.56'],
    ['0', '0.00'],
    ['12,345', null],
    ['abc', null],
    ['-10', null],
  ])('valorParaApi(%s) -> %s', (entrada, esperado) => {
    expect(valorParaApi(entrada)).toBe(esperado);
  });

  it('valorParaCampo mostra o decimal da API em pt-BR', () => {
    expect(valorParaCampo('220.00')).toBe('220,00');
    expect(valorParaCampo('x')).toBe('');
  });
});
