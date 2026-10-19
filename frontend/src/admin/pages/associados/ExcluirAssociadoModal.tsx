import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';

export type AssociadoParaExclusao = {
  id: string;
  nome: string;
};

export type ExcluirAssociadoModalProps = {
  socio: AssociadoParaExclusao;
  onClose: () => void;
  onSuccess: () => void;
};

export function ExcluirAssociadoModal({
  socio,
  onClose,
  onSuccess,
}: ExcluirAssociadoModalProps): React.ReactElement {
  const [submetendo, setSubmetendo] = useState(false);
  const [erroApi, setErroApi] = useState<string | null>(null);

  const handleExcluir = async () => {
    setSubmetendo(true);
    setErroApi(null);
    try {
      await apiClient.delete(`/associados/${socio.id}`);
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao excluir associado.'));
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Excluir associado"
      ariaLabel="Excluir associado"
      maxWidth="max-w-md"
    >
      <div className="space-y-4">
        {erroApi && (
          <div
            role="alert"
            className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm"
          >
            {erroApi}
          </div>
        )}

        <p className="text-sm text-slate-600">
          Tem certeza de que deseja excluir o associado{' '}
          <strong className="text-slate-900">{socio.nome}</strong>? Esta ação é irreversível.
        </p>

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
            disabled={submetendo}
            onClick={handleExcluir}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {submetendo ? 'Excluindo...' : 'Confirmar exclusão'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export default ExcluirAssociadoModal;
