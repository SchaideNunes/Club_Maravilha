import React from 'react';
import { AlertCircle, CheckCircle2, Save } from 'lucide-react';

export type ParametrosConfig = {
  valor_mensalidade: string;
  franquia_convidados: number;
  valor_convidado_extra: string;
  horario_disparo: string;
  automacao_ativa: boolean;
};

export type ParametrosSectionProps = {
  values: ParametrosConfig;
  onChange: <K extends keyof ParametrosConfig>(campo: K, valor: ParametrosConfig[K]) => void;
  onSalvar: () => void;
  isSalvando?: boolean;
  mensagemSucesso?: string | null;
  mensagemErro?: string | null;
};

export function ParametrosSection({
  values,
  onChange,
  onSalvar,
  isSalvando,
  mensagemSucesso,
  mensagemErro,
}: ParametrosSectionProps): React.ReactElement {
  return (
    <section
      aria-labelledby="sec-parametros"
      role="region"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6"
    >
      <div className="pb-4 border-b border-slate-100 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
        <div>
          <h2 id="sec-parametros" className="text-lg font-bold text-slate-900">
            Parâmetros gerais
          </h2>
          <p className="text-sm text-slate-500">
            Regras de faturamento, franquias de convites e agendamento da régua diária de cobrança.
          </p>
        </div>

        <button
          type="button"
          onClick={onSalvar}
          disabled={isSalvando}
          className="flex items-center justify-center gap-2 px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50 whitespace-nowrap self-start sm:self-auto"
        >
          <Save className="w-4 h-4" />
          <span>{isSalvando ? 'Salvando...' : 'Salvar configurações'}</span>
        </button>
      </div>

      {mensagemSucesso && (
        <div className="p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm flex items-center gap-2">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="flex-1 font-medium">{mensagemSucesso}</span>
        </div>
      )}

      {mensagemErro && (
        <div
          role="alert"
          className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-sm flex items-center gap-2"
        >
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="flex-1 font-medium">{mensagemErro}</span>
        </div>
      )}

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="cfg-valor-mensalidade" className="text-xs font-semibold text-slate-700">
            Valor da mensalidade (R$)
          </label>
          <input
            id="cfg-valor-mensalidade"
            type="number"
            step="0.01"
            value={values.valor_mensalidade}
            onChange={(e) => onChange('valor_mensalidade', e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="cfg-franquia-convidados" className="text-xs font-semibold text-slate-700">
            Convidados gratuitos por mês
          </label>
          <input
            id="cfg-franquia-convidados"
            type="number"
            value={values.franquia_convidados}
            onChange={(e) => onChange('franquia_convidados', Number(e.target.value))}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="cfg-valor-convidado-extra" className="text-xs font-semibold text-slate-700">
            Taxa por convidado extra (R$)
          </label>
          <input
            id="cfg-valor-convidado-extra"
            type="number"
            step="0.01"
            value={values.valor_convidado_extra}
            onChange={(e) => onChange('valor_convidado_extra', e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="cfg-horario-disparo" className="text-xs font-semibold text-slate-700">
            Horário diário de disparo
          </label>
          <input
            id="cfg-horario-disparo"
            type="time"
            value={values.horario_disparo}
            onChange={(e) => onChange('horario_disparo', e.target.value)}
            className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
          />
        </div>
      </div>

      <div className="pt-2 border-t border-slate-100">
        <label className="flex items-center gap-3 cursor-pointer">
          <input
            type="checkbox"
            checked={values.automacao_ativa}
            onChange={(e) => onChange('automacao_ativa', e.target.checked)}
            className="w-4 h-4 rounded text-slate-900 border-slate-300 focus:ring-slate-400"
          />
          <span className="text-sm font-semibold text-slate-800">Automação da régua</span>
        </label>
        <p className="mt-1 text-xs text-slate-500 pl-7">
          Quando ativado, os lembretes, cobranças e bloqueios serão executados diariamente no horário configurado.
        </p>
      </div>
    </section>
  );
}

export default ParametrosSection;
