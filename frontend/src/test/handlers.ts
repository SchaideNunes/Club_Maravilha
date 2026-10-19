/**
 * Handlers MSW padrão e fixtures que espelham os contratos REAIS do backend (FastAPI /api/v1).
 * Valores monetários Decimal chegam como string JSON (ex.: "35.00"), como o Pydantic serializa.
 */
import { http, HttpResponse } from 'msw';

export const API = 'http://api.test/api/v1';

export const ADMIN_TESTE = {
  id: '11111111-1111-4111-8111-111111111111',
  nome: 'Diretoria Teste',
  email: 'admin@clubmaravilha.com.br',
};

export const TOKEN_TESTE = 'token-jwt-de-teste';

export type AssociadoFixture = {
  id: string;
  nome: string;
  cpf: string;
  whatsapp: string;
  email: string;
  foto_url: string | null;
  observacoes: string | null;
  facial_id: string | null;
  status: 'ATIVO' | 'INADIMPLENTE' | 'BLOQUEADO';
  limite_reservas_ativas: number;
  data_adesao: string;
  dia_vencimento: number;
  convidados_usados_mes: number;
  franquia_convidados: number;
  situacao_financeira: 'EM_DIA' | 'PENDENTE' | 'ATRASADO';
  created_at: string;
  updated_at: string;
};

export function criarAssociado(overrides: Partial<AssociadoFixture> = {}): AssociadoFixture {
  return {
    id: '22222222-2222-4222-8222-222222222222',
    nome: 'Maria Souza',
    cpf: '529.982.247-25',
    whatsapp: '5575999998888',
    email: 'maria@exemplo.com',
    foto_url: null,
    observacoes: null,
    facial_id: null,
    status: 'ATIVO',
    limite_reservas_ativas: 2,
    data_adesao: '2026-01-10',
    dia_vencimento: 10,
    convidados_usados_mes: 5,
    franquia_convidados: 8,
    situacao_financeira: 'EM_DIA',
    created_at: '2026-01-10T12:00:00Z',
    updated_at: '2026-01-10T12:00:00Z',
    ...overrides,
  };
}

export function paginado<T>(items: T[], extra: Partial<{ total: number; page: number; page_size: number; total_pages: number }> = {}) {
  return {
    items,
    total: extra.total ?? items.length,
    page: extra.page ?? 1,
    page_size: extra.page_size ?? 20,
    total_pages: extra.total_pages ?? 1,
  };
}

export const RESUMO_PADRAO = {
  total_associados: 312,
  faturas_pagas_mes: 120,
  faturas_pendentes_mes: 45,
  faturas_atrasadas: 12,
  disparos_hoje: 30,
  disparos_erro_hoje: 2,
  whatsapp_status: 'CONECTADO',
};

// ------------------------------------------------------------------------------
// Feature 6 - Mensalidades (GET /faturas/ com `resumo`) e Central de Configurações
// ------------------------------------------------------------------------------

export type StatusFaturaFixture = 'PENDENTE' | 'ATRASADA' | 'PAGO' | 'CANCELADO';

/** Item de GET /faturas/ (FaturaPainelItemResponse + associado_cpf da Feature 6). */
export type FaturaFixture = {
  id: string;
  associado_id: string;
  associado_nome: string;
  associado_cpf: string;
  referencia_mes: string;
  data_vencimento: string;
  valor_base: string;
  valor_convidados_excedentes: string;
  valor_desconto: string;
  valor_total: string;
  convites_usados: number;
  convites_extras: number;
  status: StatusFaturaFixture;
  forma_pagamento: 'PIX' | 'CARTAO' | 'DINHEIRO' | null;
  data_pagamento: string | null;
  lembretes_ativos: boolean;
};

export function criarFatura(overrides: Partial<FaturaFixture> = {}): FaturaFixture {
  return {
    id: 'f0000000-0000-4000-8000-000000000001',
    associado_id: '22222222-2222-4222-8222-222222222222',
    associado_nome: 'Maria Souza',
    associado_cpf: '529.982.247-25',
    referencia_mes: '2026-11',
    data_vencimento: '2026-11-10',
    valor_base: '150.00',
    valor_convidados_excedentes: '0.00',
    valor_desconto: '0.00',
    valor_total: '150.00',
    convites_usados: 3,
    convites_extras: 0,
    status: 'PENDENTE',
    forma_pagamento: null,
    data_pagamento: null,
    lembretes_ativos: true,
    ...overrides,
  };
}

/** `resumo` de GET /faturas/ (escopo: referencia_mes/associado_id; ignora status, q e paginação). */
export type ResumoFaturasFixture = {
  total: number;
  pagas: number;
  pendentes: number;
  atrasadas: number;
  valor_total: string;
  valor_recebido: string;
};

export const RESUMO_FATURAS_VAZIO: ResumoFaturasFixture = {
  total: 0,
  pagas: 0,
  pendentes: 0,
  atrasadas: 0,
  valor_total: '0.00',
  valor_recebido: '0.00',
};

/** Resposta de GET /api/v1/configuracao (ConfiguracaoResponse). */
export type ConfiguracaoFixture = {
  id: number;
  valor_mensalidade: string;
  franquia_convidados: number;
  valor_convidado_extra: string;
  chave_pix: string | null;
  horario_disparo: string;
  automacao_ativa: boolean;
  template_d_menos_3: string;
  template_d0: string;
  template_recibo: string;
  template_d_mais_3: string;
  template_d_mais_7: string;
  updated_at: string;
};

export const CONFIGURACAO_PADRAO: ConfiguracaoFixture = {
  id: 1,
  valor_mensalidade: '150.00',
  franquia_convidados: 8,
  valor_convidado_extra: '35.00',
  chave_pix: 'financeiro@clubmaravilha.com.br',
  horario_disparo: '08:00',
  automacao_ativa: true,
  template_d_menos_3: 'Olá, {nome}! Sua mensalidade vence em {vencimento}.',
  template_d0: 'Bom dia, {nome}! Vence hoje: {valor_total}. Pix: {chave_pix}',
  template_recibo: 'Recebemos {valor_total}, {nome}. Obrigado!',
  template_d_mais_3: '{nome}, sua mensalidade de {vencimento} está em aberto.',
  template_d_mais_7: 'Atenção, {nome}! Acesso bloqueado até a regularização.',
  updated_at: '2026-10-01T12:00:00Z',
};

/** Handlers mínimos para a casca autenticada (validação opcional de sessão e indicador do WhatsApp). */
export const defaultHandlers = [
  http.get(`${API}/auth/me`, () => HttpResponse.json(ADMIN_TESTE)),
  http.get(`${API}/whatsapp/status`, () => HttpResponse.json({ status: 'CONECTADO' })),
  // Feature 6: páginas /admin/mensalidades e /admin/whatsapp montadas pelos testes de layout/rotas
  http.get(`${API}/faturas/`, () => HttpResponse.json({ ...paginado([]), resumo: RESUMO_FATURAS_VAZIO })),
  http.get(`${API}/configuracao`, () => HttpResponse.json(CONFIGURACAO_PADRAO)),
  http.get(`${API}/whatsapp/qrcode`, () => HttpResponse.json({ status: 'CONECTADO', qrcode: null })),
  http.get(`${API}/whatsapp/logs`, () => HttpResponse.json([])),
];
