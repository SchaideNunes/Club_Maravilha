import React, { useState, useRef } from 'react';
import { Eye, AlertCircle } from 'lucide-react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';

export type TemplatesConfig = {
  template_d_menos_3: string;
  template_d0: string;
  template_recibo: string;
  template_d_mais_3: string;
  template_d_mais_7: string;
  chave_pix: string;
};

export type TemplatesSectionProps = {
  values: TemplatesConfig;
  onChange: (campo: keyof TemplatesConfig, valor: string) => void;
  disabled?: boolean;
};

const TEMPLATE_FIELDS: Array<{ label: string; campo: keyof Omit<TemplatesConfig, 'chave_pix'> }> = [
  { label: 'Lembrete D-3', campo: 'template_d_menos_3' },
  { label: 'Cobrança D-0', campo: 'template_d0' },
  { label: 'Recibo de Pagamento', campo: 'template_recibo' },
  { label: 'Aviso D+3', campo: 'template_d_mais_3' },
  { label: 'Aviso D+7', campo: 'template_d_mais_7' },
];

const VARIAVEIS = [
  '{nome}',
  '{valor_base}',
  '{convites_usados}',
  '{convites_extras}',
  '{valor_total}',
  '{vencimento}',
  '{chave_pix}',
];

export function TemplatesSection({
  values,
  onChange,
  disabled,
}: TemplatesSectionProps): React.ReactElement {
  // Controle de foco e cursor para inserção de variáveis
  const ultimoCampoRef = useRef<keyof Omit<TemplatesConfig, 'chave_pix'>>('template_d0');
  const selecaoRef = useRef<{ start: number; end: number }>({ start: 0, end: 0 });

  // Previews e erros
  const [previews, setPreviews] = useState<Record<string, string>>({});
  const [errosPreview, setErrosPreview] = useState<Record<string, string>>({});
  const [carregandoPreview, setCarregandoPreview] = useState<Record<string, boolean>>({});

  const handleSelectOuFocus = (
    campo: keyof Omit<TemplatesConfig, 'chave_pix'>,
    e: React.SyntheticEvent<HTMLTextAreaElement>
  ) => {
    ultimoCampoRef.current = campo;
    const target = e.currentTarget;
    selecaoRef.current = {
      start: target.selectionStart ?? 0,
      end: target.selectionEnd ?? 0,
    };
  };

  const handleInserirVariavel = (variavel: string) => {
    const campo = ultimoCampoRef.current;
    const textoAtual = values[campo] || '';
    const { start, end } = selecaoRef.current;

    const novoTexto = textoAtual.slice(0, start) + variavel + textoAtual.slice(end);
    onChange(campo, novoTexto);

    const novaPosicao = start + variavel.length;
    selecaoRef.current = { start: novaPosicao, end: novaPosicao };
  };

  const handlePreview = async (campo: keyof Omit<TemplatesConfig, 'chave_pix'>) => {
    setErrosPreview((prev) => ({ ...prev, [campo]: '' }));
    setCarregandoPreview((prev) => ({ ...prev, [campo]: true }));

    try {
      const res = await apiClient.post<{ mensagem: string }>('/configuracao/preview-template', {
        template: values[campo],
      });
      setPreviews((prev) => ({ ...prev, [campo]: res.data.mensagem }));
    } catch (err) {
      const msg = extrairMensagemErro(err, 'Template inválido.');
      setErrosPreview((prev) => ({ ...prev, [campo]: msg }));
    } finally {
      setCarregandoPreview((prev) => ({ ...prev, [campo]: false }));
    }
  };

  return (
    <section
      aria-labelledby="sec-templates"
      role="region"
      className="bg-white rounded-xl border border-slate-200 p-6 shadow-sm space-y-6"
    >
      <div className="pb-4 border-b border-slate-100">
        <h2 id="sec-templates" className="text-lg font-bold text-slate-900">
          Templates da régua
        </h2>
        <p className="text-sm text-slate-500">
          Personalize as mensagens enviadas em cada etapa da régua de cobrança automática.
        </p>
      </div>

      {/* Variáveis Clicáveis */}
      <div className="bg-slate-50 border border-slate-200 rounded-xl p-4 space-y-2">
        <p className="text-xs font-semibold text-slate-700 uppercase tracking-wider">
          Variáveis disponíveis (clique para inserir no campo em edição):
        </p>
        <div className="flex flex-wrap gap-2">
          {VARIAVEIS.map((variavel) => (
            <button
              key={variavel}
              type="button"
              disabled={disabled}
              onClick={() => handleInserirVariavel(variavel)}
              className="px-2.5 py-1 text-xs font-mono font-medium rounded-lg border border-slate-300 bg-white hover:bg-slate-100 text-slate-800 transition-colors focus:outline-none focus:ring-2 focus:ring-slate-400 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {variavel}
            </button>
          ))}
        </div>
      </div>

      {/* Chave Pix */}
      <div className="flex flex-col gap-1.5 max-w-md">
        <label htmlFor="cfg-chave-pix" className="text-xs font-semibold text-slate-700">
          Chave Pix do clube
        </label>
        <input
          id="cfg-chave-pix"
          type="text"
          disabled={disabled}
          value={values.chave_pix}
          onChange={(e) => onChange('chave_pix', e.target.value)}
          placeholder="Ex: financeiro@clubmaravilha.com.br"
          className="px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
        />
      </div>

      {/* Lista de Templates */}
      <div className="space-y-6">
        {TEMPLATE_FIELDS.map(({ label, campo }) => (
          <div key={campo} className="space-y-2 border-t border-slate-100 pt-4">
            <div className="flex items-center justify-between">
              <label htmlFor={`cfg-${campo}`} className="text-sm font-semibold text-slate-800">
                {label}
              </label>

              <button
                type="button"
                onClick={() => handlePreview(campo)}
                disabled={carregandoPreview[campo] || disabled}
                className="flex items-center gap-1.5 px-3 py-1.5 text-xs font-medium rounded-lg border border-slate-300 text-slate-700 bg-white hover:bg-slate-50 transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                <Eye className="w-3.5 h-3.5" />
                <span>{`Pré-visualizar ${label}`}</span>
              </button>
            </div>

            <textarea
              id={`cfg-${campo}`}
              rows={3}
              disabled={disabled}
              value={values[campo]}
              onChange={(e) => {
                onChange(campo, e.target.value);
                selecaoRef.current = {
                  start: e.target.selectionStart ?? 0,
                  end: e.target.selectionEnd ?? 0,
                };
              }}
              onFocus={(e) => handleSelectOuFocus(campo, e)}
              onSelect={(e) => handleSelectOuFocus(campo, e)}
              className="w-full px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-sm font-sans text-slate-900 focus:outline-none focus:ring-2 focus:ring-slate-400 focus:bg-white transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
            />

            {errosPreview[campo] && (
              <div
                role="alert"
                className="p-3 bg-rose-50 border border-rose-200 rounded-lg text-rose-800 text-xs flex items-center gap-2"
              >
                <AlertCircle className="w-4 h-4 text-rose-600 shrink-0" />
                <span className="flex-1 font-medium">{errosPreview[campo]}</span>
              </div>
            )}

            {previews[campo] && (
              <div
                data-testid={`preview-${campo}`}
                className="p-3 bg-slate-50 border border-slate-200 rounded-lg text-xs font-mono text-slate-800 whitespace-pre-wrap"
              >
                {previews[campo]}
              </div>
            )}
          </div>
        ))}
      </div>
    </section>
  );
}

export default TemplatesSection;
