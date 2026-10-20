import React, { useState } from 'react';
import { Link, useParams } from 'react-router-dom';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import axios from 'axios';
import { AlertCircle, ArrowLeft, CheckCircle, UserX, UserCheck } from 'lucide-react';
import { apiClient } from '../api/client';
import { extrairMensagemErro } from '../api/errors';
import { formatBRL, formatCPF, formatDate, formatWhatsApp, labelSituacao } from '../utils/format';
import { ConvidadoModal } from './associados/ConvidadoModal';
import { FamiliaTab } from './associados/FamiliaTab';
import { FormularioAssociado } from './associados/FormularioAssociado';
import { FotoAssociado } from './associados/FotoAssociado';
import { ConvidadosTab, FinanceiroTab, MensagensTab } from './associados/HistoricoTabs';
import { InativarAssociadoModal } from './associados/InativarAssociadoModal';
import { Associado, InativacaoResposta, labelStatusAssociado } from './associados/tipos';

const ABAS = [
  { id: 'dados', rotulo: 'Dados cadastrais' },
  { id: 'familia', rotulo: 'Família' },
  { id: 'financeiro', rotulo: 'Financeiro' },
  { id: 'convidados', rotulo: 'Convidados' },
  { id: 'mensagens', rotulo: 'Mensagens' },
] as const;

type Aba = (typeof ABAS)[number]['id'];

const CLASSE_STATUS: Record<string, string> = {
  ATIVO: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  INADIMPLENTE: 'bg-amber-50 text-amber-700 border-amber-200',
  BLOQUEADO: 'bg-rose-50 text-rose-700 border-rose-200',
  INATIVO: 'bg-slate-100 text-slate-600 border-slate-300',
};

const CLASSE_SITUACAO: Record<string, string> = {
  EM_DIA: 'bg-emerald-50 text-emerald-700 border-emerald-200',
  PENDENTE: 'bg-amber-50 text-amber-700 border-amber-200',
  ATRASADO: 'bg-rose-50 text-rose-700 border-rose-200',
};

function plural(qtd: number, singular: string, pluralTexto: string): string {
  return `${qtd} ${qtd === 1 ? singular : pluralTexto}`;
}

type Aviso = { tipo: 'sucesso' | 'aviso'; mensagem: string; detalhe?: string };

export function FichaAssociadoPage(): React.ReactElement {
  const { id = '' } = useParams();
  const queryClient = useQueryClient();
  const queryKey = ['associado', id];

  const { data: associado, isLoading, error } = useQuery<Associado>({
    queryKey,
    queryFn: async () => (await apiClient.get<Associado>(`/associados/${id}`)).data,
  });

  const [aba, setAba] = useState<Aba>('dados');
  const [salvando, setSalvando] = useState(false);
  const [erroSalvar, setErroSalvar] = useState<string | null>(null);
  const [salvoEm, setSalvoEm] = useState<number | null>(null);
  const [modalInativar, setModalInativar] = useState(false);
  const [modalConvidado, setModalConvidado] = useState(false);
  const [aviso, setAviso] = useState<Aviso | null>(null);
  const [reativando, setReativando] = useState(false);

  const atualizarCache = (dados: Associado) => {
    queryClient.setQueryData(queryKey, dados);
    queryClient.invalidateQueries({ queryKey: ['associados'] });
  };

  const salvar = async (payload: Record<string, unknown>) => {
    setSalvando(true);
    setErroSalvar(null);
    setSalvoEm(null);
    try {
      const { data } = await apiClient.patch<Associado>(`/associados/${id}`, payload);
      atualizarCache(data);
      setSalvoEm(Date.now());
    } catch (err: unknown) {
      setErroSalvar(extrairMensagemErro(err, 'Erro ao salvar as alterações.'));
    } finally {
      setSalvando(false);
    }
  };

  const reativar = async () => {
    setReativando(true);
    setAviso(null);
    try {
      const { data } = await apiClient.post<Associado>(`/associados/${id}/reativar`);
      atualizarCache(data);
      setAviso({ tipo: 'sucesso', mensagem: 'Associado reativado.' });
    } catch (err: unknown) {
      setAviso({ tipo: 'aviso', mensagem: extrairMensagemErro(err, 'Erro ao reativar associado.') });
    } finally {
      setReativando(false);
    }
  };

  const aposInativar = (resposta: InativacaoResposta) => {
    setModalInativar(false);
    atualizarCache(resposta.associado);
    queryClient.invalidateQueries({ queryKey: ['faturas'] });
    queryClient.invalidateQueries({ queryKey: ['convidados'] });
    setAviso({
      tipo: 'sucesso',
      mensagem: 'Associado inativado.',
      detalhe: `Cancelados: ${plural(resposta.faturas_canceladas, 'fatura futura', 'faturas futuras')}, ${plural(
        resposta.convites_cancelados,
        'convite',
        'convites',
      )} e ${plural(resposta.reservas_canceladas, 'reserva', 'reservas')}.`,
    });
  };

  if (isLoading) {
    return <div className="p-8 text-sm text-slate-500">Carregando...</div>;
  }

  if (!associado) {
    const naoEncontrado = axios.isAxiosError(error) && error.response?.status === 404;
    return (
      <div className="p-8 space-y-4">
        <div role="alert" className="p-4 rounded-lg bg-red-50 text-red-700 border border-red-200 text-sm">
          {naoEncontrado ? 'Associado não encontrado' : 'Não foi possível carregar o associado. Tente novamente mais tarde.'}
        </div>
        <Link to="/admin/associados" className="text-sm font-medium text-slate-600 hover:text-slate-900">
          Voltar para associados
        </Link>
      </div>
    );
  }

  const inativo = associado.status === 'INATIVO';

  return (
    <div className="p-8 max-w-5xl space-y-6">
      <Link
        to="/admin/associados"
        className="inline-flex items-center gap-1.5 text-sm font-medium text-slate-600 hover:text-slate-900"
      >
        <ArrowLeft className="w-4 h-4" />
        Voltar para associados
      </Link>

      {/* Cabeçalho da ficha */}
      <div
        data-testid="cabecalho-associado"
        className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 flex flex-col md:flex-row gap-6"
      >
        <FotoAssociado associado={associado} onAtualizado={atualizarCache} />

        <div className="flex-1 min-w-0 space-y-3">
          <div className="flex flex-wrap items-center gap-2">
            <h1 className="text-2xl font-bold tracking-tight text-slate-900 mr-2">{associado.nome}</h1>
            <span
              className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                CLASSE_STATUS[associado.status] ?? CLASSE_STATUS.INATIVO
              }`}
            >
              {labelStatusAssociado(associado.status)}
            </span>
            {!inativo && (
              <span
                className={`inline-flex items-center px-2.5 py-0.5 rounded-full text-xs font-medium border ${
                  CLASSE_SITUACAO[associado.situacao_financeira] ?? CLASSE_SITUACAO.EM_DIA
                }`}
              >
                {labelSituacao(associado.situacao_financeira)}
              </span>
            )}
          </div>

          <dl className="grid grid-cols-1 sm:grid-cols-2 gap-x-6 gap-y-1 text-sm">
            <div className="flex gap-2">
              <dt className="text-slate-500">CPF</dt>
              <dd className="text-slate-900">{formatCPF(associado.cpf)}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">WhatsApp</dt>
              <dd className="text-slate-900">{formatWhatsApp(associado.whatsapp)}</dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">Plano</dt>
              <dd className="text-slate-900">
                {associado.plano
                  ? `${associado.plano.nome} (${formatBRL(associado.plano.valor_mensalidade)})`
                  : 'Mensalidade padrão'}
              </dd>
            </div>
            <div className="flex gap-2">
              <dt className="text-slate-500">Vencimento</dt>
              <dd className="text-slate-900">Dia {associado.dia_vencimento}</dd>
            </div>
          </dl>
          <p className="text-xs text-slate-500">Sócio desde {formatDate(associado.data_adesao)}</p>
        </div>

        <div className="flex md:flex-col gap-2 md:items-end shrink-0">
          {inativo ? (
            <button
              type="button"
              onClick={reativar}
              disabled={reativando}
              className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 disabled:opacity-50"
            >
              <UserCheck className="w-4 h-4" />
              Reativar associado
            </button>
          ) : (
            <>
              <button
                type="button"
                onClick={() => {
                  setAviso(null);
                  setModalConvidado(true);
                }}
                className="inline-flex items-center px-4 py-2 border border-slate-300 rounded-lg text-sm font-medium text-slate-700 bg-white hover:bg-slate-50"
              >
                + Adicionar convidado
              </button>
              <button
                type="button"
                onClick={() => setModalInativar(true)}
                className="inline-flex items-center gap-2 px-4 py-2 rounded-lg text-sm font-medium text-rose-700 hover:bg-rose-50"
              >
                <UserX className="w-4 h-4" />
                Inativar associado
              </button>
            </>
          )}
        </div>
      </div>

      {inativo && (
        <div role="status" className="p-4 rounded-lg bg-slate-100 border border-slate-300 text-sm text-slate-700">
          <p className="font-medium">
            Associado inativo desde {associado.data_inativacao ? formatDate(associado.data_inativacao) : '—'}
          </p>
          {associado.motivo_inativacao && <p className="mt-1">Motivo: {associado.motivo_inativacao}</p>}
          <p className="mt-1 text-slate-500">
            Não recebe faturas nem lembretes e não tem acesso ao clube. Dívidas anteriores continuam em aberto.
          </p>
        </div>
      )}

      {aviso && (
        <div
          role={aviso.tipo === 'aviso' ? 'alert' : undefined}
          className={`p-4 rounded-lg text-sm flex items-start gap-3 border ${
            aviso.tipo === 'aviso'
              ? 'bg-amber-50 text-amber-800 border-amber-200'
              : 'bg-emerald-50 text-emerald-800 border-emerald-200'
          }`}
        >
          {aviso.tipo === 'aviso' ? (
            <AlertCircle className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
          ) : (
            <CheckCircle className="w-5 h-5 text-emerald-600 shrink-0 mt-0.5" />
          )}
          <div>
            <p className="font-medium">{aviso.mensagem}</p>
            {aviso.detalhe && <p className="mt-1">{aviso.detalhe}</p>}
          </div>
        </div>
      )}

      {/* Abas */}
      <div>
        <div role="tablist" aria-label="Seções da ficha" className="flex flex-wrap gap-1 border-b border-slate-200">
          {ABAS.map((item) => (
            <button
              key={item.id}
              type="button"
              role="tab"
              id={`aba-${item.id}`}
              aria-selected={aba === item.id}
              aria-controls={`painel-${item.id}`}
              onClick={() => setAba(item.id)}
              className={`px-4 py-2.5 text-sm font-medium border-b-2 -mb-px whitespace-nowrap transition-colors ${
                aba === item.id
                  ? 'border-slate-900 text-slate-900'
                  : 'border-transparent text-slate-500 hover:text-slate-900'
              }`}
            >
              {item.rotulo}
            </button>
          ))}
        </div>

        <div role="tabpanel" id={`painel-${aba}`} aria-labelledby={`aba-${aba}`} className="pt-6">
          {aba === 'dados' && (
            <FormularioAssociado
              key={associado.id}
              associado={associado}
              rotuloEnviar="Salvar alterações"
              enviando={salvando}
              erroApi={erroSalvar}
              mensagemSucesso={salvoEm ? 'Alterações salvas' : null}
              onEnviar={salvar}
            />
          )}
          {aba !== 'dados' && (
            <div className="bg-white rounded-xl border border-slate-200 shadow-sm p-6 overflow-x-auto">
              {aba === 'familia' && <FamiliaTab associadoId={associado.id} />}
              {aba === 'financeiro' && <FinanceiroTab associadoId={associado.id} />}
              {aba === 'convidados' && <ConvidadosTab associadoId={associado.id} />}
              {aba === 'mensagens' && <MensagensTab associadoId={associado.id} />}
            </div>
          )}
        </div>
      </div>

      {modalInativar && (
        <InativarAssociadoModal associado={associado} onClose={() => setModalInativar(false)} onSuccess={aposInativar} />
      )}

      {modalConvidado && (
        <ConvidadoModal
          socio={associado}
          onClose={() => setModalConvidado(false)}
          onSuccess={(resposta) => {
            setModalConvidado(false);
            queryClient.invalidateQueries({ queryKey });
            queryClient.invalidateQueries({ queryKey: ['convidados'] });
            setAviso(
              resposta.tipo === 'EXCEDENTE' || !resposta.is_gratuito
                ? {
                    tipo: 'aviso',
                    mensagem:
                      resposta.aviso || 'Franquia de convidados excedida: este convite será cobrado na próxima fatura.',
                    detalhe: formatBRL(resposta.valor_taxa_extra),
                  }
                : { tipo: 'sucesso', mensagem: 'Convite emitido com sucesso!' },
            );
          }}
        />
      )}
    </div>
  );
}

export default FichaAssociadoPage;
