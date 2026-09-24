import React, { useState } from 'react';
import {
  CreditCard,
  QrCode,
  Copy,
  CheckCircle2,
  Clock,
  Download,
  Zap,
  Receipt,
  FileCheck
} from 'lucide-react';

export const UserFinanceiroTab: React.FC = () => {
  const [copiedPix, setCopiedPix] = useState(false);
  const [invoiceStatus, setInvoiceStatus] = useState<'PENDENTE' | 'PAGO'>('PENDENTE');
  const [isSimulating, setIsSimulating] = useState(false);

  const pixCode =
    '00020101021226830014br.gov.bcb.pix2561pix.clubmaravilha.com.br/qr/v2/cobv/9a8f7c6d5e4b3a215204000053039865406150.005802BR5920CLUB MARAVILHA GESTAO6009SAO PAULO62070503***6304E8A1';

  const handleCopyPix = () => {
    navigator.clipboard.writeText(pixCode);
    setCopiedPix(true);
    setTimeout(() => setCopiedPix(false), 3000);
  };

  const handleSimulatePayment = () => {
    setIsSimulating(true);
    setTimeout(() => {
      setInvoiceStatus('PAGO');
      setIsSimulating(false);
    }, 1800);
  };

  const pastInvoices = [
    {
      mes: 'Setembro / 2026',
      valor: 'R$ 150,00',
      vencimento: '12/09/2026',
      pagamento: '10/09/2026 às 14:22',
      forma: 'Pix Instantâneo',
      status: 'PAGO',
      txid: 'CM-202609-23A2B61A'
    },
    {
      mes: 'Agosto / 2026',
      valor: 'R$ 150,00',
      vencimento: '12/08/2026',
      pagamento: '11/08/2026 às 09:15',
      forma: 'Pix Instantâneo',
      status: 'PAGO',
      txid: 'CM-202608-88D149C2'
    },
    {
      mes: 'Julho / 2026',
      valor: 'R$ 150,00',
      vencimento: '12/07/2026',
      pagamento: '12/07/2026 às 18:40',
      forma: 'Pix Instantâneo',
      status: 'PAGO',
      txid: 'CM-202607-12F980A1'
    }
  ];

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Financeiro Integrado</span>
          <span>•</span>
          <span>Pix & Baixa Automática</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Mensalidades & Pagamentos
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Acompanhe suas faturas, gere o Pix com liquidação em 2 segundos e consulte seus comprovantes.
        </p>
      </div>

      {/* Card da Fatura Atual */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <div className="flex flex-col md:flex-row md:items-center justify-between gap-4 pb-6 border-b border-slate-100">
          <div>
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
                <CreditCard className="w-5 h-5" />
              </div>
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
                  Fatura Atual
                </span>
                <h2 className="text-xl font-black text-[#1B3B54]">
                  Mensalidade Outubro / 2026
                </h2>
              </div>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            {invoiceStatus === 'PAGO' ? (
              <span className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-full bg-emerald-100 border border-emerald-300 text-emerald-800 text-sm font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>PAGO COM PIX</span>
              </span>
            ) : (
              <span className="inline-flex items-center space-x-1.5 px-4 py-2 rounded-full bg-amber-100 border border-amber-300 text-amber-800 text-sm font-bold">
                <Clock className="w-4 h-4 text-amber-600 animate-pulse" />
                <span>AGUARDANDO PAGAMENTO</span>
              </span>
            )}
          </div>
        </div>

        {/* Detalhamento de Valores */}
        <div className="py-6 grid grid-cols-1 sm:grid-cols-3 gap-6">
          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="text-xs text-slate-400 block mb-1">Vencimento</span>
            <span className="text-lg font-bold text-[#1B3B54]">12 de Outubro de 2026</span>
          </div>

          <div className="p-4 rounded-2xl bg-slate-50 border border-slate-100">
            <span className="text-xs text-slate-400 block mb-1">Plano do Titular</span>
            <span className="text-lg font-bold text-[#1B3B54]">Sócio Ouro Familiar</span>
          </div>

          <div className="p-4 rounded-2xl bg-[#EBF4FA] border border-[#BFDBFE]">
            <span className="text-xs text-[#24537A] font-semibold block mb-1">Valor Total</span>
            <span className="text-2xl font-black text-[#1B3B54]">R$ 150,00</span>
          </div>
        </div>

        {/* Bloco de Pagamento Pix (se Pendente) ou Recibo (se Pago) */}
        {invoiceStatus === 'PENDENTE' ? (
          <div className="mt-4 p-6 rounded-2xl bg-slate-50 border border-slate-200 text-[#1B3B54] space-y-6">
            <div className="flex items-center justify-between">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-lg bg-[#EBF4FA] text-[#1B3B54] flex items-center justify-center font-bold text-xs">
                  PIX
                </div>
                <h3 className="font-bold text-base text-[#1B3B54]">
                  Pague com Pix Instantâneo (Liquidação em 2 segundos)
                </h3>
              </div>
              <span className="text-xs text-emerald-700 font-semibold hidden sm:inline">
                ● Catraca liberada na hora
              </span>
            </div>

            <div className="grid grid-cols-1 md:grid-cols-12 gap-6 items-center">
              {/* QR Code Container */}
              <div className="md:col-span-4 flex flex-col items-center p-4 bg-white rounded-2xl border border-slate-200 shadow-xs text-slate-900">
                <QrCode className="w-36 h-36 text-[#1B3B54]" />
                <span className="text-[11px] font-mono font-bold text-slate-600 mt-2">
                  TXID: CM-202610-8491
                </span>
                <span className="text-[10px] text-slate-400">Escaneie com qualquer app de banco</span>
              </div>

              {/* Copia e Cola & Simulação */}
              <div className="md:col-span-8 space-y-4">
                <div>
                  <label className="text-xs text-slate-600 font-bold block mb-1.5 uppercase tracking-wider">
                    Código Pix Copia e Cola:
                  </label>
                  <div className="flex items-center space-x-2">
                    <input
                      type="text"
                      readOnly
                      value={pixCode}
                      className="w-full bg-white border border-slate-300 rounded-xl px-3.5 py-2.5 text-xs text-slate-700 font-mono focus:outline-none focus:border-[#4E7A9C]"
                    />
                    <button
                      onClick={handleCopyPix}
                      className="px-4 py-2.5 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-xs flex items-center space-x-1.5 shadow-sm transition-colors cursor-pointer shrink-0"
                    >
                      <Copy className="w-3.5 h-3.5" />
                      <span>{copiedPix ? 'Copiado!' : 'Copiar'}</span>
                    </button>
                  </div>
                </div>

                {/* Botão de Demonstração em Reunião */}
                <div className="pt-2">
                  <div className="text-[11px] text-slate-500 mb-2 font-medium">
                    ⚡ Funcionalidade para Apresentação em Reunião:
                  </div>
                  <button
                    onClick={handleSimulatePayment}
                    disabled={isSimulating}
                    className="w-full py-3 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-sm flex items-center justify-center space-x-2 shadow-sm transition-all cursor-pointer"
                  >
                    {isSimulating ? (
                      <>
                        <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin"></div>
                        <span>Processando Webhook do Banco Central...</span>
                      </>
                    ) : (
                      <>
                        <Zap className="w-4 h-4 text-amber-300" />
                        <span>Simular Pagamento Pix Instantâneo (2s)</span>
                      </>
                    )}
                  </button>
                  <p className="text-[11px] text-slate-500 mt-2 text-center">
                    Ao receber o Pix, o sistema emite o recibo no WhatsApp e libera o associado na catraca em 0.3s.
                  </p>
                </div>
              </div>
            </div>
          </div>
        ) : (
          <div className="mt-4 p-6 rounded-2xl bg-emerald-50 border border-emerald-200 text-emerald-950 space-y-4 animate-in fade-in">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-emerald-100 text-emerald-700 flex items-center justify-center">
                <FileCheck className="w-6 h-6" />
              </div>
              <div>
                <h3 className="font-bold text-emerald-900 text-base">
                  Fatura Liquidada com Sucesso!
                </h3>
                <p className="text-xs text-emerald-700">
                  Pagamento confirmado via Pix • Autenticação Bancária: CM-202610-8491-BACEN
                </p>
              </div>
            </div>

            <div className="p-4 rounded-xl bg-white border border-emerald-200 text-xs space-y-2 font-mono text-slate-700">
              <div className="flex justify-between">
                <span>Data/Hora da Quitação:</span>
                <span className="font-bold text-[#1B3B54]">Hoje às 21:05 (Instantâneo)</span>
              </div>
              <div className="flex justify-between">
                <span>Notificação WhatsApp:</span>
                <span className="font-bold text-emerald-700">Enviada com sucesso para (75) 98328-5614</span>
              </div>
              <div className="flex justify-between">
                <span>Status Catraca Facial:</span>
                <span className="font-bold text-emerald-700">LIBERADA SEM RESTRIÇÕES</span>
              </div>
            </div>

            <div className="flex justify-end pt-2">
              <button
                onClick={() => setInvoiceStatus('PENDENTE')}
                className="text-xs text-slate-500 hover:text-[#1B3B54] underline cursor-pointer"
              >
                Resetar demonstração para 'Pendente'
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Histórico de Faturas Anteriores */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-8">
        <div className="flex items-center justify-between mb-6">
          <div className="flex items-center space-x-3">
            <Receipt className="w-5 h-5 text-[#1B3B54]" />
            <h3 className="font-bold text-[#1B3B54] text-lg">
              Histórico de Mensalidades
            </h3>
          </div>
          <span className="text-xs text-slate-500">Últimos 3 meses</span>
        </div>

        <div className="overflow-x-auto">
          <table className="w-full text-left text-sm">
            <thead>
              <tr className="border-b border-slate-200 text-xs font-bold text-slate-400 uppercase tracking-wider">
                <th className="py-3 px-4">Mês de Referência</th>
                <th className="py-3 px-4">Valor</th>
                <th className="py-3 px-4">Data Pagamento</th>
                <th className="py-3 px-4">Forma</th>
                <th className="py-3 px-4">Status</th>
                <th className="py-3 px-4 text-right">Comprovante</th>
              </tr>
            </thead>
            <tbody className="divide-y divide-slate-100">
              {pastInvoices.map((inv, idx) => (
                <tr key={idx} className="hover:bg-slate-50/80 transition-colors">
                  <td className="py-4 px-4 font-bold text-[#1B3B54]">{inv.mes}</td>
                  <td className="py-4 px-4 font-semibold text-slate-700">{inv.valor}</td>
                  <td className="py-4 px-4 text-xs text-slate-500">{inv.pagamento}</td>
                  <td className="py-4 px-4 text-xs font-medium text-slate-600">{inv.forma}</td>
                  <td className="py-4 px-4">
                    <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-xs font-bold">
                      <CheckCircle2 className="w-3 h-3 text-emerald-600" />
                      <span>{inv.status}</span>
                    </span>
                  </td>
                  <td className="py-4 px-4 text-right">
                    <button
                      onClick={() => alert(`Comprovante Digital Autenticado:\n\nRecibo: ${inv.txid}\nAssociado: Schaide Nunes\nValor: ${inv.valor}\nData: ${inv.pagamento}\nStatus: PAGO`)}
                      className="inline-flex items-center space-x-1 text-xs font-bold text-[#4E7A9C] hover:text-[#1B3B54] transition-colors cursor-pointer"
                    >
                      <Download className="w-3.5 h-3.5" />
                      <span>Recibo PDF</span>
                    </button>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
};
