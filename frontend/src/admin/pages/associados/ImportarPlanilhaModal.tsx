import React, { useState } from 'react';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';
import { Modal } from '../../components/Modal';

export type ErroImportacaoItem = {
  linha: number;
  campo?: string;
  motivo: string;
};

export type RelatorioImportacao = {
  total_lidos: number;
  total_importados: number;
  total_atualizados: number;
  total_ignorados_duplicados: number;
  erros: ErroImportacaoItem[];
};

export type ImportarPlanilhaModalProps = {
  onClose: () => void;
  onSuccess: () => void;
};

export function ImportarPlanilhaModal({
  onClose,
  onSuccess,
}: ImportarPlanilhaModalProps): React.ReactElement {
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
      // Validação de 5 MB no cliente antes do envio
      if (f.size > 5 * 1024 * 1024) {
        setErro('O arquivo selecionado excede o limite máximo permitido de 5 MB.');
        setArquivo(null);
        e.target.value = '';
        return;
      }
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
    } catch (err: unknown) {
      setErro(extrairMensagemErro(err, 'Erro ao importar planilha. Verifique o arquivo e tente novamente.'));
    } finally {
      setSubmetendo(false);
    }
  };

  return (
    <Modal
      isOpen={true}
      onClose={onClose}
      title="Importar planilha"
      ariaLabel="Importar planilha"
      maxWidth="max-w-lg"
    >
      <div className="space-y-4">
        {erro && (
          <div
            role="alert"
            className="p-3 bg-red-50 text-red-700 border border-red-200 rounded-lg text-sm"
          >
            {erro}
          </div>
        )}

        {!relatorio ? (
          <form onSubmit={handleSubmit} className="space-y-4">
            <div>
              <label
                htmlFor="arquivo-planilha"
                className="block text-sm font-medium text-slate-700 mb-1"
              >
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
                className="w-4 h-4 text-slate-900 border-slate-300 rounded focus:ring-slate-900/20"
              />
              <label htmlFor="atualizar-existentes" className="text-sm text-slate-700 cursor-pointer">
                Atualizar existentes
              </label>
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
                  {relatorio.erros.map((itemErro, i) => (
                    <div
                      key={i}
                      className="p-2 bg-red-50 text-red-700 rounded border border-red-200"
                    >
                      Linha {itemErro.linha}: {itemErro.campo ? `[${itemErro.campo}] ` : ''}
                      {itemErro.motivo}
                    </div>
                  ))}
                </div>
              </div>
            )}

            <div className="flex justify-end pt-2">
              <button
                type="button"
                onClick={onClose}
                className="px-4 py-2 bg-slate-900 hover:bg-slate-800 text-white rounded-lg text-sm font-medium transition-colors"
              >
                Concluir
              </button>
            </div>
          </div>
        )}
      </div>
    </Modal>
  );
}

export default ImportarPlanilhaModal;
