import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';

export type NovoAssociadoModalProps = {
  onClose: () => void;
  onSuccess: () => void;
};

export function NovoAssociadoModal({
  onClose,
  onSuccess,
}: NovoAssociadoModalProps): React.ReactElement {
  const [nome, setNome] = useState('');
  const [cpf, setCpf] = useState('');
  const [whatsapp, setWhatsapp] = useState('');
  const [email, setEmail] = useState('');
  const [diaVencimento, setDiaVencimento] = useState('10');
  const [errosLocais, setErrosLocais] = useState<Record<string, string>>({});
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [submetendo, setSubmetendo] = useState(false);

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErrosLocais({});
    setErroApi(null);

    const errs: Record<string, string> = {};
    if (!nome.trim()) errs.nome = 'Nome é obrigatório.';
    if (!cpf.trim()) errs.cpf = 'CPF é obrigatório.';
    if (!whatsapp.trim()) errs.whatsapp = 'WhatsApp é obrigatório.';
    if (!email.trim()) errs.email = 'E-mail é obrigatório.';

    if (Object.keys(errs).length > 0) {
      setErrosLocais(errs);
      return;
    }

    setSubmetendo(true);
    try {
      await apiClient.post('/associados/', {
        nome: nome.trim(),
        cpf: cpf.trim(),
        whatsapp: whatsapp.trim(),
        email: email.trim(),
        dia_vencimento: parseInt(diaVencimento, 10) || 10,
      });
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao cadastrar associado.'));
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Novo associado"
      ariaLabel="Novo associado"
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
            <label htmlFor="novo-nome" className="block text-sm font-medium text-slate-700 mb-1">
              Nome
            </label>
            <input
              id="novo-nome"
              type="text"
              value={nome}
              onChange={(e) => setNome(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
            {errosLocais.nome && <p className="mt-1 text-xs text-red-600">{errosLocais.nome}</p>}
          </div>

          <div>
            <label htmlFor="novo-cpf" className="block text-sm font-medium text-slate-700 mb-1">
              CPF
            </label>
            <input
              id="novo-cpf"
              type="text"
              value={cpf}
              onChange={(e) => setCpf(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
            {errosLocais.cpf && <p className="mt-1 text-xs text-red-600">{errosLocais.cpf}</p>}
          </div>

          <div>
            <label htmlFor="novo-whatsapp" className="block text-sm font-medium text-slate-700 mb-1">
              WhatsApp
            </label>
            <input
              id="novo-whatsapp"
              type="text"
              value={whatsapp}
              onChange={(e) => setWhatsapp(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
            {errosLocais.whatsapp && <p className="mt-1 text-xs text-red-600">{errosLocais.whatsapp}</p>}
          </div>

          <div>
            <label htmlFor="novo-email" className="block text-sm font-medium text-slate-700 mb-1">
              E-mail
            </label>
            <input
              id="novo-email"
              type="email"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900"
            />
            {errosLocais.email && <p className="mt-1 text-xs text-red-600">{errosLocais.email}</p>}
          </div>

          <div>
            <label htmlFor="novo-vencimento" className="block text-sm font-medium text-slate-700 mb-1">
              Dia de vencimento
            </label>
            <input
              id="novo-vencimento"
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

export default NovoAssociadoModal;
