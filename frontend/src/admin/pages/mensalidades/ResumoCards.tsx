import React from 'react';
import { formatBRL } from '../../utils/format';

export type ResumoFaturas = {
  total: number;
  pagas: number;
  pendentes: number;
  atrasadas: number;
  valor_total: string;
  valor_recebido: string;
};

export type ResumoCardsProps = {
  resumo?: ResumoFaturas;
  isLoading?: boolean;
};

export function ResumoCards({ resumo, isLoading }: ResumoCardsProps): React.ReactElement {
  if (isLoading && !resumo) {
    return (
      <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
        {[1, 2, 3, 4, 5, 6].map((i) => (
          <div key={i} className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm animate-pulse">
            <div className="h-3 w-16 bg-slate-200 rounded mb-3" />
            <div className="h-7 w-20 bg-slate-200 rounded" />
          </div>
        ))}
      </div>
    );
  }

  const total = resumo?.total ?? 0;
  const pagas = resumo?.pagas ?? 0;
  const pendentes = resumo?.pendentes ?? 0;
  const atrasadas = resumo?.atrasadas ?? 0;
  const valorTotal = formatBRL(resumo?.valor_total ?? '0.00');
  const valorRecebido = formatBRL(resumo?.valor_recebido ?? '0.00');

  return (
    <div className="grid grid-cols-2 md:grid-cols-3 lg:grid-cols-6 gap-4">
      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Total de Faturas</p>
        <p data-testid="resumo-total" className="mt-2 text-2xl font-bold text-slate-900">
          {total}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Pagas</p>
        <p data-testid="resumo-pagas" className="mt-2 text-2xl font-bold text-emerald-600">
          {pagas}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Pendentes</p>
        <p data-testid="resumo-pendentes" className="mt-2 text-2xl font-bold text-amber-600">
          {pendentes}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Atrasadas</p>
        <p data-testid="resumo-atrasadas" className="mt-2 text-2xl font-bold text-rose-600">
          {atrasadas}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Valor Total</p>
        <p data-testid="resumo-valor-total" className="mt-2 text-xl font-bold text-slate-900">
          {valorTotal}
        </p>
      </div>

      <div className="bg-white rounded-xl border border-slate-200 p-4 shadow-sm">
        <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">Valor Recebido</p>
        <p data-testid="resumo-valor-recebido" className="mt-2 text-xl font-bold text-emerald-600">
          {valorRecebido}
        </p>
      </div>
    </div>
  );
}

export default ResumoCards;
