import React, { useState } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { Edit2, Trash2, UserPlus } from 'lucide-react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';
import { formatCPF, formatDate } from '../../utils/format';
import { MembroFamilia, PARENTESCOS, labelParentesco } from './tipos';

const CLASSE_INPUT =
  'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900';

type MembroFamiliaModalProps = {
  associadoId: string;
  membro?: MembroFamilia;
  onClose: () => void;
  onSuccess: () => void;
};

function MembroFamiliaModal({ associadoId, membro, onClose, onSuccess }: MembroFamiliaModalProps): React.ReactElement {
  const [nome, setNome] = useState(membro?.nome ?? '');
  const [parentesco, setParentesco] = useState<string>(membro?.parentesco ?? '');
  const [cpf, setCpf] = useState(membro?.cpf ?? '');
  const [dataNascimento, setDataNascimento] = useState(membro?.data_nascimento ?? '');
  const [ativo, setAtivo] = useState(membro?.ativo ?? true);
  const [erros, setErros] = useState<Record<string, string>>({});
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const salvar = async (e: React.FormEvent) => {
    e.preventDefault();
    const encontrados: Record<string, string> = {};
    if (!nome.trim()) encontrados.nome = 'Nome é obrigatório.';
    if (!parentesco) encontrados.parentesco = 'Parentesco é obrigatório.';
    setErros(encontrados);
    if (Object.keys(encontrados).length > 0) return;

    const payload = {
      nome: nome.trim(),
      parentesco,
      cpf: cpf.trim() || null,
      data_nascimento: dataNascimento || null,
      ativo,
    };
    setEnviando(true);
    setErroApi(null);
    try {
      if (membro) {
        await apiClient.patch(`/associados/${associadoId}/familia/${membro.id}`, payload);
      } else {
        await apiClient.post(`/associados/${associadoId}/familia/`, payload);
      }
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao salvar familiar.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title={membro ? 'Editar familiar' : 'Adicionar familiar'}>
      <form onSubmit={salvar} noValidate className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}
        <div>
          <label htmlFor="familiar-nome" className="block text-sm font-medium text-slate-700 mb-1">
            Nome
          </label>
          <input id="familiar-nome" value={nome} onChange={(e) => setNome(e.target.value)} maxLength={150} className={CLASSE_INPUT} />
          {erros.nome && <p className="mt-1 text-xs text-red-600">{erros.nome}</p>}
        </div>
        <div>
          <label htmlFor="familiar-parentesco" className="block text-sm font-medium text-slate-700 mb-1">
            Parentesco
          </label>
          <select
            id="familiar-parentesco"
            value={parentesco}
            onChange={(e) => setParentesco(e.target.value)}
            className={CLASSE_INPUT}
          >
            <option value="">Selecione...</option>
            {PARENTESCOS.map((p) => (
              <option key={p.valor} value={p.valor}>
                {p.rotulo}
              </option>
            ))}
          </select>
          {erros.parentesco && <p className="mt-1 text-xs text-red-600">{erros.parentesco}</p>}
        </div>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label htmlFor="familiar-cpf" className="block text-sm font-medium text-slate-700 mb-1">
              CPF (opcional)
            </label>
            <input id="familiar-cpf" value={cpf} onChange={(e) => setCpf(e.target.value)} className={CLASSE_INPUT} />
          </div>
          <div>
            <label htmlFor="familiar-nascimento" className="block text-sm font-medium text-slate-700 mb-1">
              Data de nascimento
            </label>
            <input
              id="familiar-nascimento"
              type="date"
              value={dataNascimento}
              onChange={(e) => setDataNascimento(e.target.value)}
              className={CLASSE_INPUT}
            />
          </div>
        </div>
        {membro && (
          <label className="flex items-center gap-2 text-sm text-slate-700">
            <input type="checkbox" checked={ativo} onChange={(e) => setAtivo(e.target.checked)} />
            Acesso ativo ao clube
          </label>
        )}
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

type RemoverFamiliarModalProps = {
  associadoId: string;
  membro: MembroFamilia;
  onClose: () => void;
  onSuccess: () => void;
};

function RemoverFamiliarModal({ associadoId, membro, onClose, onSuccess }: RemoverFamiliarModalProps): React.ReactElement {
  const [erroApi, setErroApi] = useState<string | null>(null);
  const [enviando, setEnviando] = useState(false);

  const confirmar = async () => {
    setEnviando(true);
    setErroApi(null);
    try {
      await apiClient.delete(`/associados/${associadoId}/familia/${membro.id}`);
      onSuccess();
    } catch (err: unknown) {
      setErroApi(extrairMensagemErro(err, 'Erro ao remover familiar.'));
    } finally {
      setEnviando(false);
    }
  };

  return (
    <Modal isOpen={true} onClose={onClose} title="Remover familiar">
      <div className="space-y-4">
        {erroApi && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erroApi}
          </div>
        )}
        <p className="text-sm text-slate-700">
          Remover <strong className="font-semibold text-slate-900">{membro.nome}</strong> da família deste associado?
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
            {enviando ? 'Removendo...' : 'Confirmar remoção'}
          </button>
        </div>
      </div>
    </Modal>
  );
}

export function FamiliaTab({ associadoId }: { associadoId: string }): React.ReactElement {
  const queryClient = useQueryClient();
  const queryKey = ['familia', associadoId];
  const { data: familia = [], isLoading, isError } = useQuery<MembroFamilia[]>({
    queryKey,
    queryFn: async () => (await apiClient.get<MembroFamilia[]>(`/associados/${associadoId}/familia/`)).data,
  });
  const [editando, setEditando] = useState<MembroFamilia | 'novo' | null>(null);
  const [removendo, setRemovendo] = useState<MembroFamilia | null>(null);

  const recarregar = () => queryClient.invalidateQueries({ queryKey });

  return (
    <div className="space-y-4">
      <div className="flex items-center justify-between gap-4">
        <p className="text-sm text-slate-500">
          Familiares têm entrada gratuita e não consomem a franquia de convidados do titular.
        </p>
        <button
          type="button"
          onClick={() => setEditando('novo')}
          className="inline-flex items-center gap-2 px-3 py-2 rounded-lg text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 shrink-0"
        >
          <UserPlus className="w-4 h-4" />
          Adicionar familiar
        </button>
      </div>

      {isLoading ? (
        <p className="text-sm text-slate-500">Carregando...</p>
      ) : isError ? (
        <div role="alert" className="p-3 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          Não foi possível carregar a família.
        </div>
      ) : familia.length === 0 ? (
        <p className="py-8 text-center text-sm text-slate-500">Nenhum familiar cadastrado</p>
      ) : (
        <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
          <thead className="text-slate-600 font-semibold">
            <tr>
              <th scope="col" className="py-2 pr-4">Nome</th>
              <th scope="col" className="py-2 pr-4">Parentesco</th>
              <th scope="col" className="py-2 pr-4">CPF</th>
              <th scope="col" className="py-2 pr-4">Nascimento</th>
              <th scope="col" className="py-2 pr-4">Acesso</th>
              <th scope="col" className="py-2 text-right">Ações</th>
            </tr>
          </thead>
          <tbody className="divide-y divide-slate-100">
            {familia.map((membro) => (
              <tr key={membro.id}>
                <td className="py-3 pr-4 font-medium text-slate-900">{membro.nome}</td>
                <td className="py-3 pr-4 text-slate-600">{labelParentesco(membro.parentesco)}</td>
                <td className="py-3 pr-4 text-slate-600">{membro.cpf ? formatCPF(membro.cpf) : '—'}</td>
                <td className="py-3 pr-4 text-slate-600">{membro.data_nascimento ? formatDate(membro.data_nascimento) : '—'}</td>
                <td className="py-3 pr-4 text-slate-600">{membro.ativo ? 'Liberado' : 'Suspenso'}</td>
                <td className="py-3 text-right space-x-1 whitespace-nowrap">
                  <button
                    type="button"
                    onClick={() => setEditando(membro)}
                    aria-label={`Editar ${membro.nome}`}
                    className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg"
                  >
                    <Edit2 className="w-4 h-4" />
                  </button>
                  <button
                    type="button"
                    onClick={() => setRemovendo(membro)}
                    aria-label={`Remover ${membro.nome}`}
                    className="p-1.5 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg"
                  >
                    <Trash2 className="w-4 h-4" />
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      )}

      {editando && (
        <MembroFamiliaModal
          associadoId={associadoId}
          membro={editando === 'novo' ? undefined : editando}
          onClose={() => setEditando(null)}
          onSuccess={() => {
            setEditando(null);
            recarregar();
          }}
        />
      )}
      {removendo && (
        <RemoverFamiliarModal
          associadoId={associadoId}
          membro={removendo}
          onClose={() => setRemovendo(null)}
          onSuccess={() => {
            setRemovendo(null);
            recarregar();
          }}
        />
      )}
    </div>
  );
}

export default FamiliaTab;
