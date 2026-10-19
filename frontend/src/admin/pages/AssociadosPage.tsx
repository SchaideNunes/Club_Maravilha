import React, { useState, useEffect } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import {
  Search,
  UserPlus,
  Upload,
  Edit2,
  Trash2,
  X,
  AlertCircle,
  CheckCircle,
} from 'lucide-react';
import { apiClient } from '../api/client';
import { useDebouncedValue } from '../hooks/useDebouncedValue';
import {
  formatCPF,
  formatWhatsApp,
  formatBRL,
  labelSituacao,
} from '../utils/format';
import { ConvidadoModal } from './associados/ConvidadoModal';
import { NovoAssociadoModal } from './associados/NovoAssociadoModal';
import { EditarAssociadoModal } from './associados/EditarAssociadoModal';
import { ExcluirAssociadoModal } from './associados/ExcluirAssociadoModal';
import { ImportarPlanilhaModal } from './associados/ImportarPlanilhaModal';

export type Associado = {
  id: string;
  nome: string;
  cpf: string;
  whatsapp: string;
  email: string;
  dia_vencimento: number;
  convidados_usados_mes: number;
  franquia_convidados: number;
  situacao_financeira: string;
};

export type ListaAssociadosPaginada = {
  items: Associado[];
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
};

export type RelatorioImportacao = {
  total_lidos: number;
  total_importados: number;
  total_atualizados: number;
  total_ignorados_duplicados: number;
  erros: Array<{ linha: number; campo?: string; motivo: string }>;
};

export function AssociadosPage(): React.ReactElement {
  const queryClient = useQueryClient();

  // Estados de busca, filtro e paginação
  const [buscaInput, setBuscaInput] = useState('');
  const buscaDebounced = useDebouncedValue(buscaInput, 350);
  const [situacaoFiltro, setSituacaoFiltro] = useState('');
  const [pagina, setPagina] = useState(1);

  const handleBuscaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setBuscaInput(e.target.value);
    setPagina(1);
  };

  // Modais
  const [modalConvidadoSocio, setModalConvidadoSocio] = useState<Associado | null>(null);
  const [modalNovoAberto, setModalNovoAberto] = useState(false);
  const [modalEditarSocio, setModalEditarSocio] = useState<Associado | null>(null);
  const [modalExcluirSocio, setModalExcluirSocio] = useState<Associado | null>(null);
  const [modalImportarAberto, setModalImportarAberto] = useState(false);

  // Alerta geral fora dos modais (ex: aviso de convite)
  const [alertaGlobal, setAlertaGlobal] = useState<{
    tipo: 'sucesso' | 'aviso';
    mensagem: string;
    taxa?: string;
  } | null>(null);

  // Query dos associados
  const { data, isLoading, isError } = useQuery<ListaAssociadosPaginada>({
    queryKey: ['associados', buscaDebounced, situacaoFiltro, pagina],
    queryFn: async () => {
      const params: Record<string, string | number> = { page: pagina };
      if (buscaDebounced.trim()) params.q = buscaDebounced.trim();
      if (situacaoFiltro) params.situacao = situacaoFiltro;
      const res = await apiClient.get<ListaAssociadosPaginada>('/associados/', { params });
      return res.data;
    },
  });

  const totalPages = data?.total_pages || 1;
  const associados = data?.items || [];

  // Clamp da página caso itens sejam excluídos e a página atual exceda o total
  useEffect(() => {
    if (data && data.total_pages > 0 && pagina > data.total_pages) {
      setPagina(data.total_pages);
    }
  }, [data, pagina]);

  return (
    <div className="p-8 space-y-6">
      {/* Cabeçalho */}
      <div className="flex flex-col sm:flex-row sm:items-center sm:justify-between gap-4">
        <div>
          <h1 className="text-2xl font-bold tracking-tight text-slate-900">
            Associados
          </h1>
          <p className="mt-1 text-sm text-slate-500">
            Gestão de membros, convidados e importação de cadastros
          </p>
        </div>
        <div className="flex items-center gap-3">
          <button
            onClick={() => setModalImportarAberto(true)}
            type="button"
            className="inline-flex items-center gap-2 px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition duration-150 ease-out"
          >
            <Upload className="w-4 h-4 text-slate-500" />
            <span>Importar planilha</span>
          </button>
          <button
            onClick={() => setModalNovoAberto(true)}
            type="button"
            className="inline-flex items-center gap-2 px-4 py-2 border border-transparent rounded-lg text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 shadow-sm transition duration-150 ease-out"
          >
            <UserPlus className="w-4 h-4" />
            <span>Novo associado</span>
          </button>
        </div>
      </div>

      {/* Alerta global (após emitir convite, etc) */}
      {alertaGlobal && (
        <div
          role={alertaGlobal.tipo === 'aviso' ? 'alert' : undefined}
          className={`p-4 rounded-lg text-sm flex items-start gap-3 border ${
            alertaGlobal.tipo === 'aviso'
              ? 'bg-amber-50 text-amber-800 border-amber-200'
              : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}
        >
          {alertaGlobal.tipo === 'aviso' ? (
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <div className="flex-1">
            <p className="font-medium">{alertaGlobal.mensagem}</p>
            {alertaGlobal.taxa && (
              <p className="mt-1 font-semibold">{alertaGlobal.taxa}</p>
            )}
          </div>
          <button
            onClick={() => setAlertaGlobal(null)}
            className="text-slate-400 hover:text-slate-600"
          >
            <X className="w-4 h-4" />
          </button>
        </div>
      )}

      {/* Barra de Filtros e Busca */}
      <div className="flex flex-col sm:flex-row items-center gap-4 bg-white p-4 rounded-xl border border-slate-200 shadow-sm">
        <div className="relative flex-1 w-full">
          <label htmlFor="busca-associados" className="sr-only">
            Buscar por nome ou CPF
          </label>
          <div className="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none text-slate-400">
            <Search className="w-4 h-4" />
          </div>
          <input
            id="busca-associados"
            aria-label="Buscar por nome ou CPF"
            type="text"
            placeholder="Buscar por nome ou CPF..."
            value={buscaInput}
            onChange={handleBuscaChange}
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900 transition duration-150 ease-out"
          />
        </div>

        <div className="flex items-center gap-2 w-full sm:w-auto">
          <label
            htmlFor="filtro-situacao"
            className="text-sm font-medium text-slate-700 whitespace-nowrap"
          >
            Situação
          </label>
          <select
            id="filtro-situacao"
            aria-label="Situação"
            value={situacaoFiltro}
            onChange={(e) => {
              setSituacaoFiltro(e.target.value);
              setPagina(1);
            }}
            className="w-full sm:w-40 px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900 transition duration-150 ease-out"
          >
            <option value="">Todas</option>
            <option value="EM_DIA">Em dia</option>
            <option value="PENDENTE">Pendente</option>
            <option value="ATRASADO">Atrasado</option>
          </select>
        </div>
      </div>

      {/* Conteúdo da Tabela / Estados */}
      {isLoading ? (
        <div className="bg-white p-8 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
          Carregando...
        </div>
      ) : isError ? (
        <div
          role="alert"
          className="p-4 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm"
        >
          Não foi possível carregar os associados. Tente novamente mais tarde.
        </div>
      ) : associados.length === 0 ? (
        <div className="bg-white p-12 rounded-xl border border-slate-200 text-center text-slate-500 text-sm">
          Nenhum associado encontrado
        </div>
      ) : (
        <div className="bg-white rounded-xl border border-slate-200 shadow-sm overflow-hidden">
          <div className="overflow-x-auto">
            <table className="min-w-full divide-y divide-slate-200 text-left text-sm">
              <thead className="bg-slate-50 text-slate-600 font-semibold">
                <tr>
                  <th scope="col" className="px-6 py-3.5">Nome</th>
                  <th scope="col" className="px-6 py-3.5">CPF</th>
                  <th scope="col" className="px-6 py-3.5">WhatsApp</th>
                  <th scope="col" className="px-6 py-3.5">Vencimento</th>
                  <th scope="col" className="px-6 py-3.5">Situação</th>
                  <th scope="col" className="px-6 py-3.5">Convites</th>
                  <th scope="col" className="px-6 py-3.5 text-right">Ações</th>
                </tr>
              </thead>
              <tbody className="divide-y divide-slate-200">
                {associados.map((socio) => {
                  const sitRotulo = labelSituacao(socio.situacao_financeira);
                  return (
                    <tr key={socio.id} className="hover:bg-slate-50/75 transition duration-150 ease-out">
                      <td className="px-6 py-4 font-medium text-slate-900 whitespace-nowrap">
                        {socio.nome}
                      </td>
                      <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                        {formatCPF(socio.cpf)}
                      </td>
                      <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                        {formatWhatsApp(socio.whatsapp)}
                      </td>
                      <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                        Dia {socio.dia_vencimento}
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap">
                        <span
                          className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium ${
                            sitRotulo === 'Em dia'
                              ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                              : sitRotulo === 'Pendente'
                              ? 'bg-amber-50 text-amber-700 border border-amber-200'
                              : 'bg-rose-50 text-rose-700 border border-rose-200'
                          }`}
                        >
                          {sitRotulo}
                        </span>
                      </td>
                      <td className="px-6 py-4 text-slate-600 whitespace-nowrap">
                        {socio.convidados_usados_mes}/{socio.franquia_convidados} convites
                      </td>
                      <td className="px-6 py-4 whitespace-nowrap text-right space-x-2">
                        <button
                          onClick={() => {
                            setAlertaGlobal(null);
                            setModalConvidadoSocio(socio);
                          }}
                          aria-label={`Adicionar convidado para ${socio.nome}`}
                          type="button"
                          className="inline-flex items-center px-2.5 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 shadow-sm transition duration-150 ease-out"
                        >
                          + Adicionar Convidado
                        </button>
                        <button
                          onClick={() => setModalEditarSocio(socio)}
                          aria-label={`Editar ${socio.nome}`}
                          type="button"
                          className="inline-flex items-center p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition duration-150 ease-out"
                          title="Editar associado"
                        >
                          <Edit2 className="w-4 h-4" />
                        </button>
                        <button
                          onClick={() => setModalExcluirSocio(socio)}
                          aria-label={`Excluir ${socio.nome}`}
                          type="button"
                          className="inline-flex items-center p-1.5 text-rose-500 hover:text-rose-700 hover:bg-rose-50 rounded-lg transition duration-150 ease-out"
                          title="Excluir associado"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>

          {/* Paginação */}
          <div className="px-6 py-4 bg-slate-50 border-t border-slate-200 flex items-center justify-between">
            <span className="text-sm text-slate-600">
              Página {pagina} de {totalPages}
            </span>
            <div className="flex items-center gap-2">
              <button
                onClick={() => setPagina((p) => Math.max(1, p - 1))}
                disabled={pagina <= 1}
                type="button"
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition duration-150 ease-out"
              >
                Página anterior
              </button>
              <button
                onClick={() => setPagina((p) => Math.min(totalPages, p + 1))}
                disabled={pagina >= totalPages}
                type="button"
                className="px-3 py-1.5 border border-slate-300 rounded-lg text-xs font-medium text-slate-700 bg-white hover:bg-slate-50 disabled:opacity-40 disabled:cursor-not-allowed shadow-sm transition duration-150 ease-out"
              >
                Próxima página
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Modal: Adicionar Convidado */}
      {modalConvidadoSocio && (
        <ConvidadoModal
          socio={modalConvidadoSocio}
          onClose={() => setModalConvidadoSocio(null)}
          onSuccess={(resposta) => {
            setModalConvidadoSocio(null);
            queryClient.invalidateQueries({ queryKey: ['associados'] });
            if (resposta.tipo === 'EXCEDENTE' || !resposta.is_gratuito) {
              setAlertaGlobal({
                tipo: 'aviso',
                mensagem:
                  resposta.aviso ||
                  'Franquia de convidados excedida: este convite será cobrado na próxima fatura.',
                taxa: formatBRL(resposta.valor_taxa_extra),
              });
            } else {
              setAlertaGlobal({
                tipo: 'sucesso',
                mensagem: 'Convite emitido com sucesso!',
              });
            }
          }}
        />
      )}

      {/* Modal: Novo Associado */}
      {modalNovoAberto && (
        <NovoAssociadoModal
          onClose={() => setModalNovoAberto(false)}
          onSuccess={() => {
            setModalNovoAberto(false);
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}

      {/* Modal: Editar Associado */}
      {modalEditarSocio && (
        <EditarAssociadoModal
          socio={modalEditarSocio}
          onClose={() => setModalEditarSocio(null)}
          onSuccess={() => {
            setModalEditarSocio(null);
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}

      {/* Modal: Excluir Associado */}
      {modalExcluirSocio && (
        <ExcluirAssociadoModal
          socio={modalExcluirSocio}
          onClose={() => setModalExcluirSocio(null)}
          onSuccess={() => {
            setModalExcluirSocio(null);
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}

      {/* Modal: Importar Planilha */}
      {modalImportarAberto && (
        <ImportarPlanilhaModal
          onClose={() => setModalImportarAberto(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}
    </div>
  );
}

export default AssociadosPage;
