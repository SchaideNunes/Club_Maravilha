import React from 'react';
import { CheckCircle2, XCircle } from 'lucide-react';
import { formatDateTime, formatWhatsApp } from '../../utils/format';

export type LogMensagemItem = {
  id: string;
  associado_id?: string | null;
  associado_nome?: string | null;
  fatura_id?: string | null;
  destinatario: string;
  etapa: string;
  status: 'SUCESSO' | 'ERRO';
  mensagem: string;
  erro?: string | null;
  enviado_em: string;
};

export type DisparosSectionProps = {
  logs: LogMensagemItem[];
  isLoading: boolean;
  etapaFiltro: string;
  onEtapaFiltroChange: (etapa: string) => void;
  statusFiltro: string;
  onStatusFiltroChange: (status: string) => void;
};

export function labelEtapaRegua(etapa: string): string {
  switch (etapa) {
    case 'D_MENOS_3':
      return 'Lembrete D-3';
    case 'D0':
      return 'Cobrança D-0';
    case 'RECIBO':
      return 'Recibo de Pagamento';
    case 'D_MAIS_3':
      return 'Aviso D+3';
    case 'D_MAIS_7':
      return 'Aviso D+7';
    case 'AVULSO':
      return 'Avulso';
    case 'TESTE':
      return 'Teste';
    default:
      return etapa;
  }
}

export function DisparosSection({
  logs,
  isLoading,
  etapaFiltro,
  onEtapaFiltroChange,
  statusFiltro,
  onStatusFiltroChange,
}: DisparosSectionProps): React.ReactElement {
  return (
    <section
      aria-labelledby="sec-disparos"
      role="region"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6"
    >
      <div className="pb-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 id="sec-disparos" className="text-lg font-bold text-slate-900">
            Últimos disparos
          </h2>
          <p className="text-sm text-slate-500">
            Histórico e auditoria de mensagens enviadas pelo motor Baileys via régua e disparos manuais.
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-3">
          <div className="flex flex-col gap-1">
            <label htmlFor="filtro-etapa" className="text-xs font-semibold text-slate-700">
              Filtrar por etapa
            </label>
            <select
              id="filtro-etapa"
              value={etapaFiltro}
              onChange={(e) => onEtapaFiltroChange(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
            >
              <option value="">Todas</option>
              <option value="D_MENOS_3">Lembrete D-3</option>
              <option value="D0">Cobrança D-0</option>
              <option value="RECIBO">Recibo de Pagamento</option>
              <option value="D_MAIS_3">Aviso D+3</option>
              <option value="D_MAIS_7">Aviso D+7</option>
              <option value="AVULSO">Avulso</option>
              <option value="TESTE">Teste</option>
            </select>
          </div>

          <div className="flex flex-col gap-1">
            <label htmlFor="filtro-log-status" className="text-xs font-semibold text-slate-700">
              Filtrar por status
            </label>
            <select
              id="filtro-log-status"
              value={statusFiltro}
              onChange={(e) => onStatusFiltroChange(e.target.value)}
              className="px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
            >
              <option value="">Todos</option>
              <option value="SUCESSO">Sucesso</option>
              <option value="ERRO">Erro</option>
            </select>
          </div>
        </div>
      </div>

      <div className="overflow-x-auto">
        <table className="w-full text-left border-collapse">
          <thead>
            <tr className="border-b border-slate-200 bg-slate-50/75 text-xs font-semibold text-slate-600 uppercase tracking-wider">
              <th scope="col" className="px-4 py-3">Data/Hora</th>
              <th scope="col" className="px-4 py-3">Destinatário</th>
              <th scope="col" className="px-4 py-3">Etapa</th>
              <th scope="col" className="px-4 py-3">Status</th>
              <th scope="col" className="px-4 py-3">Erro</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100 text-sm">
            {isLoading ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-400">
                  Carregando disparos...
                </td>
              </tr>
            ) : logs.length === 0 ? (
              <tr>
                <td colSpan={5} className="px-4 py-8 text-center text-slate-500">
                  Nenhum disparo registrado
                </td>
              </tr>
            ) : (
              logs.map((log) => (
                <tr key={log.id} className="hover:bg-slate-50/50 transition-colors">
                  <td className="px-4 py-3 whitespace-nowrap text-slate-700 font-mono text-xs">
                    {formatDateTime(log.enviado_em)}
                  </td>
                  <td className="px-4 py-3">
                    <div className="font-semibold text-slate-900">
                      {log.associado_nome || formatWhatsApp(log.destinatario)}
                    </div>
                    {log.associado_nome && (
                      <div className="text-xs text-slate-500 font-mono">
                        {formatWhatsApp(log.destinatario)}
                      </div>
                    )}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap text-slate-800">
                    {labelEtapaRegua(log.etapa)}
                  </td>
                  <td className="px-4 py-3 whitespace-nowrap">
                    {log.status === 'SUCESSO' ? (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-emerald-50 text-emerald-700 border border-emerald-200">
                        <CheckCircle2 className="w-3.5 h-3.5" />
                        Sucesso
                      </span>
                    ) : (
                      <span className="inline-flex items-center gap-1 px-2.5 py-0.5 rounded-full text-xs font-semibold bg-rose-50 text-rose-700 border border-rose-200">
                        <XCircle className="w-3.5 h-3.5" />
                        Erro
                      </span>
                    )}
                  </td>
                  <td className="px-4 py-3 text-xs text-rose-600 max-w-xs truncate">
                    {log.erro || '-'}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>
    </section>
  );
}

export default DisparosSection;
