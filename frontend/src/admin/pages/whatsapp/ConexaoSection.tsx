import React, { useState } from 'react';
import { useQuery, useMutation, useQueryClient } from '@tanstack/react-query';
import { AlertCircle, CheckCircle2, RefreshCw, Send, Unplug } from 'lucide-react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';
import { labelWhatsAppStatus } from '../../utils/format';

export const WHATSAPP_STATUS_POLL_MS = 5000;
export const WHATSAPP_QRCODE_POLL_MS = 2000;

export function ConexaoSection(): React.ReactElement {
  const queryClient = useQueryClient();

  // Modal desconectar
  const [modalDesconectarAberto, setModalDesconectarAberto] = useState(false);

  // Formulário teste envio
  const [numeroTeste, setNumeroTeste] = useState('');
  const [mensagemTeste, setMensagemTeste] = useState('');
  const [erroTeste, setErroTeste] = useState<string | null>(null);
  const [sucessoTeste, setSucessoTeste] = useState<string | null>(null);

  // Erro geral conexão
  const [erroConexao, setErroConexao] = useState<string | null>(null);

  // Polling de Status
  const { data: statusData } = useQuery<{ status: string }>({
    queryKey: ['whatsapp-status-page'],
    queryFn: async () => {
      const res = await apiClient.get<{ status: string }>('/whatsapp/status');
      return res.data;
    },
    refetchInterval: WHATSAPP_STATUS_POLL_MS,
  });

  const currentStatus = statusData?.status ?? 'DESCONECTADO';

  // Polling de QR Code (somente enquanto AGUARDANDO_QRCODE)
  const { data: qrcodeData } = useQuery<{ status: string; qrcode: string | null }>({
    queryKey: ['whatsapp-qrcode-page'],
    queryFn: async () => {
      const res = await apiClient.get<{ status: string; qrcode: string | null }>('/whatsapp/qrcode');
      return res.data;
    },
    enabled: currentStatus === 'AGUARDANDO_QRCODE',
    refetchInterval: WHATSAPP_QRCODE_POLL_MS,
  });

  // Mutação: Desconectar
  const desconectarMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/whatsapp/desconectar');
      return res.data;
    },
    onSuccess: () => {
      setModalDesconectarAberto(false);
      setErroConexao(null);
      queryClient.invalidateQueries({ queryKey: ['whatsapp-status-page'] });
      queryClient.invalidateQueries({ queryKey: ['whatsapp-status'] });
    },
    onError: (err) => {
      setErroConexao(extrairMensagemErro(err, 'Erro ao desconectar WhatsApp.'));
    },
  });

  // Mutação: Reiniciar
  const reiniciarMutation = useMutation({
    mutationFn: async () => {
      const res = await apiClient.post('/whatsapp/reiniciar');
      return res.data;
    },
    onSuccess: () => {
      setErroConexao(null);
      queryClient.invalidateQueries({ queryKey: ['whatsapp-status-page'] });
      queryClient.invalidateQueries({ queryKey: ['whatsapp-status'] });
      queryClient.invalidateQueries({ queryKey: ['whatsapp-qrcode-page'] });
    },
    onError: (err) => {
      setErroConexao(extrairMensagemErro(err, 'Falha ao reiniciar WhatsApp.'));
    },
  });

  // Mutação: Teste de envio
  const testeEnvioMutation = useMutation({
    mutationFn: async (payload: { numero: string; mensagem?: string | null }) => {
      const res = await apiClient.post('/whatsapp/teste-envio', payload);
      return res.data;
    },
    onSuccess: () => {
      setErroTeste(null);
      setSucessoTeste('Mensagem de teste enviada');
      queryClient.invalidateQueries({ queryKey: ['whatsapp-logs'] });
    },
    onError: (err) => {
      setSucessoTeste(null);
      setErroTeste(extrairMensagemErro(err, 'Erro ao enviar mensagem de teste.'));
    },
  });

  const handleEnviarTeste = (e: React.FormEvent) => {
    e.preventDefault();
    setSucessoTeste(null);
    setErroTeste(null);

    const numLimpo = numeroTeste.trim();
    if (!numLimpo) {
      setErroTeste('Informe o número');
      return;
    }

    testeEnvioMutation.mutate({
      numero: numLimpo,
      mensagem: mensagemTeste.trim() ? mensagemTeste.trim() : null,
    });
  };

  return (
    <section aria-labelledby="sec-conexao" role="region" className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-4 border-b border-slate-100">
        <div>
          <h2 id="sec-conexao" className="text-lg font-bold text-slate-900">
            Conexão
          </h2>
          <p className="text-sm text-slate-500">
            Gerencie o pareamento com o WhatsApp via QR Code e verifique o estado do motor Baileys.
          </p>
        </div>

        <div className="flex items-center gap-3">
          <div className="flex items-center gap-2 px-3 py-1.5 bg-slate-50 border border-slate-200 rounded-lg text-sm">
            <span
              className={`w-2.5 h-2.5 rounded-full shrink-0 ${
                currentStatus === 'CONECTADO'
                  ? 'bg-emerald-500'
                  : currentStatus === 'AGUARDANDO_QRCODE'
                  ? 'bg-amber-500 animate-pulse'
                  : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-600 font-medium">Status:</span>
            <span data-testid="whatsapp-connection-status" className="font-semibold text-slate-900">
              {labelWhatsAppStatus(currentStatus)}
            </span>
          </div>

          <button
            type="button"
            onClick={() => reiniciarMutation.mutate()}
            disabled={reiniciarMutation.isPending}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors disabled:opacity-50"
          >
            <RefreshCw className={`w-3.5 h-3.5 ${reiniciarMutation.isPending ? 'animate-spin' : ''}`} />
            <span>Reiniciar conexão</span>
          </button>

          <button
            type="button"
            onClick={() => setModalDesconectarAberto(true)}
            className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-rose-200 text-rose-700 bg-rose-50 hover:bg-rose-100 transition-colors"
          >
            <Unplug className="w-3.5 h-3.5" />
            <span>Desconectar</span>
          </button>
        </div>
      </div>

      {erroConexao && (
        <div role="alert" className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-sm flex items-center gap-2">
          <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
          <span className="flex-1 font-medium">{erroConexao}</span>
        </div>
      )}

      {currentStatus === 'AGUARDANDO_QRCODE' && qrcodeData?.qrcode && (
        <div className="flex flex-col items-center justify-center p-6 bg-slate-50 border border-slate-200 rounded-xl space-y-3">
          <p className="text-sm font-semibold text-slate-800">
            Escaneie o QR Code abaixo com o aplicativo do WhatsApp no celular:
          </p>
          <div className="p-3 bg-white border border-slate-200 rounded-xl shadow-sm">
            <img
              alt="QR Code do WhatsApp"
              src={qrcodeData.qrcode}
              className="w-56 h-56 object-contain"
            />
          </div>
          <p className="text-xs text-slate-500">
            O código é atualizado automaticamente a cada 2 segundos.
          </p>
        </div>
      )}

      {/* Teste de Envio */}
      <div className="pt-2 border-t border-slate-100">
        <h3 className="text-sm font-semibold text-slate-900 mb-3">Teste de envio individual</h3>
        
        {sucessoTeste && (
          <div className="mb-3 p-3 bg-emerald-50 border border-emerald-200 rounded-lg text-emerald-800 text-sm flex items-center gap-2">
            <CheckCircle2 className="w-4 h-4 text-emerald-600 shrink-0" />
            <span className="flex-1 font-medium">{sucessoTeste}</span>
          </div>
        )}

        {erroTeste && (
          <div role="alert" className="mb-3 p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-sm flex items-center gap-2">
            <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
            <span className="flex-1 font-medium">{erroTeste}</span>
          </div>
        )}

        <form onSubmit={handleEnviarTeste} className="grid grid-cols-1 sm:grid-cols-12 gap-3 items-end">
          <div className="sm:col-span-4 flex flex-col gap-1">
            <label htmlFor="teste-numero" className="text-xs font-semibold text-slate-700">
              Número
            </label>
            <input
              id="teste-numero"
              type="text"
              value={numeroTeste}
              onChange={(e) => setNumeroTeste(e.target.value)}
              placeholder="Ex: 75999998888"
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
            />
          </div>

          <div className="sm:col-span-5 flex flex-col gap-1">
            <label htmlFor="teste-mensagem" className="text-xs font-semibold text-slate-700">
              Mensagem (opcional)
            </label>
            <input
              id="teste-mensagem"
              type="text"
              value={mensagemTeste}
              onChange={(e) => setMensagemTeste(e.target.value)}
              placeholder="Mensagem customizada..."
              className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors"
            />
          </div>

          <div className="sm:col-span-3">
            <button
              type="submit"
              disabled={testeEnvioMutation.isPending}
              className="w-full flex items-center justify-center gap-2 px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white text-sm font-medium rounded-lg shadow-sm transition-colors disabled:opacity-50"
            >
              <Send className="w-4 h-4" />
              <span>{testeEnvioMutation.isPending ? 'Enviando...' : 'Enviar teste'}</span>
            </button>
          </div>
        </form>
      </div>

      <Modal
        isOpen={modalDesconectarAberto}
        onClose={() => setModalDesconectarAberto(false)}
        title="Desconectar WhatsApp"
        maxWidth="max-w-sm"
      >
        <div className="space-y-4">
          <p className="text-sm text-slate-600">
            Tem certeza de que deseja desconectar o WhatsApp? Os disparos automáticos e mensagens ficarão suspensos até que um novo pareamento seja realizado.
          </p>

          <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
            <button
              type="button"
              onClick={() => setModalDesconectarAberto(false)}
              className="px-3 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
            >
              Cancelar
            </button>
            <button
              type="button"
              onClick={() => desconectarMutation.mutate()}
              disabled={desconectarMutation.isPending}
              className="px-3 py-2 text-sm font-medium text-white bg-rose-600 hover:bg-rose-700 rounded-lg transition-colors disabled:opacity-50"
            >
              {desconectarMutation.isPending ? 'Desconectando...' : 'Confirmar desconexão'}
            </button>
          </div>
        </div>
      </Modal>
    </section>
  );
}

export default ConexaoSection;
