import React from 'react';
import { RefreshCw, Search } from 'lucide-react';

export type MensalidadesFiltrosProps = {
  mes: string;
  onMesChange: (novoMes: string) => void;
  status: string;
  onStatusChange: (novoStatus: string) => void;
  busca: string;
  onBuscaChange: (novaBusca: string) => void;
  onGerarMes: () => void;
  isGerando?: boolean;
};

export function MensalidadesFiltros({
  mes,
  onMesChange,
  status,
  onStatusChange,
  busca,
  onBuscaChange,
  onGerarMes,
  isGerando,
}: MensalidadesFiltrosProps): React.ReactElement {
  return (
    <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm flex flex-col md:flex-row gap-4 items-stretch md:items-end justify-between">
      <div className="flex flex-col sm:flex-row gap-4 flex-1">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="filtro-mes" className="text-xs font-semibold text-slate-700">
            Mês de referência
          </label>
          <input
            id="filtro-mes"
            type="month"
            value={mes}
            onChange={(e) => onMesChange(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="filtro-status" className="text-xs font-semibold text-slate-700">
            Status
          </label>
          <select
            id="filtro-status"
            value={status}
            onChange={(e) => onStatusChange(e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors min-w-[140px]"
          >
            <option value="">Todas</option>
            <option value="PENDENTE">Pendente</option>
            <option value="ATRASADA">Atrasada</option>
            <option value="PAGO">Paga</option>
          </select>
        </div>

        <div className="flex flex-col gap-1.5 flex-1 max-w-md">
          <label htmlFor="filtro-busca" className="text-xs font-semibold text-slate-700">
            Buscar por nome ou CPF
          </label>
          <div className="relative">
            <Search className="w-4 h-4 text-slate-400 absolute left-3 top-1/2 -translate-y-1/2" />
            <input
              id="filtro-busca"
              type="text"
              value={busca}
              onChange={(e) => onBuscaChange(e.target.value)}
              placeholder="Digite o nome ou CPF..."
              className="w-full pl-9 pr-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
            />
          </div>
        </div>
      </div>

      <div className="flex items-center">
        <button
          type="button"
          onClick={onGerarMes}
          disabled={isGerando}
          className="flex items-center justify-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50 disabled:cursor-not-allowed whitespace-nowrap"
        >
          <RefreshCw className={`w-4 h-4 ${isGerando ? 'animate-spin' : ''}`} />
          <span>Gerar faturas do mês</span>
        </button>
      </div>
    </div>
  );
}

export default MensalidadesFiltros;
