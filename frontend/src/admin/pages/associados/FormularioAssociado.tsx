import React, { useRef, useState } from 'react';
import { useQuery } from '@tanstack/react-query';
import { apiClient } from '../../api/client';
import { formatBRL, mascararCEP } from '../../utils/format';
import { Associado, Plano, SEXOS, UFS } from './tipos';

const CLASSE_INPUT =
  'w-full px-3 py-2 border border-slate-300 rounded-lg text-sm text-slate-900 bg-white focus:outline-none focus:ring-2 focus:ring-slate-900/20 focus:border-slate-900 disabled:bg-slate-50 disabled:text-slate-500';

const CAMPOS_OPCIONAIS = [
  'data_nascimento',
  'sexo',
  'rg',
  'profissao',
  'cep',
  'logradouro',
  'numero',
  'complemento',
  'bairro',
  'cidade',
  'uf',
  'observacoes',
] as const;

type Campos = Record<
  'nome' | 'cpf' | 'whatsapp' | 'email' | 'plano_id' | 'dia_vencimento' | (typeof CAMPOS_OPCIONAIS)[number],
  string
>;

function camposIniciais(associado?: Associado): Campos {
  return {
    nome: associado?.nome ?? '',
    cpf: associado?.cpf ?? '',
    whatsapp: associado?.whatsapp ?? '',
    email: associado?.email ?? '',
    plano_id: associado?.plano?.id ?? '',
    dia_vencimento: String(associado?.dia_vencimento ?? 10),
    data_nascimento: associado?.data_nascimento ?? '',
    sexo: associado?.sexo ?? '',
    rg: associado?.rg ?? '',
    profissao: associado?.profissao ?? '',
    cep: associado?.cep ?? '',
    logradouro: associado?.logradouro ?? '',
    numero: associado?.numero ?? '',
    complemento: associado?.complemento ?? '',
    bairro: associado?.bairro ?? '',
    cidade: associado?.cidade ?? '',
    uf: associado?.uf ?? '',
    observacoes: associado?.observacoes ?? '',
  };
}

/** Valor em R$ com espaço comum (o Intl usa espaço não separável), para rótulos de <option>. */
function brl(valor: string): string {
  return formatBRL(valor).replace(/\s/g, ' ');
}

/**
 * Monta o corpo da requisição. No cadastro, campos opcionais vazios são omitidos; na edição eles são
 * enviados como null (para apagar o valor) e o CPF nunca é enviado (não é editável).
 */
function montarPayload(campos: Campos, edicao: boolean): Record<string, unknown> {
  const payload: Record<string, unknown> = {
    nome: campos.nome.trim(),
    whatsapp: campos.whatsapp.trim(),
    email: campos.email.trim(),
    dia_vencimento: parseInt(campos.dia_vencimento, 10) || 10,
  };
  if (!edicao) payload.cpf = campos.cpf.trim();

  for (const campo of CAMPOS_OPCIONAIS) {
    const valor = campos[campo].trim();
    if (valor) payload[campo] = valor;
    else if (edicao) payload[campo] = null;
  }

  if (campos.plano_id) payload.plano_id = campos.plano_id;
  else if (edicao) payload.plano_id = null;
  return payload;
}

function validar(campos: Campos): Record<string, string> {
  const erros: Record<string, string> = {};
  if (!campos.nome.trim()) erros.nome = 'Nome é obrigatório.';
  if (!campos.cpf.trim()) erros.cpf = 'CPF é obrigatório.';
  if (!campos.whatsapp.trim()) erros.whatsapp = 'WhatsApp é obrigatório.';
  if (!campos.email.trim()) erros.email = 'E-mail é obrigatório.';
  if (campos.cep && campos.cep.replace(/\D/g, '').length !== 8) erros.cep = 'CEP deve ter 8 dígitos.';
  const dia = parseInt(campos.dia_vencimento, 10);
  if (!(dia >= 1 && dia <= 31)) erros.dia_vencimento = 'Informe um dia entre 1 e 31.';
  return erros;
}

type StatusCep = 'buscando' | 'nao_encontrado' | 'falhou' | null;

export type FormularioAssociadoProps = {
  /** Sócio em edição; ausente no cadastro de um novo sócio. */
  associado?: Associado;
  rotuloEnviar: string;
  enviando: boolean;
  erroApi: string | null;
  mensagemSucesso?: string | null;
  onEnviar: (payload: Record<string, unknown>) => void;
  /** Ação secundária ao lado do botão de envio (ex.: link "Cancelar"). */
  acaoSecundaria?: React.ReactNode;
};

export function FormularioAssociado({
  associado,
  rotuloEnviar,
  enviando,
  erroApi,
  mensagemSucesso,
  onEnviar,
  acaoSecundaria,
}: FormularioAssociadoProps): React.ReactElement {
  const edicao = Boolean(associado);
  const [campos, setCampos] = useState<Campos>(() => camposIniciais(associado));
  const [erros, setErros] = useState<Record<string, string>>({});
  const [statusCep, setStatusCep] = useState<StatusCep>(null);
  const cepConsultadoRef = useRef<string | null>(null);

  const { data: planosAtivos = [] } = useQuery<Plano[]>({
    queryKey: ['planos', 'ativos'],
    queryFn: async () => (await apiClient.get<Plano[]>('/planos/', { params: { ativo: true } })).data,
  });

  const { data: mensalidadePadrao } = useQuery<string>({
    queryKey: ['mensalidade-padrao'],
    queryFn: async () =>
      String((await apiClient.get<{ valor_mensalidade: string }>('/configuracao')).data.valor_mensalidade),
  });

  // Um sócio pode continuar em um plano já desativado: ele segue disponível só para ele
  const planoAtualDesativado =
    associado?.plano && !planosAtivos.some((p) => p.id === associado.plano?.id) ? associado.plano : null;

  const alterar = (campo: keyof Campos, valor: string) => setCampos((atual) => ({ ...atual, [campo]: valor }));

  const consultarCep = async (digitos: string) => {
    cepConsultadoRef.current = digitos;
    setStatusCep('buscando');
    try {
      const resposta = await fetch(`https://viacep.com.br/ws/${digitos}/json/`);
      const dados = await resposta.json();
      if (cepConsultadoRef.current !== digitos) return; // o usuário já digitou outro CEP
      if (!resposta.ok || dados.erro) {
        setStatusCep('nao_encontrado');
        return;
      }
      setCampos((atual) => ({
        ...atual,
        logradouro: dados.logradouro || atual.logradouro,
        bairro: dados.bairro || atual.bairro,
        cidade: dados.localidade || atual.cidade,
        uf: dados.uf || atual.uf,
      }));
      setStatusCep(null);
    } catch {
      if (cepConsultadoRef.current === digitos) setStatusCep('falhou');
    }
  };

  const handleCep = (valor: string) => {
    const mascarado = mascararCEP(valor);
    alterar('cep', mascarado);
    const digitos = mascarado.replace(/\D/g, '');
    if (digitos.length === 8 && digitos !== cepConsultadoRef.current) {
      void consultarCep(digitos);
    } else if (digitos.length < 8) {
      cepConsultadoRef.current = null;
      setStatusCep(null);
    }
  };

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    const encontrados = validar(campos);
    setErros(encontrados);
    if (Object.keys(encontrados).length > 0) return;
    onEnviar(montarPayload(campos, edicao));
  };

  const campoTexto = (
    campo: keyof Campos,
    rotulo: string,
    opcoes: { tipo?: string; className?: string; obrigatorio?: boolean; disabled?: boolean; maxLength?: number } = {},
  ) => (
    <div className={opcoes.className}>
      <label htmlFor={`socio-${campo}`} className="block text-sm font-medium text-slate-700 mb-1">
        {rotulo}
      </label>
      <input
        id={`socio-${campo}`}
        type={opcoes.tipo ?? 'text'}
        value={campos[campo]}
        onChange={(e) => alterar(campo, e.target.value)}
        disabled={opcoes.disabled}
        maxLength={opcoes.maxLength}
        aria-required={opcoes.obrigatorio || undefined}
        aria-invalid={erros[campo] ? true : undefined}
        className={CLASSE_INPUT}
      />
      {erros[campo] && <p className="mt-1 text-xs text-red-600">{erros[campo]}</p>}
    </div>
  );

  return (
    <form onSubmit={handleSubmit} noValidate className="space-y-6">
      {erroApi && (
        <div role="alert" className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm">
          {erroApi}
        </div>
      )}
      {mensagemSucesso && (
        <div role="status" className="p-3 bg-emerald-50 text-emerald-800 border border-emerald-200 rounded-lg text-sm">
          {mensagemSucesso}
        </div>
      )}

      <fieldset className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <legend className="px-2 -ml-2 text-sm font-semibold text-slate-900">Dados pessoais</legend>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          {campoTexto('nome', 'Nome', { className: 'md:col-span-4', obrigatorio: true, maxLength: 150 })}
          {campoTexto('cpf', 'CPF', { className: 'md:col-span-2', obrigatorio: true, disabled: edicao })}
          {campoTexto('data_nascimento', 'Data de nascimento', { tipo: 'date', className: 'md:col-span-2' })}
          <div className="md:col-span-2">
            <label htmlFor="socio-sexo" className="block text-sm font-medium text-slate-700 mb-1">
              Sexo
            </label>
            <select
              id="socio-sexo"
              value={campos.sexo}
              onChange={(e) => alterar('sexo', e.target.value)}
              className={CLASSE_INPUT}
            >
              <option value="">Não informado</option>
              {SEXOS.map((s) => (
                <option key={s.valor} value={s.valor}>
                  {s.rotulo}
                </option>
              ))}
            </select>
          </div>
          {campoTexto('rg', 'RG', { className: 'md:col-span-2', maxLength: 20 })}
          {campoTexto('profissao', 'Profissão', { className: 'md:col-span-6', maxLength: 100 })}
        </div>
      </fieldset>

      <fieldset className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <legend className="px-2 -ml-2 text-sm font-semibold text-slate-900">Contato</legend>
        <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
          {campoTexto('whatsapp', 'WhatsApp', { tipo: 'tel', obrigatorio: true })}
          {campoTexto('email', 'E-mail', { tipo: 'email', obrigatorio: true, maxLength: 150 })}
        </div>
      </fieldset>

      <fieldset className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <legend className="px-2 -ml-2 text-sm font-semibold text-slate-900">Endereço</legend>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div className="md:col-span-2">
            <label htmlFor="socio-cep" className="block text-sm font-medium text-slate-700 mb-1">
              CEP
            </label>
            <input
              id="socio-cep"
              type="text"
              inputMode="numeric"
              value={campos.cep}
              onChange={(e) => handleCep(e.target.value)}
              aria-describedby="socio-cep-ajuda"
              aria-invalid={erros.cep ? true : undefined}
              className={CLASSE_INPUT}
            />
            <p id="socio-cep-ajuda" className="mt-1 text-xs text-slate-500" aria-live="polite">
              {statusCep === 'buscando' && 'Buscando endereço...'}
              {statusCep === 'nao_encontrado' && 'CEP não encontrado'}
              {statusCep === 'falhou' && 'Não foi possível consultar o CEP agora. Preencha o endereço manualmente.'}
              {!statusCep && !erros.cep && 'O endereço é preenchido automaticamente.'}
            </p>
            {erros.cep && <p className="mt-1 text-xs text-red-600">{erros.cep}</p>}
          </div>
          {campoTexto('logradouro', 'Logradouro', { className: 'md:col-span-4', maxLength: 150 })}
          {campoTexto('numero', 'Número', { className: 'md:col-span-1', maxLength: 10 })}
          {campoTexto('complemento', 'Complemento', { className: 'md:col-span-2', maxLength: 80 })}
          {campoTexto('bairro', 'Bairro', { className: 'md:col-span-3', maxLength: 80 })}
          {campoTexto('cidade', 'Cidade', { className: 'md:col-span-4', maxLength: 80 })}
          <div className="md:col-span-2">
            <label htmlFor="socio-uf" className="block text-sm font-medium text-slate-700 mb-1">
              UF
            </label>
            <select id="socio-uf" value={campos.uf} onChange={(e) => alterar('uf', e.target.value)} className={CLASSE_INPUT}>
              <option value="">—</option>
              {UFS.map((uf) => (
                <option key={uf} value={uf}>
                  {uf}
                </option>
              ))}
            </select>
          </div>
        </div>
      </fieldset>

      <fieldset className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <legend className="px-2 -ml-2 text-sm font-semibold text-slate-900">Plano e cobrança</legend>
        <div className="grid grid-cols-1 md:grid-cols-6 gap-4">
          <div className="md:col-span-4">
            <label htmlFor="socio-plano" className="block text-sm font-medium text-slate-700 mb-1">
              Plano
            </label>
            <select
              id="socio-plano"
              value={campos.plano_id}
              onChange={(e) => alterar('plano_id', e.target.value)}
              className={CLASSE_INPUT}
            >
              <option value="">
                {mensalidadePadrao ? `Mensalidade padrão (${brl(mensalidadePadrao)})` : 'Mensalidade padrão'}
              </option>
              {planosAtivos.map((plano) => (
                <option key={plano.id} value={plano.id}>
                  {`${plano.nome} — ${brl(plano.valor_mensalidade)}`}
                </option>
              ))}
              {planoAtualDesativado && (
                <option value={planoAtualDesativado.id}>
                  {`${planoAtualDesativado.nome} — ${brl(planoAtualDesativado.valor_mensalidade)} (desativado)`}
                </option>
              )}
            </select>
          </div>
          {campoTexto('dia_vencimento', 'Dia de vencimento', { tipo: 'number', className: 'md:col-span-2' })}
        </div>
      </fieldset>

      <fieldset className="bg-white rounded-xl border border-slate-200 shadow-sm p-6">
        <legend className="px-2 -ml-2 text-sm font-semibold text-slate-900">Observações</legend>
        <label htmlFor="socio-observacoes" className="sr-only">
          Observações
        </label>
        <textarea
          id="socio-observacoes"
          rows={3}
          value={campos.observacoes}
          onChange={(e) => alterar('observacoes', e.target.value)}
          className={CLASSE_INPUT}
        />
      </fieldset>

      <div className="flex items-center justify-end gap-3">
        {acaoSecundaria}
        <button
          type="submit"
          disabled={enviando}
          className="px-5 py-2.5 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium disabled:opacity-50 transition-colors"
        >
          {enviando ? 'Salvando...' : rotuloEnviar}
        </button>
      </div>
    </form>
  );
}

export default FormularioAssociado;
