export type StatusAssociado = 'ATIVO' | 'INADIMPLENTE' | 'BLOQUEADO';

export interface Associado {
  id: string;
  nome: string;
  cpf: string;
  whatsapp: string;
  email: string;
  foto_url?: string;
  facial_id?: string;
  status: StatusAssociado;
  limite_reservas_ativas: number;
  data_adesao: string;
  created_at: string;
  updated_at: string;
}

export type StatusFatura = 'PENDENTE' | 'PAGO' | 'CANCELADO' | 'VENCIDO';
export type FormaPagamento = 'PIX' | 'CARTAO_CREDITO' | 'DINHEIRO' | 'BOLETO';

export interface Fatura {
  id: string;
  associado_id: string;
  referencia_mes: string;
  valor_base: number;
  valor_convidados_excedentes: number;
  valor_desconto: number;
  valor_total: number;
  data_vencimento: string;
  data_pagamento?: string;
  status: StatusFatura;
  forma_pagamento: FormaPagamento;
  txid?: string;
  pix_copia_cola?: string;
  pix_qr_code_url?: string;
  created_at: string;
}

export type TipoQuadra = 'TENIS_1' | 'TENIS_2' | 'BEACH_TENNIS_1' | 'BEACH_TENNIS_2' | 'FUTEBOL_SOCIETY';
export type StatusAgendamento = 'CONFIRMADO' | 'CANCELADO' | 'CONCLUIDO' | 'NO_SHOW';

export interface AgendamentoQuadra {
  id: string;
  associado_id: string;
  quadra: TipoQuadra;
  data_inicio: string;
  data_fim: string;
  status: StatusAgendamento;
  observacoes?: string;
  created_at: string;
}

export type StatusConvidado = 'EMITIDO' | 'UTILIZADO' | 'EXPIRADO' | 'CANCELADO';

export interface Convidado {
  id: string;
  associado_titular_id: string;
  nome: string;
  cpf?: string;
  data_visita: string;
  qr_code_token: string;
  status: StatusConvidado;
  is_gratuito: boolean;
  valor_cobrado: number;
  fatura_agregada_id?: string;
  check_in_at?: string;
  created_at: string;
}
