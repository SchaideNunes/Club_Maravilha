import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';

export type AssociadoResumo = {
  id: string;
  nome: string;
  cpf: string;
};

export type ConvidadoModalProps = {
  socio: AssociadoResumo;
  onClose: () => void;
  onSuccess: (resp: {
    is_gratuito: boolean;
    tipo: string;
    valor_taxa_extra: string;
    aviso: string | null;
  }) => void;
};

function dataHojeNoClube(): string {
  const agora = new Date();
  const ano = agora.getFullYear();
  const mes = String(agora.getMonth() + 1).padStart(2, '0');
  const dia = String(agora.getDate()).padStart(2, '0');
  return `${ano}-${mes}-${dia}`;
}

export function ConvidadoModal({
  socio,
  onClose,
  onSuccess,
}: ConvidadoModalProps): React.ReactElement {
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [dataVisita, setDataVisita] = useState(dataHojeNoClube());
  const [erroNome, setErroNome] = useState<string | null>(null);
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [submetendo, setSubmetendo] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErroNome(null);
    setErroApi(null);

    if (!nome.trim()) {
      setErroNome('Informe o nome do convidado.');
      return;
    }

    setSubmetendo(true);
    try {
      const payload: { nome: string; data_visita: string; cpf?: string | null } = {
        nome: nome.trim(),
        data_visita: dataVisita,
        cpf: cpf.trim() ? cpf.trim() : null,
      };
      const res = await apiClient.post(`/associados/${socio.id}/convidados`, payload);
      onSuccess(res.data);
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Não foi possível emitir o convite.'));
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Adicionar convidado"
      ariaLabel="Adicionar convidado"
      maxWidth="max-w-md"
    >
      <div className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}

        <form onSubmit={handleSubmit} className="space-y-4">
          <div>
            <label htmlFor="convidado-nome" className="block text-sm font-medium text-slate-700 mb-1">
              Nome do convidado
            </label>
            <input
              id="convidado-nome"
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
            {erroNome && <p className="mt-1 text-xs text-red-600">{erroNome}</p>}
          </div>

          <div>
            <label htmlFor="convidado-cpf" className="block text-sm font-medium text-slate-700 mb-1">
              CPF (opcional)
            </label>
            <input
              id="convidado-cpf"
              type="text"
              value={cpf}
              onChange={(e) => setCpf(e.target.value)}
              placeholder="000.000.000-00"
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
          </div>

          <div>
            <label htmlFor="convidado-data" className="block text-sm font-medium text-slate-700 mb-1">
              Data da visita
            </label>
            <input
              id="convidado-data"
              type="date"
              value={dataVisita}
              onChange={(e) => setDataVisita(e.target.value)}
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
              type="submit"
              disabled={submetendo}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
            >
              {submetendo ? 'Emitindo...' : 'Emitir convite'}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

export default ConvidadoModal;
