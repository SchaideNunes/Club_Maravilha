import React from 'react';
import { MapPin, Clock, ArrowRight, Ticket } from 'lucide-react';
import voleiImg from '../../assets/sports_volei.jpg';
import futsalImg from '../../assets/sports_futsal.jpg';

interface SportsProgrammingSectionProps {
  onSelectEvent?: (eventTitle: string) => void;
  onViewFullSchedule?: () => void;
}

export const SportsProgrammingSection: React.FC<SportsProgrammingSectionProps> = ({
  onSelectEvent,
  onViewFullSchedule
}) => {
  const sportsEvents = [
    {
      id: 1,
      title: 'Vôlei',
      day: '12',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: voleiImg
    },
    {
      id: 2,
      title: 'Futsal',
      day: '22',
      month: 'SET',
      location: 'Quadra 1',
      time: '15:00 - 17:00',
      image: futsalImg
    },
    {
      id: 3,
      title: 'Vôlei',
      day: '26',
      month: 'SET',
      location: 'Quadra 2',
      time: '15:00 - 17:00',
      image: voleiImg
    },
    {
      id: 4,
      title: 'Vôlei',
      day: '28',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: voleiImg
    }
  ];

  return (
    <section id="programacao-esportes" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-[#1F3347] font-sans">
          Programação Esportes
        </h2>

        <button
          onClick={onViewFullSchedule}
          className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-white border border-slate-300 hover:border-[#1F3347] text-slate-700 hover:text-[#1F3347] text-xs font-medium shadow-sm transition-colors"
        >
          <span>Ver agenda completa</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Cards Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {sportsEvents.map((event) => (
          <div
            key={event.id}
            className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col"
          >
            {/* Card Image Header with Overlay Date Badge */}
            <div className="relative h-44 w-full overflow-hidden bg-slate-100">
              <img
                src={event.image}
                alt={event.title}
                className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-300"
              />

              {/* Date Badge in Top Left */}
              <div className="absolute top-3 left-3 bg-[#1F3347] text-white rounded-xl px-2.5 py-1.5 text-center shadow-md min-w-[42px]">
                <div className="text-sm font-black leading-none">{event.day}</div>
                <div className="text-[9px] font-semibold tracking-wider text-amber-200 uppercase mt-0.5">
                  {event.month}
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="p-4 flex-1 flex flex-col justify-between space-y-4">
              <div className="space-y-2">
                <h3 className="text-base font-bold text-[#1F3347] leading-tight">
                  {event.title}
                </h3>

                <div className="space-y-1 text-xs text-slate-500">
                  <div className="flex items-center space-x-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{event.location}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{event.time}</span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => onSelectEvent?.(event.title)}
                className="w-full py-2 px-3 rounded-lg bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors focus:outline-none"
              >
                <Ticket className="w-3.5 h-3.5 text-amber-300" />
                <span>Saiba mais</span>
                <ArrowRight className="w-3.5 h-3.5" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
