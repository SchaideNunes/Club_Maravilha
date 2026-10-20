import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Edit2, Plus, Trash2 } from 'lucide-react';
import { apiClient } from '../api/client';
import { extrairMensagemErro } from '../api/errors';
import { Modal } from '../components/Modal';
import { formatBRL, valorParaApi, valorParaCampo } from '../utils/format';
import { Plano } from './associados/tipos';

const CLASSE_INPUT =
  'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900';

type PlanoModalProps = {
  plano?: Plano;
  onClose: () => void;
  onSuccess: () => void;
};

function PlanoModal({ plano, onClose, onSuccess }: PlanoModalProps): React.ReactElement {
  const [nome, setNome] = useState(plano?.nome ?? '');
  const [descricao, setDescricao] = useState(plano?.descricao ?? '');
  const [valor, setValor] = useState(plano ? valorParaCampo(plano.valor_mensalidade) : '');
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    const encontrados: Record<string, string> = {};
    if (!nome.trim()) encontrados.nome = 'Nome é obrigatório.';
    const valorApi = valorParaApi(valor);
    if (!valor.trim()) encontrados.valor = 'Valor da mensalidade é obrigatório.';
    else if (valorApi === null) encontrados.valor = 'Informe um valor válido (ex: 150,00).';
    setErros(encontrados);
    if (Object.keys(encontrados).length > 0) return;

    const payload = { nome: nome.trim(), descricao: descricao.trim() || null, valor_mensalidade: valorApi };
    setEnviando(true);
    setErroApi(null);
    try {
      if (plano) await apiClient.patch(`/planos/${plano.id}`, payload);
      else await apiClient.post('/planos/', payload);
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao salvar o plano.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title={plano ? 'Editar plano' : 'Novo plano'}>
      <form onSubmit={salvar} noValidate className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}
        <div>
          <label htmlFor="plano-nome" className="block text-sm font-medium text-slate-700 mb-1">
            Nome
          </label>
          <input id="plano-nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={80} className={CLASSE_INPUT} />
          {erros.nome && <p className="mt-1 text-xs text-red-600">{erros.nome}</p>}
        </div>
        <div>
          <label htmlFor="plano-descricao" className="block text-sm font-medium text-slate-700 mb-1">
            Descrição
          </label>
          <textarea
            id="plano-descricao"
            rows={2}
            maxLength={500}
            value={descricao}
            onChange={(e) => setDescricao(e.target.value)}
            className={CLASSE_INPUT}
          />
        </div>
        <div>
          <label htmlFor="plano-valor" className="block text-sm font-medium text-slate-700 mb-1">
            Valor da mensalidade
          </label>
          <input
            id="plano-valor"
            inputMode="decimal"
            placeholder="0,00"
            value={valor}
            onChange={(e) => setValor(e.target.value)}
            aria-describedby="plano-valor-ajuda"
            className={CLASSE_INPUT}
          />
          <p id="plano-valor-ajuda" className="mt-1 text-xs text-slate-500">
            Use 0 para sócios isentos (remidos, beneméritos).
          </p>
          {erros.valor && <p className="mt-1 text-xs text-red-600">{erros.valor}</p>}
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
            disabled={enviando}
            className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
          >
            {enviando ? 'Salvando...' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

function ExcluirPlanoModal({ plano, onClose, onSuccess }: { plano: Plano; onClose: () => void; onSuccess: () => void }) {
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const confirmar = async () => {
    setEnviando(true);
    setErroApi(null);
    try {
      await apiClient.delete(`/planos/${plano.id}`);
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao excluir o plano.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title="Excluir plano">
      <div className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}
        <p className="text-sm text-slate-700">
          Excluir o plano <strong className="font-semibold text-slate-900">{plano.nome}</strong>? Só é possível excluir
          planos que nunca tiveram sócios; os demais podem ser desativados.
        </p>
        <div className="flex justify-end gap-2">
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
            {enviando ? 'Excluindo...' : 'Confirmar exclusão'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export function PlanosPage(): React.ReactElement {
  const queryClient = useQueryClient();
  const { data: planos = [], isLoading, isError } = useQuery<Plano[]>({
    queryKey: ['planos', 'todos'],
    queryFn: async () => (await apiClient.get<Plano[]>('/planos/')).data,
  });
  const { data: mensalidadePadrao } = useQuery<string>({
    queryKey: ['mensalidade-padrao'],
    queryFn: async () =>
      String((await apiClient.get<{ valor_mensalidade: string }>('/configuracao')).data.valor_mensalidade),
  });

  const [editando, setEditando] = useState<Plano | 'novo' | null>(null);
  const [excluindo, setExcluindo] = useState<Plano | null>(null);
  const [erroAcao, setErroAcao] = useState<string | null>(null);

  const recarregar = () => queryClient.invalidateQueries({ queryKey: ['planos'] });

  const alternarAtivo = async (plano: Plano) => {
    setErroAcao(null);
    try {
      await apiClient.patch(`/planos/${plano.id}`, { ativo: !plano.ativo });
      recarregar();
    } catch (err: unknown) {
      setErroAcao(extrairMensagemErro(err, 'Erro ao atualizar o plano.'));
    }
  };

  return (
    <div className="p-8 space-y-6">
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">Planos</h1>
          <p className="mt-1 text-sm text-slate-500">
            {mensalidadePadrao
              ? `Sócios sem plano pagam a mensalidade padrão de ${formatBRL(mensalidadePadrao)}, definida em WhatsApp & Configurações.`
              : 'Categorias de mensalidade dos sócios.'}
          </p>
        </div>
        <button
          type="button"
          onClick={() => setEditando('novo')}
          className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 shadow-sm"
        >
          <Plus className="w-4 h-4" />
          Novo plano
        </button>
      </div>

      {erroAcao && (
        <div role="alert" className="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          {erroAcao}
        </div>
      )}

      {isLoading ? (
        <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">Carregando...</div>
      ) : isError ? (
        <div role="alert" className="p-4 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          Não foi possível carregar os planos. Tente novamente mais tarde.
        </div>
      ) : planos.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
          Nenhum plano cadastrado
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-x-auto">
          <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
            <thead className="bg-slate-50 text-slate-600 font-semibold">
              <tr>
                <th scope="col" className="px-6 py-3.5">Nome</th>
                <th scope="col" className="px-6 py-3.5">Descrição</th>
                <th scope="col" className="px-6 py-3.5">Mensalidade</th>
                <th scope="col" className="px-6 py-3.5">Sócios</th>
                <th scope="col" className="px-6 py-3.5">Situação</th>
                <th scope="col" className="px-6 py-3.5 text-right">Ações</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-200">
              {planos.map((plano) => (
                <tr key={plano.id} className={plano.ativo ? '' : 'bg-slate-50/60'}>
                  <td className="px-6 py-4 font-medium text-slate-900 whitespace-nowrap">{plano.nome}</td>
                  <td className="px-6 py-4 text-slate-600">{plano.descricao || '—'}</td>
                  <td className="px-6 py-4 text-slate-900 whitespace-nowrap">
                    {parseFloat(plano.valor_mensalidade) === 0 ? 'Isento' : formatBRL(plano.valor_mensalidade)}
                  </td>
                  <td className="px-6 py-4 text-slate-600">{plano.total_associados}</td>
                  <td className="px-6 py-4">
                    <span
                      className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                        plano.ativo
                          ? 'bg-emerald-50 text-emerald-700 border-emerald-200'
                          : 'bg-slate-100 text-slate-600 border-slate-300'
                      }`}
                    >
                      {plano.ativo ? 'Ativo' : 'Desativado'}
                    </span>
                  </td>
                  <td className="px-6 py-4 text-right whitespace-nowrap space-x-1">
                    <button
                      type="button"
                      onClick={() => alternarAtivo(plano)}
                      aria-label={`${plano.ativo ? 'Desativar' : 'Ativar'} ${plano.nome}`}
                      className="px-2.5 py-1.5 rounded-lg text-xs font-medium text-slate-700 hover:bg-slate-100"
                    >
                      {plano.ativo ? 'Desativar' : 'Ativar'}
                    </button>
                    <button
                      type="button"
                      onClick={() => setEditando(plano)}
                      aria-label={`Editar ${plano.nome}`}
                      className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                    >
                      <Edit2 className="w-4 h-4" />
                    </button>
                    <button
                      type="button"
                      onClick={() => setExcluindo(plano)}
                      aria-label={`Excluir ${plano.nome}`}
                      className="p-1.5 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg"
                    >
                      <Trash2 className="w-4 h-4" />
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {editando && (
        <PlanoModal
          plano={editando === 'novo' ? undefined : editando}
          onClose={() => setEditando(null)}
          onSuccess={() => {
            setEditando(null);
            recarregar();
          }}
        />
      )}
      {excluindo && (
        <ExcluirPlanoModal
          plano={excluindo}
          onClose={() => setExcluindo(null)}
          onSuccess={() => {
            setExcluindo(null);
            recarregar();
          }}
        />
      )}
    </div>
  );
}

export default PlanosPage;
