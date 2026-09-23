import React, { useState } from 'react';
import {
  Calendar,
  CheckCircle2,
  Trash2,
  BookmarkCheck
} from 'lucide-react';

interface Booking {
  id: string;
  court: string;
  date: string;
  time: string;
  status: string;
  token: string;
}

export const UserReservasTab: React.FC = () => {
  const courts = [
    {
      id: 'bt1',
      name: 'Quadra Beach Tennis 1',
      type: 'Areia Iluminada',
      badge: 'Beach Tennis / Vôlei de Praia'
    },
    {
      id: 'bt2',
      name: 'Quadra Beach Tennis 2',
      type: 'Areia Iluminada',
      badge: 'Beach Tennis / Futevôlei'
    },
    {
      id: 'soc1',
      name: 'Campo Society de Futebol',
      type: 'Grama Sintética FIFA',
      badge: 'Futebol Society 7x7'
    },
    {
      id: 'pol1',
      name: 'Quadra Poliesportiva Coberta',
      type: 'Piso Modular Flutuante',
      badge: 'Futsal / Basquete / Vôlei'
    },
    {
      id: 'qui4',
      name: 'Quiosque Gourmet 4',
      type: 'Espaço Convivência',
      badge: 'Churrasqueira & Freezer'
    }
  ];

  const days = ['Hoje (22/09)', 'Amanhã (23/09)', 'Sábado (26/09)', 'Domingo (27/09)'];

  const initialSlots = [
    { time: '07:00 - 08:00', available: true },
    { time: '08:00 - 09:00', available: false },
    { time: '09:00 - 10:00', available: true },
    { time: '16:00 - 17:00', available: true },
    { time: '17:00 - 18:00', available: true },
    { time: '18:00 - 19:00', available: false },
    { time: '19:00 - 20:00', available: true },
    { time: '20:00 - 21:00', available: true }
  ];

  const [selectedCourt, setSelectedCourt] = useState(courts[0].name);
  const [selectedDay, setSelectedDay] = useState(days[0]);
  const [selectedSlot, setSelectedSlot] = useState<string | null>(null);
  const [bookingSuccessMsg, setBookingSuccessMsg] = useState<string | null>(null);

  const [activeBookings, setActiveBookings] = useState<Booking[]>([
    {
      id: 'bk-1',
      court: 'Quadra Beach Tennis 1',
      date: '20/09/2026',
      time: '17:00 - 18:00',
      status: 'CONFIRMADO',
      token: 'CM-RES-9182'
    }
  ]);

  const handleConfirmBooking = () => {
    if (!selectedSlot) return;

    if (activeBookings.length >= 2) {
      alert('Limite de 2 reservas ativas atingido. Cancele uma reserva anterior para agendar um novo horário.');
      return;
    }

    const newBooking = {
      id: `bk-${Date.now()}`,
      court: selectedCourt,
      date: selectedDay.split(' ')[0],
      time: selectedSlot,
      status: 'CONFIRMADO',
      token: `CM-RES-${Math.floor(1000 + Math.random() * 9000)}`
    };

    setActiveBookings([newBooking, ...activeBookings]);
    setBookingSuccessMsg(`Reserva de ${selectedCourt} às ${selectedSlot} confirmada com sucesso!`);
    setSelectedSlot(null);
    setTimeout(() => setBookingSuccessMsg(null), 5000);
  };

  const handleCancelBooking = (id: string) => {
    setActiveBookings(activeBookings.filter((b) => b.id !== id));
  };

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Estrutura Esportiva</span>
          <span>•</span>
          <span>Reserva Antecipada</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Agendamento de Quadras & Espaços
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Reserve quadras e quiosques com confirmação imediata. Sistema inteligente que previne conflitos de horários.
        </p>
      </div>

      {bookingSuccessMsg && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="text-sm font-bold">{bookingSuccessMsg}</span>
          </div>
          <span className="text-xs bg-emerald-200 text-emerald-800 font-mono px-2 py-0.5 rounded-full">
            Catraca da quadra liberada
          </span>
        </div>
      )}

      {/* Grid Principal: Seletor à esquerda e Minhas Reservas à direita */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Painel de Reserva (8 colunas) */}
        <div className="lg:col-span-8 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-7 space-y-6">
          {/* 1. Escolha da Quadra */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[#1B3B54] block mb-3">
              1. Selecione a Estrutura:
            </label>
            <div className="grid grid-cols-1 sm:grid-cols-2 gap-3">
              {courts.map((court) => {
                const isSelected = selectedCourt === court.name;
                return (
                  <button
                    key={court.id}
                    onClick={() => {
                      setSelectedCourt(court.name);
                      setSelectedSlot(null);
                    }}
                    className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                      isSelected
                        ? 'border-[#1B3B54] bg-[#EBF4FA] shadow-sm ring-1 ring-[#1B3B54]'
                        : 'border-slate-200 hover:border-slate-300 hover:bg-slate-50'
                    }`}
                  >
                    <div className="font-bold text-sm text-[#1B3B54]">{court.name}</div>
                    <div className="text-xs text-slate-500 mt-0.5">{court.badge}</div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* 2. Escolha da Data */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[#1B3B54] block mb-3">
              2. Data da Atividade:
            </label>
            <div className="flex gap-2 overflow-x-auto pb-1">
              {days.map((day) => {
                const isSelected = selectedDay === day;
                return (
                  <button
                    key={day}
                    onClick={() => {
                      setSelectedDay(day);
                      setSelectedSlot(null);
                    }}
                    className={`px-4 py-2 rounded-xl text-xs font-bold whitespace-nowrap transition-all cursor-pointer ${
                      isSelected
                        ? 'bg-[#1B3B54] text-white shadow-sm'
                        : 'bg-slate-100 text-slate-600 hover:bg-slate-200'
                    }`}
                  >
                    {day}
                  </button>
                );
              })}
            </div>
          </div>

          {/* 3. Horários Disponíveis */}
          <div>
            <label className="text-xs font-bold uppercase tracking-wider text-[#1B3B54] block mb-3">
              3. Horários Disponíveis (1 hora de duração):
            </label>
            <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
              {initialSlots.map((slot, idx) => {
                const isSelected = selectedSlot === slot.time;
                return (
                  <button
                    key={idx}
                    disabled={!slot.available}
                    onClick={() => setSelectedSlot(slot.time)}
                    className={`p-3 rounded-xl border text-center transition-all cursor-pointer ${
                      !slot.available
                        ? 'border-slate-200 bg-slate-100 text-slate-400 cursor-not-allowed line-through'
                        : isSelected
                        ? 'border-emerald-600 bg-emerald-50 text-emerald-900 font-bold ring-2 ring-emerald-500 shadow-sm'
                        : 'border-slate-200 hover:border-[#1B3B54] text-[#1B3B54] hover:bg-slate-50'
                    }`}
                  >
                    <div className="text-xs font-semibold">{slot.time}</div>
                    <div className="text-[10px] mt-1">
                      {slot.available ? (
                        <span className="text-emerald-700 font-medium">Disponível</span>
                      ) : (
                        <span className="text-slate-400">Ocupado</span>
                      )}
                    </div>
                  </button>
                );
              })}
            </div>
          </div>

          {/* Botão de Confirmação */}
          <div className="pt-3 border-t border-slate-100 flex flex-col sm:flex-row items-center justify-between gap-4">
            <div className="text-xs text-slate-500">
              {selectedSlot ? (
                <span>
                  Selecionado: <b className="text-[#1B3B54]">{selectedCourt}</b> às <b className="text-[#1B3B54]">{selectedSlot}</b> ({selectedDay})
                </span>
              ) : (
                <span>Selecione um horário disponível acima para continuar.</span>
              )}
            </div>

            <button
              onClick={handleConfirmBooking}
              disabled={!selectedSlot}
              className={`w-full sm:w-auto px-6 py-3 rounded-xl font-bold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-md ${
                !selectedSlot
                  ? 'bg-slate-200 text-slate-400 cursor-not-allowed'
                  : 'bg-emerald-600 hover:bg-emerald-500 text-white shadow-emerald-600/20 hover:shadow-lg'
              }`}
            >
              <BookmarkCheck className="w-4 h-4" />
              <span>Confirmar Reserva</span>
            </button>
          </div>
        </div>

        {/* Minhas Reservas Ativas (4 colunas) */}
        <div className="lg:col-span-4 space-y-6">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <h3 className="font-bold text-[#1B3B54] text-base">
                Minhas Reservas Ativas
              </h3>
              <span className="text-xs px-2.5 py-0.5 rounded-full bg-slate-100 font-bold text-slate-600">
                {activeBookings.length}/2
              </span>
            </div>

            {activeBookings.length === 0 ? (
              <p className="text-xs text-slate-400 py-4 text-center">
                Nenhuma reserva ativa no momento.
              </p>
            ) : (
              <div className="space-y-3">
                {activeBookings.map((b) => (
                  <div
                    key={b.id}
                    className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2 relative group"
                  >
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="text-xs font-bold text-[#1B3B54] leading-snug">
                          {b.court}
                        </div>
                        <div className="text-[11px] text-slate-500 mt-1 flex items-center space-x-1.5">
                          <Calendar className="w-3.5 h-3.5 text-slate-400" />
                          <span>{b.date} • {b.time}</span>
                        </div>
                      </div>

                      <button
                        onClick={() => handleCancelBooking(b.id)}
                        title="Cancelar Reserva"
                        className="text-slate-400 hover:text-rose-600 transition-colors cursor-pointer p-1"
                      >
                        <Trash2 className="w-4 h-4" />
                      </button>
                    </div>

                    <div className="pt-2 border-t border-slate-200/60 flex items-center justify-between text-[10px] text-slate-400 font-mono">
                      <span>Token: {b.token}</span>
                      <span className="text-emerald-700 font-bold uppercase">Confirmado</span>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {/* Política do Clube */}
            <div className="p-3 rounded-xl bg-blue-50/70 border border-blue-200/60 text-blue-900 text-[11px] space-y-1">
              <span className="font-bold block">Regra de Convivência:</span>
              <span>Cancelamento sem penalidade até 2 horas antes do início da partida.</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
