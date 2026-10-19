import React from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../api/client';
import { formatDateTime, labelWhatsAppStatus } from '../utils/format';

export const DASHBOARD_REFETCH_INTERVAL_MS = 15000;

export type DashboardResumo = {
  total_associados: number;
  faturas_pagas_mes: number;
  faturas_pendentes_mes: number;
  faturas_atrasadas: number;
  disparos_hoje: number;
  disparos_erro_hoje: number;
  whatsapp_status: string;
};

export type DashboardAtividade = {
  tipo: 'DISPARO' | 'BAIXA';
  data: string;
  descricao: string;
  associado_nome: string | null;
  status: string | null;
};

export function DashboardPage(): React.ReactElement {
  const {
    data: resumo,
    isLoading: carregandoResumo,
    isError: erroResumo,
  } = useQuery<DashboardResumo>({
    queryKey: ['dashboard-resumo'],
    queryFn: async () => {
      const res = await apiClient.get<DashboardResumo>('/dashboard/resumo');
      return res.data;
    },
    refetchInterval: DASHBOARD_REFETCH_INTERVAL_MS,
  });

  const {
    data: atividades,
    isLoading: carregandoAtividades,
    isError: erroAtividades,
  } = useQuery<DashboardAtividade[]>({
    queryKey: ['dashboard-atividades'],
    queryFn: async () => {
      const res = await apiClient.get<DashboardAtividade[]>('/dashboard/atividades');
      return res.data;
    },
    refetchInterval: DASHBOARD_REFETCH_INTERVAL_MS,
  });

  if (carregandoResumo || carregandoAtividades) {
    return (
      <div className="p-8">
        <p className="text-slate-500 text-sm">Carregando...</p>
      </div>
    );
  }

  if (erroResumo || erroAtividades) {
    return (
      <div className="p-8">
        <div
          role="alert"
          className="rounded-lg bg-red-50 p-4 text-sm text-red-700 border border-red-200"
        >
          Não foi possível carregar as informações do dashboard. Tente novamente mais tarde.
        </div>
      </div>
    );
  }

  const statusZap = labelWhatsAppStatus(resumo?.whatsapp_status || 'DESCONECTADO');

  return (
    <div className="p-8 space-y-8">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          Dashboard
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Visão geral operacional e financeira do Club Maravilha
        </p>
      </div>

      {/* Grid de 5 Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-4">
        {/* Card 1: Total Associados */}
        <div
          data-testid="card-total-associados"
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Total de Associados
          </p>
          <p className="mt-2 text-3xl font-bold text-slate-900">
            {resumo?.total_associados ?? 0}
          </p>
        </div>

        {/* Card 2: Pagas no Mês */}
        <div
          data-testid="card-pagas-mes"
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Pagas no Mês
          </p>
          <p className="mt-2 text-3xl font-bold text-emerald-600">
            {resumo?.faturas_pagas_mes ?? 0}
          </p>
        </div>

        {/* Card 3: Pendentes / Atrasadas */}
        <div
          data-testid="card-pendentes-atrasadas"
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Pendentes / Atrasadas
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">
              {resumo?.faturas_pendentes_mes ?? 0}
            </span>
            <span className="text-slate-400 text-lg">/</span>
            <span className="text-2xl font-semibold text-rose-600">
              {resumo?.faturas_atrasadas ?? 0}
            </span>
          </div>
        </div>

        {/* Card 4: Disparos Hoje */}
        <div
          data-testid="card-disparos-hoje"
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Disparos Hoje
          </p>
          <div className="mt-2 flex items-baseline gap-2">
            <span className="text-3xl font-bold text-slate-900">
              {resumo?.disparos_hoje ?? 0}
            </span>
            <span className="text-xs font-medium text-rose-600">
              {resumo?.disparos_erro_hoje ?? 0} com erro
            </span>
          </div>
        </div>

        {/* Card 5: Status WhatsApp */}
        <div
          data-testid="card-whatsapp-status"
          className="bg-white p-5 rounded-xl border border-slate-200 shadow-sm"
        >
          <p className="text-xs font-medium text-slate-500 uppercase tracking-wider">
            Status WhatsApp
          </p>
          <div className="mt-2 flex items-center gap-2">
            <span
              className={`w-2.5 h-2.5 rounded-full ${
                statusZap === 'Conectado'
                  ? 'bg-emerald-500'
                  : statusZap === 'Aguardando QR Code'
                  ? 'bg-amber-500'
                  : 'bg-rose-500'
              }`}
            />
            <span className="text-lg font-bold text-slate-900">
              {statusZap}
            </span>
          </div>
        </div>
      </div>

      {/* Atividades Recentes */}
      <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <h2 className="text-base font-semibold text-slate-900 mb-4">
          Atividades Recentes
        </h2>

        {!atividades || atividades.length === 0 ? (
          <p className="text-sm text-slate-500 py-4">Nenhuma atividade recente</p>
        ) : (
          <ul aria-label="Atividades recentes" className="divide-y divide-slate-100">
            {atividades.map((atv, idx) => {
              const isDisparo = atv.tipo === 'DISPARO';
              const isErro = atv.status === 'ERRO';

              return (
                <li
                  key={idx}
                  className="py-3 flex items-center justify-between gap-4 text-sm"
                >
                  <div className="flex items-center gap-3 min-w-0">
                    <span
                      className={`inline-flex items-center px-2 py-0.5 rounded text-xs font-medium ${
                        isDisparo
                          ? 'bg-blue-50 text-blue-700 border border-blue-200'
                          : 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                      }`}
                    >
                      {isDisparo ? 'Disparo' : 'Baixa'}
                    </span>

                    {isErro && (
                      <span className="inline-flex items-center px-2 py-0.5 rounded text-xs font-medium bg-rose-50 text-rose-700 border border-rose-200">
                        Erro
                      </span>
                    )}

                    <span className="font-medium text-slate-900 truncate">
                      {atv.descricao}
                    </span>

                    {atv.associado_nome && (
                      <span className="text-slate-500 truncate text-xs">
                        • {atv.associado_nome}
                      </span>
                    )}
                  </div>

                  <time className="text-xs text-slate-400 shrink-0">
                    {formatDateTime(atv.data)}
                  </time>
                </li>
              );
            })}
          </ul>
        )}
      </div>
    </div>
  );
}

export default DashboardPage;
