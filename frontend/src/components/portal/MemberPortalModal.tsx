import { useState } from 'react';
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
  Zap 
} from 'lucide-react';

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
        className="fixed inset-0 bg-black/80 backdrop-blur-md transition-opacity"
      />

      {/* Modal Container */}
      <div className="relative w-full max-w-4xl bg-slate-950 border border-white/10 rounded-3xl shadow-2xl overflow-hidden z-10 flex flex-col max-h-[90vh]">
        {/* Modal Topbar */}
        <div className="px-6 py-4 border-b border-white/10 bg-slate-900/70 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-amber-500/10 border border-amber-500/30 flex items-center justify-center text-amber-400 font-serif font-bold">
              CM
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <span className="font-serif text-lg font-medium text-white">Portal do Associado</span>
                <span className="text-[10px] px-2 py-0.5 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 font-semibold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>ATIVO • SÓCIO #0142</span>
                </span>
              </div>
              <span className="text-xs text-slate-400">Carlos Eduardo Silva • Titular</span>
            </div>
          </div>

          <button
            onClick={onClose}
            className="p-2 rounded-xl text-slate-400 hover:text-white hover:bg-white/10 transition-colors"
          >
            <X className="w-5 h-5" />
          </button>
        </div>

        {/* Modal Navigation Tabs */}
        <div className="flex border-b border-white/10 bg-slate-900/40 px-6 gap-2 sm:gap-6 overflow-x-auto text-xs uppercase tracking-wider font-semibold">
          <button
            onClick={() => setActiveTab('carteirinha')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
              activeTab === 'carteirinha'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <User className="w-3.5 h-3.5" />
            <span>Carteirinha Digital</span>
          </button>

          <button
            onClick={() => setActiveTab('quadras')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
              activeTab === 'quadras'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Agendamento de Quadras</span>
          </button>

          <button
            onClick={() => setActiveTab('convidados')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
              activeTab === 'convidados'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
            }`}
          >
            <QrCode className="w-3.5 h-3.5" />
            <span>Convites (Cota de 8)</span>
          </button>

          <button
            onClick={() => setActiveTab('financeiro')}
            className={`py-3.5 border-b-2 transition-all flex items-center space-x-2 whitespace-nowrap ${
              activeTab === 'financeiro'
                ? 'border-amber-400 text-amber-400'
                : 'border-transparent text-slate-400 hover:text-slate-200'
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
              {/* Luxury Digital Membership Card */}
              <div className="max-w-md mx-auto rounded-3xl p-6 bg-gradient-to-tr from-slate-900 via-slate-900 to-amber-950/50 border border-amber-500/30 shadow-2xl relative overflow-hidden">
                <div className="flex items-center justify-between mb-8">
                  <div className="flex items-center space-x-2">
                    <span className="font-serif text-lg tracking-widest text-amber-300 font-semibold uppercase">Club Maravilha</span>
                  </div>
                  <span className="text-[10px] font-bold px-2.5 py-1 rounded-full bg-emerald-500/20 text-emerald-400 border border-emerald-500/30 uppercase tracking-wider">
                    Catraca Liberada
                  </span>
                </div>

                <div className="flex items-center space-x-5 mb-8">
                  <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-500 to-amber-700 flex items-center justify-center text-slate-950 font-serif font-bold text-2xl shadow-lg">
                    CE
                  </div>
                  <div>
                    <h4 className="text-lg font-bold text-white leading-tight">Carlos Eduardo Silva</h4>
                    <p className="text-xs text-slate-400 mt-1">CPF: 123.***.***-44</p>
                    <p className="text-xs text-amber-400/90 font-medium">Sócio Titular • Plano Familiar</p>
                  </div>
                </div>

                <div className="pt-4 border-t border-white/10 flex items-center justify-between text-xs text-slate-300">
                  <div>
                    <span className="block text-[10px] text-slate-400 uppercase">Validade do Acesso</span>
                    <span className="font-medium text-white">31/12/2026</span>
                  </div>
                  <div className="text-right">
                    <span className="block text-[10px] text-slate-400 uppercase">Biometria Facial</span>
                    <span className="font-medium text-emerald-400 flex items-center space-x-1 justify-end">
                      <ShieldCheck className="w-3.5 h-3.5" />
                      <span>Sincronizada</span>
                    </span>
                  </div>
                </div>
              </div>

              {/* Status Rápido */}
              <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4">
                <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Mensalidade</span>
                  <span className="text-emerald-400 font-semibold flex items-center space-x-1 text-sm">
                    <CheckCircle2 className="w-4 h-4" />
                    <span>Em Dia (Setembro)</span>
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Franquia de Convites</span>
                  <span className="text-amber-400 font-semibold text-sm">
                    {8 - emittedGuests.length} de 8 disponíveis
                  </span>
                </div>

                <div className="p-4 rounded-2xl bg-slate-900/60 border border-white/5">
                  <span className="text-xs text-slate-400 uppercase tracking-wider block mb-1">Reservas Ativas</span>
                  <span className="text-white font-semibold text-sm">
                    0 de 2 (limite simultâneo)
                  </span>
                </div>
              </div>
            </div>
          )}

          {/* TAB 2: AGENDAMENTO DE QUADRAS */}
          {activeTab === 'quadras' && (
            <div className="space-y-6">
              {bookingSuccess && (
                <div className="p-4 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm flex items-center space-x-3 animate-fade-in">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>Horário reservado com sucesso! Confirmação enviada e catraca sincronizada.</span>
                </div>
              )}

              {/* Seletor de Quadra e Data */}
              <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                <div>
                  <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2 font-medium">
                    Quadra Esportiva
                  </label>
                  <select
                    value={selectedCourt}
                    onChange={(e) => setSelectedCourt(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-400"
                  >
                    <option>Quadra de Beach Tennis 1</option>
                    <option>Quadra de Beach Tennis 2</option>
                    <option>Quadra de Tênis 1 (Saibro)</option>
                    <option>Quadra de Tênis 2 (Rápida)</option>
                    <option>Campo Society (Sintético)</option>
                  </select>
                </div>

                <div>
                  <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2 font-medium">
                    Data da Partida
                  </label>
                  <select
                    value={selectedDate}
                    onChange={(e) => setSelectedDate(e.target.value)}
                    className="w-full bg-slate-900 border border-white/10 rounded-xl px-4 py-3 text-white text-sm focus:outline-none focus:border-amber-400"
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
                <span className="block text-xs uppercase tracking-wider text-slate-400 mb-3 font-medium">
                  Grade de Horários Disponíveis (06h00 às 22h00)
                </span>
                <div className="grid grid-cols-3 sm:grid-cols-4 md:grid-cols-6 gap-2.5">
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
                        className={`py-3 px-2 rounded-xl text-xs font-semibold transition-all text-center flex flex-col items-center justify-center space-y-1 ${
                          isOccupied
                            ? 'bg-slate-900/40 text-slate-600 border border-white/5 cursor-not-allowed'
                            : isSelected
                            ? 'bg-amber-500 text-slate-950 font-bold shadow-lg shadow-amber-950/40 border border-amber-400'
                            : 'bg-slate-900/80 hover:bg-slate-800 text-slate-200 border border-white/10 hover:border-amber-400/40'
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
              <div className="pt-4 border-t border-white/10 flex items-center justify-between">
                <div className="text-xs text-slate-400">
                  {selectedSlot ? (
                    <span>Selecionado: <strong className="text-amber-400">{selectedCourt}</strong> às <strong className="text-white">{selectedSlot}</strong></span>
                  ) : (
                    <span>Selecione um horário livre na grade acima.</span>
                  )}
                </div>

                <button
                  disabled={!selectedSlot}
                  onClick={handleBookCourt}
                  className={`px-6 py-3 rounded-xl text-xs uppercase tracking-wider font-semibold transition-all ${
                    selectedSlot
                      ? 'bg-amber-500 hover:bg-amber-400 text-slate-950 shadow-lg shadow-amber-950/40'
                      : 'bg-slate-800 text-slate-500 cursor-not-allowed'
                  }`}
                >
                  Confirmar Reserva
                </button>
              </div>
            </div>
          )}

          {/* TAB 3: CONTROLE DE CONVIDADOS */}
          {activeTab === 'convidados' && (
            <div className="space-y-6">
              {guestCreatedMessage && (
                <div className="p-4 rounded-2xl bg-emerald-500/20 border border-emerald-500/30 text-emerald-300 text-xs sm:text-sm flex items-center space-x-3 animate-fade-in">
                  <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
                  <span>{guestCreatedMessage}</span>
                </div>
              )}

              {/* Quota Meter */}
              <div className="p-6 rounded-3xl bg-slate-900/80 border border-white/10">
                <div className="flex items-center justify-between mb-3">
                  <span className="text-xs uppercase tracking-widest text-amber-400 font-semibold">
                    Franquia Mensal Gratuita
                  </span>
                  <span className="text-sm font-bold text-white">
                    {emittedGuests.length} de 8 Utilizados
                  </span>
                </div>
                <div className="w-full h-3 bg-slate-800 rounded-full overflow-hidden mb-3">
                  <div 
                    className="h-full bg-gradient-to-r from-amber-500 to-emerald-400 transition-all duration-500 rounded-full"
                    style={{ width: `${(emittedGuests.length / 8) * 100}%` }}
                  />
                </div>
                <p className="text-xs text-slate-400 font-light">
                  A franquia de 8 convites gratuitos reinicia todo dia 1º de cada mês. Convites adicionais (a partir do 9º) possuem taxa de R$ 35,00 somada no próximo Pix mensal.
                </p>
              </div>

              {/* Form de Emissão de Convite */}
              <form onSubmit={handleCreateGuest} className="p-6 rounded-3xl bg-slate-900/50 border border-white/10 space-y-4">
                <span className="block text-xs uppercase tracking-wider text-white font-semibold mb-2">
                  Emitir Novo Convite com QR Code Temporário
                </span>
                <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Nome Completo do Convidado</label>
                    <input
                      type="text"
                      required
                      placeholder="Ex: Beatriz Lima"
                      value={guestName}
                      onChange={(e) => setGuestName(e.target.value)}
                      className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-amber-400"
                    />
                  </div>
                  <div>
                    <label className="block text-xs text-slate-400 mb-1">Data da Visita</label>
                    <input
                      type="date"
                      required
                      value={guestDate}
                      onChange={(e) => setGuestDate(e.target.value)}
                      className="w-full bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-white text-sm focus:outline-none focus:border-amber-400"
                    />
                  </div>
                </div>

                <div className="flex justify-end pt-2">
                  <button
                    type="submit"
                    className="px-6 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs uppercase tracking-wider shadow-lg shadow-amber-950/40 flex items-center space-x-2"
                  >
                    <Plus className="w-4 h-4" />
                    <span>Gerar QR Code do Visitante</span>
                  </button>
                </div>
              </form>

              {/* Lista de Convites Ativos */}
              <div>
                <span className="block text-xs uppercase tracking-wider text-slate-400 mb-3 font-medium">
                  Convites Emitidos Neste Mês
                </span>
                <div className="space-y-3">
                  {emittedGuests.map((guest) => (
                    <div
                      key={guest.id}
                      className="p-4 rounded-2xl bg-slate-900/60 border border-white/5 flex items-center justify-between"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-10 h-10 rounded-xl bg-slate-800 flex items-center justify-center text-amber-400">
                          <QrCode className="w-5 h-5" />
                        </div>
                        <div>
                          <span className="text-sm font-semibold text-white block">{guest.nome}</span>
                          <span className="text-xs text-slate-400">Data: {guest.data} • Token: {guest.token}</span>
                        </div>
                      </div>

                      <div className="flex items-center space-x-3">
                        <span className={`text-[10px] font-bold px-2.5 py-0.5 rounded-full ${
                          guest.status === 'EMITIDO'
                            ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                            : 'bg-slate-700/50 text-slate-400'
                        }`}>
                          {guest.status}
                        </span>
                        <button
                          type="button"
                          onClick={() => alert(`Link de acesso do QR Code copiado para envio: https://clubmaravilha.com.br/pass/${guest.token}`)}
                          className="p-2 rounded-lg bg-white/5 hover:bg-white/10 text-slate-300 hover:text-white transition-colors"
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
              <div className="p-6 rounded-3xl bg-slate-900/80 border border-white/10">
                <div className="flex items-center justify-between mb-4">
                  <div>
                    <span className="text-xs text-amber-400 uppercase tracking-widest font-semibold block">
                      Fatura Vigente
                    </span>
                    <h3 className="font-serif text-2xl text-white font-normal">
                      Mensalidade Setembro / 2026
                    </h3>
                  </div>
                  <span className={`text-xs font-bold px-3 py-1 rounded-full border ${
                    invoiceStatus === 'PAGO'
                      ? 'bg-emerald-500/20 text-emerald-400 border-emerald-500/30'
                      : 'bg-amber-500/20 text-amber-400 border-amber-500/30'
                  }`}>
                    {invoiceStatus === 'PAGO' ? 'PAGO • BAIXA REALIZADA' : 'AGUARDANDO PAGAMENTO'}
                  </span>
                </div>

                <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 pt-4 border-t border-white/10 text-xs mb-6">
                  <div>
                    <span className="text-slate-400 block">Mensalidade Base:</span>
                    <span className="text-white font-semibold text-sm">R$ 150,00</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Convidados Excedentes:</span>
                    <span className="text-white font-semibold text-sm">R$ 0,00 (0 excedentes)</span>
                  </div>
                  <div>
                    <span className="text-slate-400 block">Valor Total:</span>
                    <span className="text-amber-400 font-bold text-base">R$ 150,00</span>
                  </div>
                </div>

                {invoiceStatus === 'PENDENTE' ? (
                  <div className="space-y-4">
                    {/* Pix Copia e Cola */}
                    <div>
                      <label className="block text-xs uppercase tracking-wider text-slate-400 mb-2 font-medium">
                        Pix Copia e Cola (Liquidação Instantânea em 2s)
                      </label>
                      <div className="flex items-center space-x-2">
                        <input
                          readOnly
                          value={pixCode}
                          className="flex-1 bg-slate-950 border border-white/10 rounded-xl px-4 py-2.5 text-xs text-slate-300 font-mono focus:outline-none"
                        />
                        <button
                          onClick={handleCopyPix}
                          className="px-5 py-2.5 rounded-xl bg-amber-500 hover:bg-amber-400 text-slate-950 font-semibold text-xs uppercase tracking-wider flex items-center space-x-1.5 shadow-lg shadow-amber-950/40"
                        >
                          <Copy className="w-3.5 h-3.5" />
                          <span>{copiedPix ? 'Copiado!' : 'Copiar'}</span>
                        </button>
                      </div>
                    </div>

                    {/* Simulação de Webhook (2s) para o Usuário Testar */}
                    <div className="p-4 rounded-2xl bg-amber-500/10 border border-amber-500/20 flex flex-col sm:flex-row items-center justify-between gap-4">
                      <div className="flex items-center space-x-3 text-xs text-amber-200">
                        <Zap className="w-5 h-5 text-amber-400 shrink-0" />
                        <span>Simule o disparo do Webhook Pix para testar a baixa automática em 2 segundos sem leitura manual de comprovante.</span>
                      </div>
                      <button
                        disabled={simulatingWebhook}
                        onClick={handleSimulateWebhook}
                        className="w-full sm:w-auto px-5 py-2.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white font-bold text-xs uppercase tracking-wider shadow-lg shadow-emerald-950/40 whitespace-nowrap flex items-center justify-center space-x-1.5"
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
                  <div className="p-6 rounded-2xl bg-emerald-500/10 border border-emerald-500/20 text-center space-y-2">
                    <CheckCircle2 className="w-8 h-8 text-emerald-400 mx-auto" />
                    <h4 className="text-base font-bold text-white">Pagamento Confirmado via Webhook!</h4>
                    <p className="text-xs text-slate-300 max-w-md mx-auto">
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
