import React, { useState, useEffect } from 'react';
import { AlertCircle } from 'lucide-react';
import { Modal } from '../../components/Modal';
import { formatBRL } from '../../utils/format';
import { apiClient } from '../../api/client';
import { extrairMensagemErro } from '../../api/errors';

export type FaturaItem = {
  id: string;
  associado_id: string;
  associado_nome: string;
  associado_cpf: string;
  referencia_mes: string;
  data_vencimento: string;
  valor_base: string;
  valor_convidados_excedentes: string;
  valor_desconto: string;
  valor_total: string;
  convites_usados: number;
  convites_extras: number;
  status: 'PENDENTE' | 'ATRASADA' | 'PAGO' | 'CANCELADO';
  forma_pagamento: 'PIX' | 'CARTAO' | 'DINHEIRO' | null;
  data_pagamento: string | null;
  lembretes_ativos: boolean;
};

export type BaixaManualModalProps = {
  isOpen: boolean;
  onClose: () => void;
  fatura: FaturaItem | null;
  onSuccess: () => void;
};

export function BaixaManualModal({
  isOpen,
  onClose,
  fatura,
  onSuccess,
}: BaixaManualModalProps): React.ReactElement | null {
  const [formaPagamento, setFormaPagamento] = useState<'PIX' | 'CARTAO' | 'DINHEIRO'>('PIX');
  const [erro, setErro] = useState<string | null>(null);
  const [salvando, setSalvando] = useState(false);

  useEffect(() => {
    if (isOpen) {
      setFormaPagamento('PIX');
      setErro(null);
      setSalvando(false);
    }
  }, [isOpen]);

  if (!fatura) return null;

  const handleConfirmar = async (e: React.FormEvent) => {
    e.preventDefault();
    setErro(null);
    setSalvando(true);

    try {
      await apiClient.post(`/faturas/${fatura.id}/baixa-manual`, {
        forma_pagamento: formaPagamento,
      });
      onSuccess();
    } catch (err) {
      const msg = extrairMensagemErro(err, 'Não foi possível confirmar o pagamento.');
      setErro(msg);
    } finally {
      setSalvando(false);
    }
  };

  return (
    <Modal isOpen={isOpen} onClose={onClose} title="Dar baixa manual" maxWidth="max-w-md">
      <form onSubmit={handleConfirmar} className="space-y-4">
        {erro && (
          <div
            role="alert"
            className="flex items-start gap-2.5 p-3 rounded-lg bg-rose-50 border border-rose-200 text-rose-800 text-sm"
          >
            <AlertCircle className="w-4 h-4 shrink-0 text-rose-600 mt-0.5" />
            <span className="flex-1">{erro}</span>
          </div>
        )}

        <div className="bg-slate-50 border border-slate-200 rounded-lg p-3 space-y-1.5 text-sm">
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Associado:</span>
            <span className="font-semibold text-slate-900">{fatura.associado_nome}</span>
          </div>
          <div className="flex justify-between items-center">
            <span className="text-slate-500">Valor Total:</span>
            <span className="font-bold text-slate-900 text-base">{formatBRL(fatura.valor_total)}</span>
          </div>
        </div>

        <fieldset className="space-y-2">
          <legend className="text-xs font-semibold text-slate-700 mb-2">Forma de pagamento</legend>
          <div className="grid grid-cols-3 gap-2">
            <label
              className={`flex items-center gap-2 p-2.5 border rounded-lg cursor-pointer text-sm font-medium transition-colors ${
                formaPagamento === 'PIX'
                  ? 'border-slate-900 bg-slate-50 text-slate-900'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="forma_pagamento"
                value="PIX"
                checked={formaPagamento === 'PIX'}
                onChange={() => setFormaPagamento('PIX')}
                className="text-slate-900 focus:ring-slate-400"
              />
              <span>Pix</span>
            </label>

            <label
              className={`flex items-center gap-2 p-2.5 border rounded-lg cursor-pointer text-sm font-medium transition-colors ${
                formaPagamento === 'CARTAO'
                  ? 'border-slate-900 bg-slate-50 text-slate-900'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="forma_pagamento"
                value="CARTAO"
                checked={formaPagamento === 'CARTAO'}
                onChange={() => setFormaPagamento('CARTAO')}
                className="text-slate-900 focus:ring-slate-400"
              />
              <span>Cartão</span>
            </label>

            <label
              className={`flex items-center gap-2 p-2.5 border rounded-lg cursor-pointer text-sm font-medium transition-colors ${
                formaPagamento === 'DINHEIRO'
                  ? 'border-slate-900 bg-slate-50 text-slate-900'
                  : 'border-slate-200 text-slate-700 hover:bg-slate-50'
              }`}
            >
              <input
                type="radio"
                name="forma_pagamento"
                value="DINHEIRO"
                checked={formaPagamento === 'DINHEIRO'}
                onChange={() => setFormaPagamento('DINHEIRO')}
                className="text-slate-900 focus:ring-slate-400"
              />
              <span>Dinheiro</span>
            </label>
          </div>
        </fieldset>

        <div className="flex justify-end gap-2 pt-2 border-t border-slate-100">
          <button
            type="button"
            onClick={onClose}
            disabled={salvando}
            className="px-4 py-2 text-sm font-medium text-slate-700 hover:bg-slate-100 rounded-lg transition-colors"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={salvando}
            className="px-4 py-2 text-sm font-medium text-white bg-slate-900 hover:bg-slate-800 rounded-lg transition-colors disabled:opacity-50"
          >
            {salvando ? 'Confirmando...' : 'Confirmar pagamento'}
          </button>
        </div>
      </form>
    </Modal>
  );
}

export default BaixaManualModal;
