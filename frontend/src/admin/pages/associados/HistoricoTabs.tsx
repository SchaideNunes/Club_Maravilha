import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { formatBRL, formatDate, formatDateTime, formatReferencia } from '../../utils/format';
import { labelEtapaRegua } from '../whatsapp/DisparosSection';

type FaturaDoSocio = {
  id: string;
  referencia_mes: string;
  data_vencimento: string;
  valor_total: string;
  status: 'PENDENTE' | 'ATRASADA' | 'PAGO' | 'CANCELADO';
  forma_pagamento: string | null;
  data_pagamento: string | null;
};

type ConvidadoDoSocio = {
  id: string;
  nome: string;
  data_visita: string;
  status: 'EMITIDO' | 'UTILIZADO' | 'EXPIRADO' | 'CANCELADO';
  is_gratuito: boolean;
  valor_cobrado: string;
};

type MensagemDoSocio = {
  id: string;
  etapa: string;
  mensagem: string;
  status: 'SUCESSO' | 'ERRO';
  erro: string | null;
  enviado_em: string;
};

const ROTULO_FATURA: Record<FaturaDoSocio['status'], { texto: string; classe: string }> = {
  PAGO: { texto: 'Paga', classe: 'bg-emerald-50 text-emerald-700 border-emerald-200' },
  PENDENTE: { texto: 'Pendente', classe: 'bg-amber-50 text-amber-700 border-amber-200' },
  ATRASADA: { texto: 'Atrasada', classe: 'bg-rose-50 text-rose-700 border-rose-200' },
  CANCELADO: { texto: 'Cancelada', classe: 'bg-slate-100 text-slate-700 border-slate-200' },
};

const ROTULO_CONVIDADO: Record<ConvidadoDoSocio['status'], string> = {
  EMITIDO: 'Emitido',
  UTILIZADO: 'Utilizado',
  EXPIRADO: 'Expirado',
  CANCELADO: 'Cancelado',
};

function Selo({ texto, classe }: { texto: string; classe: string }): React.ReactElement {
  return (
    <span className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${classe}`}>
      {texto}
    </span>
  );
}

function EstadoConsulta({
  isLoading,
  isError,
  vazio,
  mensagemVazio,
  children,
}: {
  isLoading: boolean;
  isError: boolean;
  vazio: boolean;
  mensagemVazio: string;
  children: React.ReactNode;
}): React.ReactElement {
  if (isLoading) return <p className="text-sm text-slate-500">Carregando...</p>;
  if (isError) {
    return (
      <div role="alert" className="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
        Não foi possível carregar o histórico. Tente novamente mais tarde.
      </div>
    );
  }
  if (vazio) return <p className="py-8 text-center text-sm text-slate-500">{mensagemVazio}</p>;
  return <>{children}</>;
}

const TH = 'py-2 pr-4';
const TD = 'py-3 pr-4 text-slate-600 whitespace-nowrap';

export function FinanceiroTab({ associadoId }: { associadoId: string }): React.ReactElement {
  const { data, isLoading, isError } = useQuery<FaturaDoSocio[]>({
    queryKey: ['faturas', 'associado', associadoId],
    queryFn: async () =>
      (
        await apiClient.get<{ items: FaturaDoSocio[] }>('/faturas/', {
          params: { associado_id: associadoId, page_size: 100 },
        })
      ).data.items,
  });
  const faturas = data ?? [];

  return (
    <EstadoConsulta isLoading={isLoading} isError={isError} vazio={faturas.length === 0} mensagemVazio="Nenhuma fatura">
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="text-slate-600 font-semibold">
          <tr>
            <th scope="col" className={TH}>Referência</th>
            <th scope="col" className={TH}>Vencimento</th>
            <th scope="col" className={TH}>Valor</th>
            <th scope="col" className={TH}>Status</th>
            <th scope="col" className={TH}>Pagamento</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {faturas.map((fatura) => (
            <tr key={fatura.id}>
              <td className={`${TD} font-medium text-slate-900`}>{formatReferencia(fatura.referencia_mes)}</td>
              <td className={TD}>{formatDate(fatura.data_vencimento)}</td>
              <td className={TD}>{formatBRL(fatura.valor_total)}</td>
              <td className={TD}>
                <Selo {...ROTULO_FATURA[fatura.status]} />
              </td>
              <td className={TD}>
                {fatura.data_pagamento
                  ? `${formatDate(fatura.data_pagamento)}${fatura.forma_pagamento ? ` · ${fatura.forma_pagamento}` : ''}`
                  : '—'}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </EstadoConsulta>
  );
}

export function ConvidadosTab({ associadoId }: { associadoId: string }): React.ReactElement {
  const { data, isLoading, isError } = useQuery<ConvidadoDoSocio[]>({
    queryKey: ['convidados', 'associado', associadoId],
    queryFn: async () =>
      (await apiClient.get<ConvidadoDoSocio[]>('/convidados/', { params: { associado_id: associadoId, limit: 100 } }))
        .data,
  });
  const convidados = data ?? [];

  return (
    <EstadoConsulta
      isLoading={isLoading}
      isError={isError}
      vazio={convidados.length === 0}
      mensagemVazio="Nenhum convite emitido"
    >
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="text-slate-600 font-semibold">
          <tr>
            <th scope="col" className={TH}>Convidado</th>
            <th scope="col" className={TH}>Visita</th>
            <th scope="col" className={TH}>Status</th>
            <th scope="col" className={TH}>Cobrança</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {convidados.map((convidado) => (
            <tr key={convidado.id}>
              <td className={`${TD} font-medium text-slate-900`}>{convidado.nome}</td>
              <td className={TD}>{formatDate(convidado.data_visita)}</td>
              <td className={TD}>{ROTULO_CONVIDADO[convidado.status] ?? convidado.status}</td>
              <td className={TD}>{convidado.is_gratuito ? 'Gratuito' : formatBRL(convidado.valor_cobrado)}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </EstadoConsulta>
  );
}

export function MensagensTab({ associadoId }: { associadoId: string }): React.ReactElement {
  const { data, isLoading, isError } = useQuery<MensagemDoSocio[]>({
    queryKey: ['whatsapp-logs', 'associado', associadoId],
    queryFn: async () =>
      (await apiClient.get<MensagemDoSocio[]>('/whatsapp/logs', { params: { associado_id: associadoId, limit: 100 } }))
        .data,
  });
  const mensagens = data ?? [];

  return (
    <EstadoConsulta
      isLoading={isLoading}
      isError={isError}
      vazio={mensagens.length === 0}
      mensagemVazio="Nenhuma mensagem enviada"
    >
      <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
        <thead className="text-slate-600 font-semibold">
          <tr>
            <th scope="col" className={TH}>Data</th>
            <th scope="col" className={TH}>Mensagem</th>
            <th scope="col" className={TH}>Status</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-100">
          {mensagens.map((mensagem) => (
            <tr key={mensagem.id}>
              <td className={TD}>{formatDateTime(mensagem.enviado_em)}</td>
              <td className="py-3 pr-4 text-slate-600">
                <span className="font-medium text-slate-900">{labelEtapaRegua(mensagem.etapa)}</span>
                <p className="mt-0.5 text-xs text-slate-500 line-clamp-2" title={mensagem.mensagem}>
                  {mensagem.mensagem}
                </p>
              </td>
              <td className={TD}>
                {mensagem.status === 'SUCESSO' ? (
                  <Selo texto="Enviada" classe="bg-emerald-50 text-emerald-700 border-emerald-200" />
                ) : (
                  <span title={mensagem.erro ?? undefined}>
                    <Selo texto="Erro" classe="bg-rose-50 text-rose-700 border-rose-200" />
                  </span>
                )}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </EstadoConsulta>
  );
}
