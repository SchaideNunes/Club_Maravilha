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
    <section id="programacao-esportes" className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 py-10">
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

      {/* 4 Sports Cards Grid matching Figma Frame 60 (gap: 16px) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {sportsEvents.map((event) => (
          <div
            key={event.id}
            className="bg-white rounded-[32px] border border-black/30 overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between"
          >
            {/* Top Image Container (Frame 56: h: 200px, bg: #0C1014) */}
            <div className="relative h-[200px] w-full overflow-hidden bg-[#0C1014]">
              <img
                src={event.image}
                alt={event.title}
                className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-500"
              />

              {/* Date Badge (Frame 113: w: 65px, h: 74px, left: 24.5px, top: 102.5px, bg: #2B3E4E, border: 1px solid #FFFFFF, rounded: 16px) */}
              <div className="absolute top-[102px] left-[24px] w-[65px] h-[74px] bg-[#2B3E4E] border border-white rounded-[16px] flex flex-col items-center justify-center shadow-lg pointer-events-none">
                <span className="text-[20px] font-bold leading-6 text-white text-center font-sans">
                  {event.day}
                </span>
                <span className="text-[20px] font-bold leading-6 text-white text-center font-sans">
                  {event.month}
                </span>
              </div>
            </div>

            {/* Card Body (Frame 57: padding: 16px, gap: 16px) */}
            <div className="p-4 flex-1 flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-2">
                {/* Event Title: (font-bold 24px, #1B3D5A) */}
                <h3 className="text-[24px] font-bold leading-7 text-[#1B3D5A] font-sans">
                  {event.title}
                </h3>

                {/* Info Rows (Frame 116 & 115: font-medium 18px, rgba(36, 83, 122, 0.8)) */}
                <div className="flex flex-col gap-2 pt-1 text-[18px] font-medium text-[rgba(36,83,122,0.8)] font-sans">
                  <div className="flex items-center gap-3">
                    <MapPin className="w-6 h-6 text-[rgba(36,83,122,0.8)] shrink-0" />
                    <span className="leading-snug">{event.location}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="w-6 h-6 text-[rgba(36,83,122,0.8)] shrink-0" />
                    <span className="leading-snug">{event.time}</span>
                  </div>
                </div>
              </div>

              {/* Action Button (Frame 49: h: 48px, bg: #2B3E4E, rounded: 8px, padding: 8px 16px, gap: 8px) */}
              <button
                onClick={() => onSelectEvent?.(event.title)}
                className="w-full h-[48px] rounded-[8px] bg-[#2B3E4E] hover:bg-[#202e3b] text-white flex items-center justify-center gap-2 transition-colors cursor-pointer shadow-sm"
              >
                <Ticket className="w-7 h-7 text-white shrink-0" />
                <span className="text-[22px] font-normal leading-7 text-white font-sans">
                  Saiba mais
                </span>
                <ArrowRight className="w-6 h-6 text-white shrink-0" />
              </button>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
