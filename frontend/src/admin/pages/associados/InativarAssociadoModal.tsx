import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';
import { Associado, InativacaoResposta } from './tipos';

export type InativarAssociadoModalProps = {
  associado: Associado;
  onClose: () => void;
  onSuccess: (resposta: InativacaoResposta) => void;
};

export function InativarAssociadoModal({
  associado,
  onClose,
  onSuccess,
}: InativarAssociadoModalProps): React.ReactElement {
  const [motivo, setMotivo] = useState('');
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const confirmar = async () => {
    setEnviando(true);
    setErroApi(null);
    try {
      const { data } = await apiClient.post<InativacaoResposta>(`/associados/${associado.id}/inativar`, {
        motivo: motivo.trim() || null,
      });
      onSuccess(data);
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao inativar associado.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title="Inativar associado" maxWidth="max-w-lg">
      <div className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}

        <p className="text-sm text-slate-700">
          <strong className="font-semibold text-slate-900">{associado.nome}</strong> deixará de ser cobrado e
          perderá o acesso ao clube. O cadastro e todo o histórico (faturas, convites e mensagens) são mantidos, e
          o sócio pode ser reativado depois.
        </p>
        <ul className="text-sm text-slate-600 list-disc pl-5 space-y-1">
          <li>Faturas pendentes que ainda não venceram serão canceladas.</li>
          <li>Faturas já vencidas continuam em aberto como dívida.</li>
          <li>Convites e reservas de quadra futuros serão cancelados.</li>
        </ul>

        <div>
          <label htmlFor="inativar-motivo" className="block text-sm font-medium text-slate-700 mb-1">
            Motivo (opcional)
          </label>
          <textarea
            id="inativar-motivo"
            rows={2}
            maxLength={255}
            value={motivo}
            onChange={(e) => setMotivo(e.target.value)}
            className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
          />
        </div>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Cancelar
          </button>
          <button
            type="button"
            onClick={confirmar}
            disabled={enviando}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {enviando ? 'Inativando...' : 'Confirmar inativação'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default InativarAssociadoModal;
