import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';
import { formatCPF } from '../../utils/format';

export type AssociadoCompleto = {
  id: string;
  nome: string;
  cpf: string;
  whatsapp: string;
  email: string;
  dia_vencimento: number;
};

export type EditarAssociadoModalProps = {
  socio: AssociadoCompleto;
  onClose: () => void;
  onSuccess: () => void;
};

export function EditarAssociadoModal({
  socio,
  onClose,
  onSuccess,
}: EditarAssociadoModalProps): React.ReactElement {
  const [nome, setNome] = useState(socio.nome);
  const [whatsapp, setWhatsapp] = useState(socio.whatsapp);
  const [email, setEmail] = useState(socio.email);
  const [diaVencimento, setDiaVencimento] = useState(String(socio.dia_vencimento));
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [submetendo, setSubmetendo] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErroApi(null);
    setSubmetendo(true);

    try {
      // PATCH sem o CPF!
      await apiClient.patch(`/associados/${socio.id}`, {
        nome: nome.trim(),
        whatsapp: whatsapp.trim(),
        email: email.trim(),
        dia_vencimento: parseInt(diaVencimento, 10) || socio.dia_vencimento,
      });
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao editar associado.'));
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Editar associado"
      ariaLabel="Editar associado"
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
            <label htmlFor="edit-nome" className="block text-sm font-medium text-slate-700 mb-1">
              Nome
            </label>
            <input
              id="edit-nome"
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
          </div>

          <div>
            <label htmlFor="edit-cpf" className="block text-sm font-medium text-slate-500 mb-1">
              CPF
            </label>
            <input
              id="edit-cpf"
              type="text"
              disabled
              value={formatCPF(socio.cpf)}
              className="w-full px-3 py-2 border border-slate-200 rounded-lg text-sm text-slate-500 bg-slate-50 cursor-not-allowed"
            />
          </div>

          <div>
            <label htmlFor="edit-whatsapp" className="block text-sm font-medium text-slate-700 mb-1">
              WhatsApp
            </label>
            <input
              id="edit-whatsapp"
              type="text"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
          </div>

          <div>
            <label htmlFor="edit-email" className="block text-sm font-medium text-slate-700 mb-1">
              E-mail
            </label>
            <input
              id="edit-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
          </div>

          <div>
            <label htmlFor="edit-vencimento" className="block text-sm font-medium text-slate-700 mb-1">
              Dia de vencimento
            </label>
            <input
              id="edit-vencimento"
              type="number"
              min="1"
              max="31"
              value={diaVencimento}
              onChange={(e) => setDiaVencimento(e.target.value)}
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
              {submetendo ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </Modal>
  );
}

export default EditarAssociadoModal;
