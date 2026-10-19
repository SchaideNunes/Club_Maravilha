import React from 'react';
import { CheckCircle, AlertTriangle, Clock, XCircle } from 'lucide-react';
import { FaturaItem } from './BaixaManualModal';
import { formatBRL, formatDate } from '../../utils/format';

export type MensalidadesTabelaProps = {
  faturas: FaturaItem[];
  isLoading: boolean;
  isError: boolean;
  onBaixaManual: (fatura: FaturaItem) => void;
  onCobrarWhatsApp: (fatura: FaturaItem) => void;
  isCobrandoId?: string | null;
};

export function MensalidadesTabela({
  faturas,
  isLoading,
  isError,
  onBaixaManual,
  onCobrarWhatsApp,
  isCobrandoId,
}: MensalidadesTabelaProps): React.ReactElement {
  if (isError) {
    return (
      <div
        role="alert"
        className="p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm flex items-center gap-2"
      >
        <XCircle className="w-5 h-5 text-rose-600 shrink-0" />
        <span>Não foi possível carregar as faturas. Tente novamente mais tarde.</span>
      </div>
    );
  }

  const renderStatusBadge = (status: FaturaItem['status']) => {
    switch (status) {
      case 'PAGO':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
            <CheckCircle className="w-3.5 h-3.5" />
            Paga
          </span>
        );
      case 'ATRASADA':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
            <AlertTriangle className="w-3.5 h-3.5" />
            Atrasada
          </span>
        );
      case 'PENDENTE':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-amber-50 text-amber-700 border border-amber-200">
            <Clock className="w-3.5 h-3.5" />
            Pendente
          </span>
        );
      case 'CANCELADO':
        return (
          <span className="inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-semibold bg-slate-100 text-slate-700 border border-slate-200">
            <XCircle className="w-3.5 h-3.5" />
            Cancelada
          </span>
        );
    }
  };

  return (
    <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/75 text-xs font-semibold text-slate-600 uppercase tracking-wider">
              <th scope="col" className="px-4 py-3.5">Associado</th>
              <th scope="col" className="px-4 py-3.5">Vencimento</th>
              <th scope="col" className="px-4 py-3.5">Valor Base</th>
              <th scope="col" className="px-4 py-3.5">Acréscimo Convidados</th>
              <th scope="col" className="px-4 py-3.5">Valor Total</th>
              <th scope="col" className="px-4 py-3.5">Status</th>
              <th scope="col" className="px-4 py-3.5 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {isLoading ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-400">
                  Carregando faturas...
                </td>
              </tr>
            ) : faturas.length === 0 ? (
              <tr>
                <td colSpan={7} className="px-4 py-8 text-center text-slate-500">
                  Nenhuma fatura encontrada
                </td>
              </tr>
            ) : (
              faturas.map((fatura) => {
                const podeOperar = fatura.status === 'PENDENTE' || fatura.status === 'ATRASADA';
                const cobrandoEste = isCobrandoId === fatura.id;

                return (
                  <tr key={fatura.id} className="hover:bg-slate-50/50 transition-colors">
                    <td className="px-4 py-3.5">
                      <div className="font-semibold text-slate-900">{fatura.associado_nome}</div>
                      {fatura.associado_cpf && (
                        <div className="text-xs text-slate-400">{fatura.associado_cpf}</div>
                      )}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 whitespace-nowrap">
                      {formatDate(fatura.data_vencimento)}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 whitespace-nowrap">
                      {formatBRL(fatura.valor_base)}
                    </td>
                    <td className="px-4 py-3.5 text-slate-600 whitespace-nowrap">
                      {formatBRL(fatura.valor_convidados_excedentes)}
                    </td>
                    <td className="px-4 py-3.5 font-semibold text-slate-900 whitespace-nowrap">
                      {formatBRL(fatura.valor_total)}
                    </td>
                    <td className="px-4 py-3.5 whitespace-nowrap">
                      {renderStatusBadge(fatura.status)}
                    </td>
                    <td className="px-4 py-3.5 text-right whitespace-nowrap">
                      <div className="inline-flex items-center justify-end gap-2">
                        <button
                          type="button"
                          onClick={() => onBaixaManual(fatura)}
                          disabled={!podeOperar}
                          title={podeOperar ? 'Dar baixa manual' : 'Fatura já liquidada ou cancelada'}
                          aria-label={`Dar baixa manual para ${fatura.associado_nome}`}
                          className="px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40 disabled:cursor-not-allowed border-slate-300 text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                        >
                          Dar Baixa Manual
                        </button>

                        <button
                          type="button"
                          onClick={() => onCobrarWhatsApp(fatura)}
                          disabled={!podeOperar || cobrandoEste}
                          title={podeOperar ? 'Cobrar agora via WhatsApp' : 'Fatura já liquidada ou cancelada'}
                          aria-label={`Cobrar agora via WhatsApp para ${fatura.associado_nome}`}
                          className="px-2.5 py-1.5 text-xs font-medium rounded-lg border transition-colors disabled:opacity-40 disabled:cursor-not-allowed border-slate-300 text-slate-700 bg-white hover:bg-slate-50 focus:outline-none focus:ring-2 focus:ring-slate-400"
                        >
                          {cobrandoEste ? 'Enviando...' : 'Cobrar Agora via WhatsApp'}
                        </button>
                      </div>
                    </td>
                  </tr>
                );
              })
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}

export default MensalidadesTabela;
