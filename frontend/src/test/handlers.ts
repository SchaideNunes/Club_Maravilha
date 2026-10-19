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

/** Handlers mínimos para a casca autenticada (validação opcional de sessão e indicador do WhatsApp). */
export const defaultHandlers = [
  http.get(`${API}/auth/me`, () => HttpResponse.json(ADMIN_TESTE)),
  http.get(`${API}/whatsapp/status`, () => HttpResponse.json({ status: 'CONECTADO' })),
];
