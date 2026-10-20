import React, { useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { useQueryClient } from '@tanstack/react-query';
import { ArrowLeft } from 'lucide-react';
import { apiClient } from '../api/client';
import { extrairMensagemErro } from '../api/errors';
import { FormularioAssociado } from './associados/FormularioAssociado';
import { Associado } from './associados/tipos';

export function NovoAssociadoPage(): React.ReactElement {
  const navigate = useNavigate();
  const queryClient = useQueryClient();
  const [enviando, setEnviando] = useState(false);
  const [erroApi, setErroApi] = useState<string | null>(null);

  const cadastrar = async (payload: Record<string, unknown>) => {
    setEnviando(true);
    setErroApi(null);
    try {
      const { data } = await apiClient.post<Associado>('/associados/', payload);
      queryClient.invalidateQueries({ queryKey: ['associados'] });
      navigate(`/admin/associados/${data.id}`);
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao cadastrar associado.'));
      window.scrollTo({ top: 0, behavior: 'smooth' });
    } finally {
      setEnviando(false);
    }
  };

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <Link
        to="/admin/associados"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar para associados
      </Link>

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-slate-900">Novo associado</h1>
        <p className="mt-1 text-sm text-slate-500">
          Preencha nome, CPF, WhatsApp e e-mail. Os demais dados podem ser completados depois na ficha do sócio.
        </p>
      </div>

      <FormularioAssociado
        rotuloEnviar="Cadastrar associado"
        enviando={enviando}
        erroApi={erroApi}
        onEnviar={cadastrar}
        acaoSecundaria={
          <Link
            to="/admin/associados"
            className="px-4 py-2.5 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50 transition-colors"
          >
            Cancelar
          </Link>
        }
      />
    </div>
  );
}

export default NovoAssociadoPage;
