import React, { useState } from 'react';
import { 
  X, 
  User, 
  Calendar, 
  QrCode, 
  CreditCard, 
  ShieldCheck, 
  CheckCircle2, 
  Copy, 
  Clock, 
  Plus, 
  Send, 
  Zap,
  Users
} from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';

interface MemberPortalModalProps {
  isOpen: boolean;
  onClose: () => void;
  preSelectedCourt?: string;
}

export const MemberPortalModal: React.FC<MemberPortalModalProps> = ({
  isOpen,
  onClose,
  preSelectedCourt
}) => {
  const [activeTab, setActiveTab] = useState<'carteirinha' | 'quadras' | 'convidados' | 'financeiro'>('carteirinha');
  
  // Quadras State
  const [selectedCourt, setSelectedCourt] = useState(preSelectedCourt || 'Quadra de Beach Tennis 1');
  const [selectedDate, setSelectedDate] = useState('Hoje (10/09)');
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [bookingSuccess, setBookingSuccess] = useState(false);

  // Convidados State
  const [guestName, setGuestName] = useState('');
  const [guestDate, setGuestDate] = useState('2026-09-15');
  const [emittedGuests, setEmittedGuests] = useState([
    { id: '1', nome: 'Mariana Duarte', data: '12/09/2026', status: 'EMITIDO', gratuito: true, token: 'cm_guest_9f83a2' },
    { id: '2', nome: 'Rodrigo Albuquerque', data: '05/09/2026', status: 'UTILIZADO', gratuito: true, token: 'cm_guest_4b71c8' },
  ]);
  const [guestCreatedMessage, setGuestCreatedMessage] = useState<string | null>(null);

  // Financeiro / Pix State
  const [invoiceStatus, setInvoiceStatus] = useState<'PENDENTE' | 'PAGO'>('PENDENTE');
  const [copiedPix, setCopiedPix] = useState(false);
  const [simulatingWebhook, setSimulatingWebhook] = useState(false);

  const pixCode = "00020101021226830014br.gov.bcb.pix2561pix.clubmaravilha.com.br/qr/v2/cobv/9a8f7c6d5e4b3a215204000053039865406150.005802BR5920CLUB MARAVILHA GESTAO6009SAO PAULO62070503***6304E8A1";

  if (!isOpen) return null;

  const handleBookCourt = () => {
    if (!selectedSlot) return;
    setBookingSuccess(true);
    setTimeout(() => {
      setBookingSuccess(false);
      setSelectedSlot(null);
    }, 4000);
  };

  const handleCreateGuest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!guestName.trim()) return;

    const newGuest = {
      id: String(Date.now()),
      nome: guestName,
      data: guestDate,
      status: 'EMITIDO',
      gratuito: emittedGuests.length < 8,
      token: `cm_qr_${Math.random().toString(36).substring(2, 8)}`
    };

    setEmittedGuests([newGuest, ...emittedGuests]);
    setGuestCreatedMessage(`Convite gerado com sucesso para ${guestName}! QR Code pronto para envio.`);
    setGuestName('');
    setTimeout(() => setGuestCreatedMessage(null), 5000);
  };

  const handleCopyPix = () => {
    navigator.clipboard.writeText(pixCode);
    setCopiedPix(true);
    setTimeout(() => setCopiedPix(false), 3000);
  };

  const handleSimulateWebhook = () => {
    setSimulatingWebhook(true);
    setTimeout(() => {
      setInvoiceStatus('PAGO');
      setSimulatingWebhook(false);
    }, 2000);
  };

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center p-4 sm:p-6 overflow-y-auto">
      {/* Backdrop */}
      <div 
        onClick={onClose}
        className="fixed inset-0 bg-slate-900/60 backdrop-blur-xs transition-opacity"
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-4xl bg-[#F8FAFC] border border-slate-200/90 rounded-3xl shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]">
        {/* Modal Topbar */}
        <div className="px-6 py-4 border-b border-slate-200 bg-white flex items-center justify-between">
          <div className="flex items-center space-x-3.5">
            <ClubeMaravilhaLogo variant="default" size="sm" />
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-bold text-base sm:text-lg text-[#1B3B54] font-sans">
                  Portal do Associado
                </span>
                <span className="text-[11px] px-2.5 py-0.5 rounded-full bg-emerald-50 text-emerald-700 border border-emerald-200 font-bold flex items-center space-x-1.5">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>ATIVO • #2026-0042</span>
                </span>
              </div>
              <span className="text-xs text-slate-500 font-medium">Schaide Nunes • Sócio Titular Ouro</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-[#1B3B54] hover:bg-slate-100 transition-colors cursor-pointer"
            aria-label="Fechar modal"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-slate-200 bg-white px-6 gap-2 sm:gap-6 overflow-x-auto text-xs uppercase tracking-wider font-bold">
          <button
            onClick={() => setActiveTab('carteirinha')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'carteirinha'
                ? 'border-[#1B3B54] text-[#1B3B54]'
                : 'border-transparent text-slate-500 hover:text-[#1B3B54]'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Carteirinha Digital</span>
          </button>

          <button
            onClick={() => setActiveTab('quadras')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'quadras'
                ? 'border-[#1B3B54] text-[#1B3B54]'
                : 'border-transparent text-slate-500 hover:text-[#1B3B54]'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Agendamento de Quadras</span>
          </button>

          <button
            onClick={() => setActiveTab('convidados')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'convidados'
                ? 'border-[#1B3B54] text-[#1B3B54]'
                : 'border-transparent text-slate-500 hover:text-[#1B3B54]'
            }`}
          >
            <QrCode className="w-3.5 h-3.5" />
            <span>Convites (Cota de 8)</span>
          </button>

          <button
            onClick={() => setActiveTab('financeiro')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap cursor-pointer ${
              activeTab === 'financeiro'
                ? 'border-[#1B3B54] text-[#1B3B54]'
                : 'border-transparent text-slate-500 hover:text-[#1B3B54]'
            }`}
          >
            <CreditCard className="w-3.5 h-3.5" />
            <span>Mensalidade & Pix 2s</span>
          </button>
        </div>

        {/* Modal Tab Contents */}
        <div className="p-6 overflow-y-auto flex-1 space-y-6">
          {/* TAB 1: CARTEIRINHA DIGITAL */}
          {activeTab === 'carteirinha' && (
            <div className="space-y-6">
              {/* Carteirinha Digital Oficial (Paleta Limpa do Clube) */}
              <div className="max-w-md mx-auto rounded-3xl p-6 bg-[#1B3B54] text-white shadow-lg border border-[#2B5475] relative">
                {/* Topbar da Carteirinha */}
                <div className="flex items-center justify-between pb-5 border-b border-white/15">
                  <div className="flex items-center space-x-2">
                    <div className="w-8 h-8 rounded-lg bg-amber-400 text-[#1B3B54] font-black text-xs flex items-center justify-center shadow-xs">
                      CM
                    </div>
                    <div>
                      <h4 className="font-bold text-sm tracking-wider uppercase text-white leading-none">
                        Clube Maravilha
                      </h4>
                      <span className="text-[10px] text-slate-300">Teofilândia • Bahia</span>
                    </div>
                  </div>
                  <span className="text-[11px] font-bold px-3 py-1 rounded-full bg-emerald-500/20 text-emerald-300 border border-emerald-400/30 uppercase tracking-wider">
                    Catraca Liberada
                  </span>
                </div>

                {/* Dados do Sócio */}
                <div className="py-5 flex items-center space-x-4">
                  <div className="w-16 h-16 rounded-2xl bg-amber-400 text-[#1B3B54] flex flex-col items-center justify-center font-black shadow-md shrink-0">
                    <span className="text-xl">SN</span>
                    <span className="text-[8px] uppercase tracking-tighter text-[#1B3B54]/80">TITULAR</span>
                  </div>
                  <div className="min-w-0">
                    <span className="text-[10px] font-bold uppercase tracking-widest text-amber-300 block mb-0.5">
                      Sócio Titular Ouro
                    </span>
                    <h3 className="text-lg font-black text-white leading-tight truncate">
                      Schaide Nunes
                    </h3>
                    <p className="text-xs text-slate-300 mt-0.5">
                      CPF: <span className="font-mono">123.456.789-00</span>
                    </p>
                    <div className="mt-1.5 inline-flex items-center space-x-1 px-2 py-0.5 rounded-md bg-white/10 text-white/90 text-[11px] font-medium">
                      <Users className="w-3 h-3 text-amber-300" />
                      <span>Plano Ouro Familiar • 4 Vidas</span>
                    </div>
                  </div>
                </div>

                {/* Rodapé da Carteirinha */}
                <div className="pt-4 border-t border-white/15 flex items-center justify-between text-xs text-slate-300">
                  <div className="space-y-1">
                    <div>
                      <span className="block text-[10px] text-slate-300 uppercase">Matrícula</span>
                      <span className="font-mono font-bold text-white text-sm">#2026-0042</span>
                    </div>
                    <div>
                      <span className="block text-[10px] text-slate-300 uppercase">Validade</span>
                      <span className="font-medium text-white">31/12/2026</span>
                    </div>
                  </div>

                  <div className="flex flex-col items-center">
                    <div className="p-2 bg-white rounded-xl shadow-xs">
                      <QrCode className="w-12 h-12 text-[#1B3B54]" />
                    </div>
                    <span className="text-[10px] text-emerald-300 font-semibold flex items-center space-x-1 mt-1">
                      <ShieldCheck className="w-3 h-3" />
                      <span>Biometria Facial</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Rápido em Cards Claros e Refinados */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-2">
                <div className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs">
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1.5">
                    Mensalidade
                  </span>
                  <span className="inline-flex items-center space-x-1.5 text-xs font-bold text-emerald-800 bg-emerald-50 px-2.5 py-1 rounded-full border border-emerald-200">
                    <CheckCircle2 className="w-3.5 h-3.5 text-emerald-600" />
                    <span>Em Dia (Setembro)</span>
                  </span>
                </div>

                <div className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs">
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1.5">
                    Franquia de Convites
                  </span>
                  <span className="text-base font-bold text-[#1B3B54] block">
                    {8 - emittedGuests.length} de 8 disponíveis
                  </span>
                  <span className="text-[11px] text-slate-400 mt-0.5 block">
                    Reinicia dia 1º do mês
                  </span>
                </div>

                <div className="p-5 rounded-2xl bg-white border border-slate-200/90 shadow-xs">
                  <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block mb-1.5">
                    Reservas Ativas
                  </span>
                  <span className="text-base font-bold text-[#1B3B54] block">
                    0 de 2 simultâneas
                  </span>
                  <span className="text-[11px] text-slate-400 mt-0.5 block">
                    Limite por titular
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: AGENDAMENTO DE QUADRAS */}
          {activeTab === 'quadras' && (
            <div className="space-y-6">
              {bookingSuccess && (
                <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs sm:text-sm flex items-center space-x-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span className="font-semibold">Horário reservado com sucesso! Confirmação enviada e catraca sincronizada.</span>
                </div>
              )}

              {/* Seletor de Quadra e Data em Card Branco */}
              <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-6">
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-600 mb-2 font-bold">
                      Quadra Esportiva
                    </label>
                    <select
                      value={selectedCourt}
                      onChange={(e) => setSelectedCourt(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-[#1B3B54] text-sm focus:outline-none focus:border-[#4E7A9C]"
                    >
                      <option>Quadra de Beach Tennis 1</option>
                      <option>Quadra de Beach Tennis 2</option>
                      <option>Quadra de Tênis 1 (Saibro)</option>
                      <option>Quadra de Tênis 2 (Rápida)</option>
                      <option>Campo Society (Sintético)</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-xs uppercase tracking-wider text-slate-600 mb-2 font-bold">
                      Data da Partida
                    </label>
                    <select
                      value={selectedDate}
                      onChange={(e) => setSelectedDate(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-[#1B3B54] text-sm focus:outline-none focus:border-[#4E7A9C]"
                    >
                      <option>Hoje (10/09)</option>
                      <option>Amanhã (11/09)</option>
                      <option>Sábado (12/09)</option>
                      <option>Domingo (13/09)</option>
                    </select>
                  </div>
                </div>

                {/* Grade de Horários */}
                <div>
                  <span className="block text-xs uppercase tracking-wider text-slate-600 mb-3 font-bold">
                    Grade de Horários Disponíveis (06h00 às 22h00)
                  </span>
                  <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-7 gap-2.5">
                    {[
                      { slot: '06:00 - 07:00', status: 'disponivel' },
                      { slot: '07:00 - 08:00', status: 'ocupado' },
                      { slot: '08:00 - 09:00', status: 'disponivel' },
                      { slot: '09:00 - 10:00', status: 'ocupado' },
                      { slot: '10:00 - 11:00', status: 'disponivel' },
                      { slot: '11:00 - 12:00', status: 'disponivel' },
                      { slot: '14:00 - 15:00', status: 'disponivel' },
                      { slot: '15:00 - 16:00', status: 'disponivel' },
                      { slot: '16:00 - 17:00', status: 'ocupado' },
                      { slot: '17:00 - 18:00', status: 'disponivel' },
                      { slot: '18:00 - 19:00', status: 'ocupado' },
                      { slot: '19:00 - 20:00', status: 'disponivel' },
                      { slot: '20:00 - 21:00', status: 'disponivel' },
                      { slot: '21:00 - 22:00', status: 'disponivel' },
                    ].map((item, idx) => {
                      const isSelected = selectedSlot === item.slot;
                      const isOccupied = item.status === 'ocupado';

                      return (
                        <button
                          key={idx}
                          disabled={isOccupied}
                          onClick={() => setSelectedSlot(item.slot)}
                          className={`py-2.5 px-2 rounded-xl text-xs font-semibold transition-all text-center flex flex-col items-center justify-center space-y-1 cursor-pointer ${
                            isOccupied
                              ? 'bg-slate-100 text-slate-400 border border-slate-200 cursor-not-allowed'
                              : isSelected
                              ? 'bg-[#1B3B54] text-white font-bold shadow-xs border border-[#1B3B54]'
                              : 'bg-white hover:bg-slate-50 text-[#1B3B54] border border-slate-200/90 hover:border-[#1B3B54]'
                          }`}
                        >
                          <span>{item.slot}</span>
                          <span className="text-[10px] font-normal opacity-80">
                            {isOccupied ? 'Ocupado' : isSelected ? 'Selecionado' : 'Livre'}
                          </span>
                        </button>
                      );
                    })}
                  </div>
                </div>

                {/* Botão de Confirmação de Agendamento */}
                <div className="pt-4 border-t border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                  <div className="text-xs text-slate-500">
                    {selectedSlot ? (
                      <span>Selecionado: <strong className="text-[#1B3B54] font-bold">{selectedCourt}</strong> às <strong className="text-[#1B3B54] font-bold">{selectedSlot}</strong></span>
                    ) : (
                      <span>Selecione um horário livre na grade acima.</span>
                    )}
                  </div>

                  <button
                    disabled={!selectedSlot}
                    onClick={handleBookCourt}
                    className={`w-full sm:w-auto px-6 py-2.5 rounded-xl text-xs uppercase tracking-wider font-bold transition-all cursor-pointer ${
                      selectedSlot
                        ? 'bg-[#1F3347] hover:bg-[#162737] text-white shadow-md'
                        : 'bg-slate-200 text-slate-400 cursor-not-allowed'
                    }`}
                  >
                    Confirmar Reserva
                  </button>
                </div>
              </div>
            </div>
          )}

          {/* TAB 3: CONTROLE DE CONVIDADOS */}
          {activeTab === 'convidados' && (
            <div className="space-y-6">
              {guestCreatedMessage && (
                <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 text-xs sm:text-sm flex items-center space-x-3">
                  <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
                  <span className="font-semibold">{guestCreatedMessage}</span>
                </div>
              )}

              {/* Quota Meter */}
              <div className="p-6 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-3">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase tracking-wider text-slate-500 font-bold">
                    Franquia Mensal Gratuita
                  </span>
                  <span className="text-sm font-bold text-[#1B3B54]">
                    {emittedGuests.length} de 8 Utilizados
                  </span>
                </div>
                <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
                  <div 
                    className="h-full bg-[#4E7A9C] transition-all duration-500 rounded-full"
                    style={{ width: `${(emittedGuests.length / 8) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-slate-500">
                  A franquia de 8 convites gratuitos reinicia todo dia 1º de cada mês. Convites adicionais (a partir do 9º) possuem taxa de R$ 35,00 somada no próximo Pix mensal.
                </p>
              </div>

              {/* Form de Emissão de Convite */}
              <form onSubmit={handleCreateGuest} className="p-6 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-4">
                <span className="block text-xs uppercase tracking-wider text-[#1B3B54] font-bold">
                  Emitir Novo Convite com QR Code Temporário
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-600 mb-1 font-semibold">Nome Completo do Convidado</label>
                    <input
                      type="text"
                      required
                      placeholder="Ex: Beatriz Lima"
                      value={guestName}
                      onChange={(e) => setGuestName(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-[#1B3B54] text-sm focus:outline-none focus:border-[#4E7A9C]"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-600 mb-1 font-semibold">Data da Visita</label>
                    <input
                      type="date"
                      required
                      value={guestDate}
                      onChange={(e) => setGuestDate(e.target.value)}
                      className="w-full bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-[#1B3B54] text-sm focus:outline-none focus:border-[#4E7A9C]"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="px-6 py-2.5 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-xs uppercase tracking-wider shadow-md flex items-center space-x-2 cursor-pointer"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Gerar QR Code do Visitante</span>
                  </button>
                </div>
              </form>

              {/* Lista de Convites Ativos */}
              <div>
                <span className="block text-xs uppercase tracking-wider text-slate-600 mb-3 font-bold">
                  Convites Emitidos Neste Mês
                </span>
                <div className="space-y-3">
                  {emittedGuests.map((guest) => (
                    <div
                      key={guest.id}
                      className="p-4 rounded-xl bg-white border border-slate-200/90 shadow-xs flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-xl bg-[#EBF4FA] text-[#1B3B54] flex items-center justify-center">
                          <QrCode className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-sm font-bold text-[#1B3B54] block">{guest.nome}</span>
                          <span className="text-xs text-slate-500">Data: {guest.data} • Token: {guest.token}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                          guest.status === 'EMITIDO'
                            ? 'bg-emerald-50 text-emerald-700 border border-emerald-200'
                            : 'bg-slate-100 text-slate-500'
                        }`}>
                          {guest.status}
                        </span>
                        <button
                          type="button"
                          onClick={() => alert(`Link de acesso do QR Code copiado para envio: https://clubmaravilha.com.br/pass/${guest.token}`)}
                          className="p-2 rounded-lg bg-slate-100 hover:bg-slate-200 text-slate-600 hover:text-[#1B3B54] transition-colors cursor-pointer"
                          title="Compartilhar QR Code"
                        >
                          <Send className="w-3.5 h-3.5" />
                        </button>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </div>
          )}

          {/* TAB 4: MENSALIDADE & PIX INSTANTÂNEO */}
          {activeTab === 'financeiro' && (
            <div className="space-y-6">
              {/* Fatura Card */}
              <div className="p-6 rounded-2xl bg-white border border-slate-200/90 shadow-xs space-y-6">
                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                  <div>
                    <span className="text-xs text-slate-500 uppercase tracking-wider font-bold block">
                      Fatura Vigente
                    </span>
                    <h3 className="text-xl font-black text-[#1B3B54]">
                      Mensalidade Setembro / 2026
                    </h3>
                  </div>
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border self-start sm:self-auto ${
                    invoiceStatus === 'PAGO'
                      ? 'bg-emerald-50 text-emerald-800 border-emerald-300'
                      : 'bg-amber-50 text-amber-800 border-amber-300'
                  }`}>
                    {invoiceStatus === 'PAGO' ? 'PAGO • BAIXA REALIZADA' : 'AGUARDANDO PAGAMENTO'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-slate-200 text-xs">
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-0.5">Mensalidade Base:</span>
                    <span className="text-[#1B3B54] font-bold text-sm">R$ 150,00</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-slate-50 border border-slate-200">
                    <span className="text-slate-500 block mb-0.5">Convidados Excedentes:</span>
                    <span className="text-[#1B3B54] font-bold text-sm">R$ 0,00 (0 excedentes)</span>
                  </div>
                  <div className="p-3.5 rounded-xl bg-[#EBF4FA] border border-[#BFDBFE]">
                    <span className="text-[#24537A] font-semibold block mb-0.5">Valor Total:</span>
                    <span className="text-[#1B3B54] font-black text-base">R$ 150,00</span>
                  </div>
                </div>

                {invoiceStatus === 'PENDENTE' ? (
                  <div className="space-y-4 pt-2">
                    {/* Pix Copia e Cola */}
                    <div>
                      <label className="block text-xs uppercase tracking-wider text-slate-600 mb-2 font-bold">
                        Pix Copia e Cola (Liquidação Instantânea em 2s)
                      </label>
                      <div className="flex items-center space-x-2">
                        <input
                          readOnly
                          value={pixCode}
                          className="flex-1 bg-slate-50 border border-slate-300 rounded-xl px-4 py-2.5 text-xs text-slate-700 font-mono focus:outline-none"
                        />
                        <button
                          onClick={handleCopyPix}
                          className="px-5 py-2.5 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-xs uppercase tracking-wider flex items-center space-x-1.5 shadow-sm cursor-pointer shrink-0"
                        >
                          <Copy className="w-3.5 h-3.5" />
                          <span>{copiedPix ? 'Copiado!' : 'Copiar'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Simulação de Webhook (2s) para o Usuário Testar */}
                    <div className="p-4 rounded-xl bg-slate-50 border border-slate-200 flex flex-col sm:flex-row items-center justify-between gap-4">
                      <div className="flex items-center space-x-3 text-xs text-slate-600">
                        <Zap className="w-5 h-5 text-amber-500 shrink-0" />
                        <span>Simule o disparo do Webhook Pix para testar a baixa automática em 2 segundos sem conferência manual.</span>
                      </div>
                      <button
                        disabled={simulatingWebhook}
                        onClick={handleSimulateWebhook}
                        className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs uppercase tracking-wider shadow-sm whitespace-nowrap flex items-center justify-center space-x-1.5 cursor-pointer"
                      >
                        {simulatingWebhook ? (
                          <>
                            <Clock className="w-3.5 h-3.5 animate-spin" />
                            <span>Processando Webhook (2s)...</span>
                          </>
                        ) : (
                          <span>Simular Pagamento Instantâneo</span>
                        )}
                      </button>
                    </div>
                  </div>
                ) : (
                  <div className="p-6 rounded-2xl bg-emerald-50 border border-emerald-200 text-center space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-600 mx-auto" />
                    <h4 className="text-base font-bold text-emerald-900">Pagamento Confirmado via Webhook!</h4>
                    <p className="text-xs text-emerald-700 max-w-md mx-auto">
                      A fatura foi quitada em 2.1 segundos. O recibo automático foi emitido e sua biometria facial na catraca permanece 100% liberada.
                    </p>
                  </div>
                )}
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  );
};
