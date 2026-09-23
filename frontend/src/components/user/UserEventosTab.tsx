import React, { useState } from 'react';
import {
  Calendar,
  Ticket,
  Clock,
  MapPin,
  CheckCircle2
} from 'lucide-react';

import showJoaoImg from '../../assets/show_joao_gomes.jpg';
import showCalypsoImg from '../../assets/show_calypso.jpg';
import showDorgivalImg from '../../assets/show_dorgival.jpg';
import showTarcisioImg from '../../assets/show_tarcisio.jpg';

export const UserEventosTab: React.FC = () => {
  const [purchasedTickets, setPurchasedTickets] = useState<string[]>(['show-joao']);
  const [successToast, setSuccessToast] = useState<string | null>(null);

  const events = [
    {
      id: 'show-joao',
      title: 'João Gomes - Sunset Maravilha',
      date: '12 de Setembro de 2026',
      time: '15:00 - 22:00',
      location: 'Arena Principal de Shows',
      priceNormal: 'R$ 160,00',
      priceSocio: 'R$ 80,00 (50% OFF Sócio)',
      image: showJoaoImg,
      tag: 'GRANDE SHOW'
    },
    {
      id: 'show-calypso',
      title: 'Banda Calypso - Tour Maravilha',
      date: '18 de Setembro de 2026',
      time: '19:00 - 01:00',
      location: 'Arena Principal de Shows',
      priceNormal: 'R$ 140,00',
      priceSocio: 'R$ 70,00 (50% OFF Sócio)',
      image: showCalypsoImg,
      tag: 'GRANDE SHOW'
    },
    {
      id: 'show-dorgival',
      title: 'Dorgival Dantas - Noite do Forró',
      date: '20 de Setembro de 2026',
      time: '20:00 - 02:00',
      location: 'Palco Lago Sunset',
      priceNormal: 'R$ 120,00',
      priceSocio: 'R$ 60,00 (50% OFF Sócio)',
      image: showDorgivalImg,
      tag: 'TRADIÇÃO'
    },
    {
      id: 'show-tarcisio',
      title: 'Tarcísio do Acordeon - Festival Primavera',
      date: '28 de Setembro de 2026',
      time: '18:00 - 00:00',
      location: 'Arena Principal de Shows',
      priceNormal: 'R$ 150,00',
      priceSocio: 'R$ 75,00 (50% OFF Sócio)',
      image: showTarcisioImg,
      tag: 'FESTIVAL'
    }
  ];

  const handleBuyTicket = (eventId: string, title: string) => {
    if (!purchasedTickets.includes(eventId)) {
      setPurchasedTickets([...purchasedTickets, eventId]);
    }
    setSuccessToast(`Ingresso Sócio garantido para ${title}! Vinculado à sua Carteirinha Digital.`);
    setTimeout(() => setSuccessToast(null), 5000);
  };

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Programação Cultural</span>
          <span>•</span>
          <span>Benefício Exclusivo</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Eventos & Grandes Shows
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Sócios do Club Maravilha contam com 50% de desconto automático e acesso VIP pela portaria exclusiva.
        </p>
      </div>

      {successToast && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="text-sm font-bold">{successToast}</span>
          </div>
          <span className="text-xs bg-emerald-200 text-emerald-800 font-mono px-2 py-0.5 rounded-full">
            Entrada Facial Liberada
          </span>
        </div>
      )}

      {/* Grid de Eventos */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
        {events.map((evt) => {
          const isPurchased = purchasedTickets.includes(evt.id);

          return (
            <div
              key={evt.id}
              className="bg-white rounded-3xl border border-slate-200 overflow-hidden shadow-sm hover:shadow-md transition-all flex flex-col justify-between"
            >
              <div className="relative h-52 w-full overflow-hidden bg-slate-900">
                <img
                  src={evt.image}
                  alt={evt.title}
                  className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                />
                <div className="absolute top-4 left-4 px-3 py-1 rounded-full bg-slate-950/80 backdrop-blur-xs text-amber-300 text-xs font-bold uppercase tracking-wider border border-white/10">
                  {evt.tag}
                </div>
                {isPurchased && (
                  <div className="absolute top-4 right-4 px-3 py-1 rounded-full bg-emerald-600 text-white text-xs font-bold uppercase tracking-wider shadow-md flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Ingresso Garantido</span>
                  </div>
                )}
              </div>

              <div className="p-6 flex-1 flex flex-col justify-between space-y-5">
                <div>
                  <h3 className="text-xl font-black text-[#1B3B54]">{evt.title}</h3>
                  <div className="mt-3 space-y-1.5 text-xs text-slate-500">
                    <div className="flex items-center space-x-2">
                      <Calendar className="w-4 h-4 text-slate-400" />
                      <span>{evt.date}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Clock className="w-4 h-4 text-slate-400" />
                      <span>{evt.time}</span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <MapPin className="w-4 h-4 text-slate-400" />
                      <span>{evt.location}</span>
                    </div>
                  </div>
                </div>

                <div className="pt-4 border-t border-slate-100 flex items-center justify-between">
                  <div>
                    <span className="text-[10px] text-slate-400 line-through block">
                      Não-sócio: {evt.priceNormal}
                    </span>
                    <span className="text-sm font-black text-emerald-700">
                      {evt.priceSocio}
                    </span>
                  </div>

                  <button
                    onClick={() => handleBuyTicket(evt.id, evt.title)}
                    className={`px-4 py-2.5 rounded-xl font-bold text-xs flex items-center space-x-1.5 transition-all cursor-pointer ${
                      isPurchased
                        ? 'bg-emerald-100 text-emerald-800 border border-emerald-300'
                        : 'bg-[#1B3B54] hover:bg-[#152e42] text-white shadow-md'
                    }`}
                  >
                    <Ticket className="w-4 h-4" />
                    <span>{isPurchased ? 'Ver Ingresso' : 'Garantir Ingresso Sócio'}</span>
                  </button>
                </div>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
