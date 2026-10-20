/**
 * Tipos do cadastro de sócios, espelhando os schemas do backend (AssociadoResponse, PlanoResponse,
 * MembroFamiliaResponse). Valores monetários Decimal chegam como string ("150.00").
 */

export type StatusAssociado = 'ATIVO' | 'INADIMPLENTE' | 'BLOQUEADO' | 'INATIVO';
export type Sexo = 'MASCULINO' | 'FEMININO' | 'OUTRO';
export type Parentesco = 'CONJUGE' | 'FILHO' | 'ENTEADO' | 'PAI_MAE' | 'IRMAO' | 'OUTRO';

export type PlanoResumo = {
  id: string;
  nome: string;
  valor_mensalidade: string;
};

export type Plano = PlanoResumo & {
  descricao: string | null;
  ativo: boolean;
  total_associados: number;
};

export type Associado = {
  id: string;
  nome: string;
  cpf: string;
  whatsapp: string;
  email: string;
  foto_url: string | null;
  observacoes: string | null;
  status: StatusAssociado;
  data_adesao: string;
  dia_vencimento: number;
  convidados_usados_mes: number;
  franquia_convidados: number;
  situacao_financeira: string;
  data_nascimento: string | null;
  rg: string | null;
  sexo: Sexo | null;
  profissao: string | null;
  cep: string | null;
  logradouro: string | null;
  numero: string | null;
  complemento: string | null;
  bairro: string | null;
  cidade: string | null;
  uf: string | null;
  plano: PlanoResumo | null;
  data_inativacao: string | null;
  motivo_inativacao: string | null;
};

export type MembroFamilia = {
  id: string;
  associado_id: string;
  nome: string;
  parentesco: Parentesco;
  cpf: string | null;
  data_nascimento: string | null;
  ativo: boolean;
};

export type InativacaoResposta = {
  associado: Associado;
  faturas_canceladas: number;
  convites_cancelados: number;
  reservas_canceladas: number;
};

export const SEXOS: Array<{ valor: Sexo; rotulo: string }> = [
  { valor: 'FEMININO', rotulo: 'Feminino' },
  { valor: 'MASCULINO', rotulo: 'Masculino' },
  { valor: 'OUTRO', rotulo: 'Outro' },
];

export const PARENTESCOS: Array<{ valor: Parentesco; rotulo: string }> = [
  { valor: 'CONJUGE', rotulo: 'Cônjuge' },
  { valor: 'FILHO', rotulo: 'Filho(a)' },
  { valor: 'ENTEADO', rotulo: 'Enteado(a)' },
  { valor: 'PAI_MAE', rotulo: 'Pai/Mãe' },
  { valor: 'IRMAO', rotulo: 'Irmão(ã)' },
  { valor: 'OUTRO', rotulo: 'Outro' },
];

export const UFS = [
  'AC', 'AL', 'AP', 'AM', 'BA', 'CE', 'DF', 'ES', 'GO', 'MA', 'MT', 'MS', 'MG', 'PA',
  'PB', 'PR', 'PE', 'PI', 'RJ', 'RN', 'RS', 'RO', 'RR', 'SC', 'SP', 'SE', 'TO',
];

export function labelParentesco(parentesco: string): string {
  return PARENTESCOS.find((p) => p.valor === parentesco)?.rotulo ?? parentesco;
}

export function labelStatusAssociado(status: string): string {
  switch (status) {
    case 'ATIVO':
      return 'Ativo';
    case 'INADIMPLENTE':
      return 'Inadimplente';
    case 'BLOQUEADO':
      return 'Bloqueado';
    case 'INATIVO':
      return 'Inativo';
    default:
      return status;
  }
}
