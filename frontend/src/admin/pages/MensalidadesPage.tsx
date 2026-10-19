import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, ChevronLeft, ChevronRight } from 'lucide-react';
import { apiClient } from '../api/client';
import { extrairMensagemErro } from '../api/errors';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import { ResumoCards } from './mensalidades/ResumoCards';
import { MensalidadesFiltros } from './mensalidades/MensalidadesFiltros';
import { MensalidadesTabela } from './mensalidades/MensalidadesTabela';
import { BaixaManualModal, FaturaItem } from './mensalidades/BaixaManualModal';

function mesCorrenteNoClube(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date()).slice(0, 7);
}

export type FaturasApiResponse = {
  items: FaturaItem[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
  resumo: {
    total: number;
    pagas: number;
    pendentes: number;
    atrasadas: number;
    valor_total: string;
    valor_recebido: string;
  };
};

export function MensalidadesPage(): React.ReactElement {
  const queryClient = useQueryClient();

  // Filtros
  const [mes, setMes] = useState<string>(mesCorrenteNoClube);
  const [status, setStatus] = useState<string>('');
  const [buscaInput, setBuscaInput] = useState<string>('');
  const buscaDebounced = useDebouncedValue(buscaInput, 350);
  const [pagina, setPagina] = useState<number>(1);

  // Estados de feedback / alertas
  const [mensagemSucesso, setMensagemSucesso] = useState<string | null>(null);
  const [erroAlerta, setErroAlerta] = useState<string | null>(null);

  // Modal de baixa manual
  const [faturaParaBaixa, setFaturaParaBaixa] = useState<FaturaItem | null>(null);

  // Cobrança WhatsApp em andamento
  const [faturaCobrandoId, setFaturaCobrandoId] = useState<string | null>(null);

  const handleMesChange = (novoMes: string) => {
    setMes(novoMes);
    setPagina(1);
  };

  const handleStatusChange = (novoStatus: string) => {
    setStatus(novoStatus);
    setPagina(1);
  };

  const handleBuscaChange = (novaBusca: string) => {
    setBuscaInput(novaBusca);
    setPagina(1);
  };

  // Consulta faturas
  const { data, isLoading, isError } = useQuery<FaturasApiResponse>({
    queryKey: ['faturas', mes, status, buscaDebounced, pagina],
    queryFn: async () => {
      const params: Record<string, string | number> = {
        page: pagina,
        page_size: 20,
      };
      if (mes) params.referencia_mes = mes;
      if (status) params.status = status;
      if (buscaDebounced.trim()) params.q = buscaDebounced.trim();

      const res = await apiClient.get<FaturasApiResponse>('/faturas/', { params });
      return res.data;
    },
  });

  // Mutação: Gerar faturas do mês
  const gerarMesMutation = useMutation({
    mutationFn: async (refMes: string) => {
      const res = await apiClient.post<{
        referencia_mes: string;
        criadas: number;
        ja_existentes: number;
        total: number;
      }>('/faturas/gerar-mes', { referencia_mes: refMes });
      return res.data;
    },
    onSuccess: (resData) => {
      setErroAlerta(null);
      setMensagemSucesso(`${resData.criadas} criadas, ${resData.ja_existentes} já existentes`);
      queryClient.invalidateQueries({ queryKey: ['faturas'] });
    },
    onError: (err) => {
      setMensagemSucesso(null);
      const msg = extrairMensagemErro(err, 'Erro ao gerar faturas do mês.');
      setErroAlerta(msg);
    },
  });

  // Mutação: Cobrança WhatsApp
  const cobrarMutation = useMutation({
    mutationFn: async (faturaId: string) => {
      setFaturaCobrandoId(faturaId);
      const res = await apiClient.post(`/faturas/${faturaId}/cobrar-whatsapp`);
      return res.data;
    },
    onSuccess: () => {
      setErroAlerta(null);
      setMensagemSucesso('Cobrança enfileirada');
    },
    onError: (err) => {
      setMensagemSucesso(null);
      const msg = extrairMensagemErro(err, 'Não foi possível cobrar fatura via WhatsApp.');
      setErroAlerta(msg);
    },
    onSettled: () => {
      setFaturaCobrandoId(null);
    },
  });

  const handleSucessoBaixa = () => {
    setFaturaParaBaixa(null);
    setErroAlerta(null);
    setMensagemSucesso('Pagamento confirmado — recibo enviado no WhatsApp');
    queryClient.invalidateQueries({ queryKey: ['faturas'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard-resumo'] });
    queryClient.invalidateQueries({ queryKey: ['dashboard-atividades'] });
  };

  return (
    <div className="p-8 space-y-6 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Mensalidades</h1>
        <p className="mt-1 text-sm text-slate-500">
          Gestão de faturas mensais, baixas de pagamento e disparos de cobrança via WhatsApp.
        </p>
      </div>

      {mensagemSucesso && (
        <div className="flex items-center gap-2.5 p-3 rounded-lg bg-emerald-50 border border-emerald-200 text-emerald-800 text-sm">
          <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
          <span className="flex-1 font-medium">{mensagemSucesso}</span>
          <button
            type="button"
            onClick={() => setMensagemSucesso(null)}
            className="text-emerald-600 hover:text-emerald-800 text-xs font-semibold"
          >
            Fechar
          </button>
        </div>
      )}

      {erroAlerta && (
        <div
          role="alert"
          className="flex items-center gap-2.5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm"
        >
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="flex-1 font-medium">{erroAlerta}</span>
          <button
            type="button"
            onClick={() => setErroAlerta(null)}
            className="text-rose-600 hover:text-rose-800 text-xs font-semibold"
          >
            Fechar
          </button>
        </div>
      )}

      <ResumoCards resumo={data?.resumo} isLoading={isLoading} />

      <MensalidadesFiltros
        mes={mes}
        onMesChange={handleMesChange}
        status={status}
        onStatusChange={handleStatusChange}
        busca={buscaInput}
        onBuscaChange={handleBuscaChange}
        onGerarMes={() => gerarMesMutation.mutate(mes)}
        isGerando={gerarMesMutation.isPending}
      />

      <MensalidadesTabela
        faturas={data?.items ?? []}
        isLoading={isLoading}
        isError={isError}
        onBaixaManual={(fat) => setFaturaParaBaixa(fat)}
        onCobrarWhatsApp={(fat) => cobrarMutation.mutate(fat.id)}
        isCobrandoId={faturaCobrandoId}
      />

      {data && data.total_pages > 1 && (
        <div className="flex items-center justify-between pt-2">
          <span className="text-sm text-slate-500">
            Página {data.page} de {data.total_pages}
          </span>
          <div className="flex items-center gap-2">
            <button
              type="button"
              onClick={() => setPagina((p) => Math.max(1, p - 1))}
              disabled={pagina <= 1 || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <ChevronLeft className="w-4 h-4" />
              <span>Página anterior</span>
            </button>
            <button
              type="button"
              onClick={() => setPagina((p) => Math.min(data.total_pages, p + 1))}
              disabled={pagina >= data.total_pages || isLoading}
              className="flex items-center gap-1 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors disabled:opacity-40 disabled:cursor-not-allowed"
            >
              <span>Próxima página</span>
              <ChevronRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}

      <BaixaManualModal
        isOpen={Boolean(faturaParaBaixa)}
        onClose={() => setFaturaParaBaixa(null)}
        fatura={faturaParaBaixa}
        onSuccess={handleSucessoBaixa}
      />
    </div>
  );
}

export default MensalidadesPage;
