import React, { useState, useEffect, useRef } from 'react';
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
import {
  formatCPF,
  formatWhatsApp,
  formatBRL,
  labelSituacao,
} from '../utils/format';

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

function dataHojeNoClube(): string {
  return new Intl.DateTimeFormat('en-CA', { timeZone: 'America/Sao_Paulo' }).format(new Date());
}

export function AssociadosPage(): React.ReactElement {
  const queryClient = useQueryClient();

  // Estados de busca, filtro e paginação
  const [buscaInput, setBuscaInput] = useState('');
  const [buscaDebounced, setBuscaDebounced] = useState('');
  const [situacaoFiltro, setSituacaoFiltro] = useState('');
  const [pagina, setPagina] = useState(1);

  // Debounce da busca
  const debounceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null);
  const handleBuscaChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const val = e.target.value;
    setBuscaInput(val);
    setPagina(1);
    if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    debounceTimerRef.current = setTimeout(() => {
      setBuscaDebounced(val);
    }, 350);
  };

  useEffect(() => {
    return () => {
      if (debounceTimerRef.current) clearTimeout(debounceTimerRef.current);
    };
  }, []);

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
            className="w-full pl-9 pr-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 placeholder-slate-400 focus:outline-none focus:ring-2 focus:ring-primary/20 transition duration-150 ease-out"
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
            className="w-full sm:w-40 px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-primary/20 transition duration-150 ease-out"
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
        <ModalConvidado
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
        <ModalNovoAssociado
          onClose={() => setModalNovoAberto(false)}
          onSuccess={() => {
            setModalNovoAberto(false);
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}

      {/* Modal: Editar Associado */}
      {modalEditarSocio && (
        <ModalEditarAssociado
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
        <ModalExcluirAssociado
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
        <ModalImportarPlanilha
          onClose={() => setModalImportarAberto(false)}
          onSuccess={() => {
            queryClient.invalidateQueries({ queryKey: ['associados'] });
          }}
        />
      )}
    </div>
  );
}

// -----------------------------------------------------------------------------
// Subcomponentes dos Modais
// -----------------------------------------------------------------------------

function ModalConvidado({
  socio,
  onClose,
  onSuccess,
}: {
  socio: Associado;
  onClose: () => void;
  onSuccess: (resp: {
    is_gratuito: boolean;
    tipo: string;
    valor_taxa_extra: string;
    aviso: string | null;
  }) => void;
}) {
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
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setErroApi(detail.map((d: any) => d.msg).join(', '));
      } else if (typeof detail === 'string') {
        setErroApi(detail);
      } else {
        setErroApi('Não foi possível emitir o convite.');
      }
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Adicionar convidado"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Adicionar convidado
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submetendo}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {submetendo ? 'Emitindo...' : 'Emitir convite'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalNovoAssociado({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
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
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setErroApi(detail.map((d: any) => d.msg).join(', '));
      } else if (typeof detail === 'string') {
        setErroApi(detail);
      } else {
        setErroApi('Erro ao cadastrar associado.');
      }
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Novo associado"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Novo associado
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submetendo}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {submetendo ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalEditarAssociado({
  socio,
  onClose,
  onSuccess,
}: {
  socio: Associado;
  onClose: () => void;
  onSuccess: () => void;
}) {
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
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (Array.isArray(detail)) {
        setErroApi(detail.map((d: any) => d.msg).join(', '));
      } else if (typeof detail === 'string') {
        setErroApi(detail);
      } else {
        setErroApi('Erro ao editar associado.');
      }
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Editar associado"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Editar associado
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
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
              className="w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-primary/20"
            />
          </div>

          <div className="flex justify-end gap-2 pt-2">
            <button
              type="button"
              onClick={onClose}
              className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
            >
              Cancelar
            </button>
            <button
              type="submit"
              disabled={submetendo}
              className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
            >
              {submetendo ? 'Salvando...' : 'Salvar'}
            </button>
          </div>
        </form>
      </div>
    </div>
  );
}

function ModalExcluirAssociado({
  socio,
  onClose,
  onSuccess,
}: {
  socio: Associado;
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [submetendo, setSubmetendo] = useState(false);

  const handleExcluir = async () => {
    setSubmetendo(true);
    try {
      await apiClient.delete(`/associados/${socio.id}`);
      onSuccess();
    } catch {
      // Ignora ou trata erro
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Excluir associado"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-md w-full p-6 space-y-4">
        <h2 className="text-lg font-semibold text-slate-900">
          Excluir associado
        </h2>
        <p className="text-sm text-slate-600">
          Tem certeza de que deseja excluir o associado{' '}
          <strong className="text-slate-900">{socio.nome}</strong>? Esta ação é irreversível.
        </p>

        <div className="flex justify-end gap-2 pt-2">
          <button
            type="button"
            onClick={onClose}
            className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
          >
            Cancelar
          </button>
          <button
            type="button"
            disabled={submetendo}
            onClick={handleExcluir}
            className="px-4 py-2 bg-rose-600 hover:bg-rose-700 text-white rounded-lg text-sm font-medium disabled:opacity-50"
          >
            {submetendo ? 'Excluindo...' : 'Confirmar exclusão'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ModalImportarPlanilha({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: () => void;
}) {
  const [arquivo, setArquivo] = useState<File | null>(null);
  const [atualizarExistentes, setAtualizarExistentes] = useState(false);
  const [erro, setErro] = useState<string | null>(null);
  const [submetendo, setSubmetendo] = useState(false);
  const [relatorio, setRelatorio] = useState<RelatorioImportacao | null>(null);

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setErro(null);
    const files = e.target.files;
    if (files && files.length > 0) {
      const f = files[0];
      setArquivo(f);
    }
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);

    if (!arquivo) return;

    const nomeArquivo = arquivo.name.toLowerCase();
    if (!nomeArquivo.endsWith('.xlsx') && !nomeArquivo.endsWith('.csv')) {
      setErro('Formato de arquivo inválido. Selecione um arquivo .xlsx ou .csv.');
      return;
    }

    setSubmetendo(true);
    try {
      const formData = new FormData();
      formData.append('file', arquivo);

      const res = await apiClient.post<RelatorioImportacao>(
        `/associados/importar?atualizar_existentes=${atualizarExistentes ? 'true' : 'false'}`,
        formData,
        {
          headers: {
            'Content-Type': 'multipart/form-data',
          },
        },
      );
      setRelatorio(res.data);
      onSuccess();
    } catch (err: any) {
      const detail = err.response?.data?.detail;
      if (typeof detail === 'string') {
        setErro(detail);
      } else {
        setErro('Erro ao importar planilha. Verifique o arquivo e tente novamente.');
      }
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <div
      role="dialog"
      aria-label="Importar planilha"
      className="fixed inset-0 z-50 flex items-center justify-center bg-slate-900/50 p-4"
    >
      <div className="bg-white rounded-xl shadow-xl border border-slate-200 max-w-lg w-full p-6 space-y-4">
        <div className="flex items-center justify-between border-b border-slate-100 pb-3">
          <h2 className="text-lg font-semibold text-slate-900">
            Importar planilha
          </h2>
          <button onClick={onClose} className="text-slate-400 hover:text-slate-600">
            <X className="w-5 h-5" />
          </button>
        </div>

        {erro && (
          <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
            {erro}
          </div>
        )}

        {!relatorio ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label htmlFor="arquivo-planilha" className="block text-sm font-medium text-slate-700 mb-1">
                Arquivo da planilha
              </label>
              <input
                id="arquivo-planilha"
                type="file"
                accept=".xlsx,.csv"
                onChange={handleFileChange}
                className="w-full text-sm text-slate-500 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-medium file:bg-slate-100 file:text-slate-700 hover:file:bg-slate-200"
              />
            </div>

            <div className="flex items-center gap-2">
              <input
                id="atualizar-existentes"
                type="checkbox"
                checked={atualizarExistentes}
                onChange={(e) => setAtualizarExistentes(e.target.checked)}
                className="w-4 h-4 text-slate-900 border-slate-300 rounded focus:ring-primary/20"
              />
              <label htmlFor="atualizar-existentes" className="text-sm text-slate-700 cursor-pointer">
                Atualizar existentes
              </label>
            </div>

            <div className="flex justify-end gap-2 pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 hover:bg-slate-50"
              >
                Cancelar
              </button>
              <button
                type="submit"
                disabled={submetendo}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50"
              >
                {submetendo ? 'Enviando...' : 'Enviar planilha'}
              </button>
            </div>
          </form>
        ) : (
          <div className="space-y-4">
            <div className="grid grid-cols-2 gap-3 p-4 bg-slate-50 rounded-lg border border-slate-200 text-sm">
              <div>
                <span className="text-slate-500">Total lidos: </span>
                <span data-testid="import-total-lidos" className="font-semibold text-slate-900">
                  {relatorio.total_lidos}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Importados: </span>
                <span data-testid="import-total-importados" className="font-semibold text-emerald-600">
                  {relatorio.total_importados}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Atualizados: </span>
                <span data-testid="import-total-atualizados" className="font-semibold text-blue-600">
                  {relatorio.total_atualizados}
                </span>
              </div>
              <div>
                <span className="text-slate-500">Ignorados: </span>
                <span data-testid="import-total-ignorados" className="font-semibold text-slate-600">
                  {relatorio.total_ignorados_duplicados}
                </span>
              </div>
            </div>

            {relatorio.erros && relatorio.erros.length > 0 && (
              <div className="space-y-2">
                <p className="text-xs font-semibold uppercase text-slate-500 tracking-wider">
                  Erros identificados:
                </p>
                <div className="max-h-40 overflow-y-auto space-y-1 text-xs">
                  {relatorio.erros.map((err, i) => (
                    <div key={i} className="p-2 bg-red-50 text-red-700 rounded border border-red-200">
                      Linha {err.linha}: {err.campo ? `[${err.campo}] ` : ''}{err.motivo}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium"
              >
                Concluir
              </button>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}

export default AssociadosPage;
