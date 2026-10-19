import React, { useState, useEffect, useRef } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle } from 'lucide-react';
import { apiClient } from '../api/client';
import { extrairMensagemErro } from '../api/errors';
import { ConexaoSection, WHATSAPP_STATUS_POLL_MS, WHATSAPP_QRCODE_POLL_MS } from './whatsapp/ConexaoSection';
import { TemplatesSection, TemplatesConfig } from './whatsapp/TemplatesSection';
import { ParametrosSection, ParametrosConfig } from './whatsapp/ParametrosSection';
import { DisparosSection, LogMensagemItem } from './whatsapp/DisparosSection';

export { WHATSAPP_STATUS_POLL_MS, WHATSAPP_QRCODE_POLL_MS };

export type FullConfiguracao = TemplatesConfig & ParametrosConfig;

export function normalizarConfiguracao(d: Record<string, unknown>): FullConfiguracao {
  return {
    template_d_menos_3: String(d.template_d_menos_3 || ''),
    template_d0: String(d.template_d0 || ''),
    template_recibo: String(d.template_recibo || ''),
    template_d_mais_3: String(d.template_d_mais_3 || ''),
    template_d_mais_7: String(d.template_d_mais_7 || ''),
    chave_pix: d.chave_pix !== null && d.chave_pix !== undefined ? String(d.chave_pix) : '',
    valor_mensalidade: String(d.valor_mensalidade ?? '0.00'),
    franquia_convidados: Number(d.franquia_convidados ?? 0),
    valor_convidado_extra: String(d.valor_convidado_extra ?? '0.00'),
    horario_disparo: String(d.horario_disparo || '08:00'),
    automacao_ativa: Boolean(d.automacao_ativa ?? true),
  };
}

const CONFIG_INICIAL: FullConfiguracao = {
  template_d_menos_3: '',
  template_d0: '',
  template_recibo: '',
  template_d_mais_3: '',
  template_d_mais_7: '',
  chave_pix: '',
  valor_mensalidade: '0.00',
  franquia_convidados: 0,
  valor_convidado_extra: '0.00',
  horario_disparo: '08:00',
  automacao_ativa: true,
};

export function WhatsAppConfigPage(): React.ReactElement {
  const queryClient = useQueryClient();

  // Estado do formulário de configuração
  const [formState, setFormState] = useState<FullConfiguracao>(CONFIG_INICIAL);
  const ultimoSalvoRef = useRef<FullConfiguracao | null>(null);

  // Feedbacks de salvamento
  const [mensagemSucesso, setMensagemSucesso] = useState<string | null>(null);
  const [mensagemErro, setMensagemErro] = useState<string | null>(null);

  // Filtros de Logs
  const [etapaFiltro, setEtapaFiltro] = useState<string>('');
  const [statusFiltro, setStatusFiltro] = useState<string>('');

  // Consulta Configuração
  const {
    data: configData,
    isLoading: isLoadingConfig,
    isError: isErrorConfig,
    refetch: refetchConfig,
  } = useQuery<FullConfiguracao>({
    queryKey: ['configuracao'],
    queryFn: async () => {
      const res = await apiClient.get<Record<string, unknown>>('/configuracao');
      return normalizarConfiguracao(res.data);
    },
  });

  const inicializadoRef = useRef(false);

  // Atualiza o estado na carga inicial da configuração
  useEffect(() => {
    if (configData && !inicializadoRef.current) {
      inicializadoRef.current = true;
      setFormState(configData);
      ultimoSalvoRef.current = configData;
    }
  }, [configData]);

  // Consulta Logs
  const {
    data: logsData,
    isLoading: isLoadingLogs,
    isError: isErrorLogs,
  } = useQuery<LogMensagemItem[]>({
    queryKey: ['whatsapp-logs', etapaFiltro, statusFiltro],
    queryFn: async () => {
      const params: Record<string, string> = {};
      if (etapaFiltro) params.etapa = etapaFiltro;
      if (statusFiltro) params.status = statusFiltro;
      const res = await apiClient.get<LogMensagemItem[]>('/whatsapp/logs', { params });
      return res.data;
    },
  });

  const handleTemplateChange = (campo: keyof TemplatesConfig, valor: string) => {
    setFormState((prev) => ({ ...prev, [campo]: valor }));
    setMensagemSucesso(null);
    setMensagemErro(null);
  };

  const handleParametroChange = <K extends keyof ParametrosConfig>(
    campo: K,
    valor: ParametrosConfig[K]
  ) => {
    setFormState((prev) => ({ ...prev, [campo]: valor }));
    setMensagemSucesso(null);
    setMensagemErro(null);
  };

  // Mutação: Salvar Configurações (PATCH)
  const salvarMutation = useMutation({
    mutationFn: async (diff: Record<string, unknown>) => {
      const res = await apiClient.patch<Record<string, unknown>>('/configuracao', diff);
      return res.data;
    },
    onSuccess: (data, variables) => {
      setMensagemErro(null);
      setMensagemSucesso('Configurações salvas');

      const normalizado = normalizarConfiguracao(data);

      if (ultimoSalvoRef.current) {
        ultimoSalvoRef.current = {
          ...ultimoSalvoRef.current,
          ...variables,
          ...(variables.chave_pix === null ? { chave_pix: '' } : {}),
        } as FullConfiguracao;
      } else {
        ultimoSalvoRef.current = normalizado;
      }

      queryClient.setQueryData(['configuracao'], normalizado);
    },
    onError: (err) => {
      setMensagemSucesso(null);
      const msg = extrairMensagemErro(err, 'Erro ao salvar configurações.');
      setMensagemErro(msg);
    },
  });

  const handleSalvar = () => {
    setMensagemSucesso(null);
    setMensagemErro(null);

    const base = ultimoSalvoRef.current;
    if (!base) return;

    const diff: Record<string, unknown> = {};

    // Compara campos de texto e templates
    const camposTexto: (keyof FullConfiguracao)[] = [
      'template_d_menos_3',
      'template_d0',
      'template_recibo',
      'template_d_mais_3',
      'template_d_mais_7',
      'horario_disparo',
    ];

    for (const c of camposTexto) {
      if (formState[c] !== base[c]) {
        diff[c] = formState[c];
      }
    }

    // Chave Pix: se vazia, envia como null se antes não era vazia
    if (formState.chave_pix !== base.chave_pix) {
      diff.chave_pix = formState.chave_pix.trim() ? formState.chave_pix.trim() : null;
    }

    // Valores numéricos
    if (formState.valor_mensalidade !== base.valor_mensalidade) {
      diff.valor_mensalidade = formState.valor_mensalidade;
    }
    if (formState.valor_convidado_extra !== base.valor_convidado_extra) {
      diff.valor_convidado_extra = formState.valor_convidado_extra;
    }
    if (formState.franquia_convidados !== base.franquia_convidados) {
      diff.franquia_convidados = formState.franquia_convidados;
    }
    if (formState.automacao_ativa !== base.automacao_ativa) {
      diff.automacao_ativa = formState.automacao_ativa;
    }

    if (Object.keys(diff).length === 0) {
      return;
    }

    salvarMutation.mutate(diff);
  };

  const inputsDesabilitados = isLoadingConfig || isErrorConfig || !configData;

  return (
    <div className="p-8 space-y-8 max-w-7xl mx-auto">
      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">
          WhatsApp & Configurações
        </h1>
        <p className="mt-1 text-sm text-slate-500">
          Conexão Baileys, templates da régua de cobrança, parâmetros do clube e histórico de disparos.
        </p>
      </div>

      {isErrorConfig && (
        <div
          role="alert"
          className="flex items-center justify-between gap-4 p-4 rounded-xl bg-rose-50 border border-rose-200 text-rose-800 text-sm"
        >
          <div className="flex items-center gap-2.5">
            <AlertCircle className="w-5 h-5 text-rose-600 shrink-0" />
            <span className="font-medium">Erro ao carregar configurações do WhatsApp.</span>
          </div>
          <button
            type="button"
            onClick={() => refetchConfig()}
            className="px-3 py-1.5 rounded-lg bg-rose-100 hover:bg-rose-200 text-rose-900 font-semibold text-xs transition-colors"
          >
            Tentar novamente
          </button>
        </div>
      )}

      {configData && (!formState.chave_pix || formState.chave_pix.trim() === '') && formState.automacao_ativa && (
        <div
          role="alert"
          className="flex items-center gap-2.5 p-4 rounded-xl bg-amber-50 border border-amber-200 text-amber-900 text-sm"
        >
          <AlertCircle className="w-5 h-5 text-amber-600 shrink-0" />
          <span className="font-medium">
            Chave Pix não configurada — as cobranças sairão sem chave
          </span>
        </div>
      )}

      <ConexaoSection />

      <TemplatesSection
        values={{
          template_d_menos_3: formState.template_d_menos_3,
          template_d0: formState.template_d0,
          template_recibo: formState.template_recibo,
          template_d_mais_3: formState.template_d_mais_3,
          template_d_mais_7: formState.template_d_mais_7,
          chave_pix: formState.chave_pix,
        }}
        onChange={handleTemplateChange}
        disabled={inputsDesabilitados}
      />

      <ParametrosSection
        values={{
          valor_mensalidade: formState.valor_mensalidade,
          franquia_convidados: formState.franquia_convidados,
          valor_convidado_extra: formState.valor_convidado_extra,
          horario_disparo: formState.horario_disparo,
          automacao_ativa: formState.automacao_ativa,
        }}
        onChange={handleParametroChange}
        onSalvar={handleSalvar}
        isSalvando={salvarMutation.isPending}
        disabled={inputsDesabilitados}
        mensagemSucesso={mensagemSucesso}
        mensagemErro={mensagemErro}
      />

      <DisparosSection
        logs={logsData ?? []}
        isLoading={isLoadingLogs}
        isError={isErrorLogs}
        etapaFiltro={etapaFiltro}
        onEtapaFiltroChange={setEtapaFiltro}
        statusFiltro={statusFiltro}
        onStatusFiltroChange={setStatusFiltro}
      />
    </div>
  );
}

export default WhatsAppConfigPage;
