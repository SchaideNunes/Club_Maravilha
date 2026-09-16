import React from 'react';
import { MapPin, Clock, ArrowRight, Music2 } from 'lucide-react';
import joaoImg from '../../assets/show_joao_gomes.jpg';
import calypsoImg from '../../assets/show_calypso.jpg';
import dorgivalImg from '../../assets/show_dorgival.jpg';
import tarcisioImg from '../../assets/show_tarcisio.jpg';

interface LeisureProgrammingSectionProps {
  onSelectShow?: (showTitle: string) => void;
  onViewFullSchedule?: () => void;
}

export const LeisureProgrammingSection: React.FC<LeisureProgrammingSectionProps> = ({
  onSelectShow,
  onViewFullSchedule
}) => {
  const leisureShows = [
    {
      id: 1,
      artist: 'João Gomes',
      category: 'SHOW',
      day: '12',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: joaoImg
    },
    {
      id: 2,
      artist: 'Calypso',
      category: 'SHOW',
      day: '18',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: calypsoImg
    },
    {
      id: 3,
      artist: 'Dorgival Dantas',
      category: 'SHOW',
      day: '20',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: dorgivalImg
    },
    {
      id: 4,
      artist: 'Tarcísio do acordeon',
      category: 'SHOW',
      day: '20',
      month: 'SET',
      location: 'Quadra 4',
      time: '15:00 - 17:00',
      image: tarcisioImg
    }
  ];

  return (
    <section id="programacao-lazer" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center space-x-3">
          <h2 className="text-xl sm:text-2xl font-bold text-[#1F3347] font-sans">
            Programação Lazer
          </h2>
          <button
            onClick={onViewFullSchedule}
            className="hidden sm:inline-flex items-center space-x-1.5 px-3 py-1 rounded-full bg-white border border-slate-300 hover:border-[#1F3347] text-slate-600 hover:text-[#1F3347] text-[11px] font-medium shadow-sm transition-colors"
          >
            <span>Ver agenda completa</span>
            <ArrowRight className="w-3 h-3" />
          </button>
        </div>

        <button
          onClick={onViewFullSchedule}
          className="sm:hidden inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-white border border-slate-300 text-slate-700 text-xs font-medium shadow-sm"
        >
          <span>Agenda</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 4 Shows Grid */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
        {leisureShows.map((show) => (
          <div
            key={show.id}
            className="bg-white rounded-2xl border border-slate-200/80 overflow-hidden shadow-sm hover:shadow-md transition-shadow duration-200 flex flex-col"
          >
            {/* Card Image Header with Overlay Date Badge */}
            <div className="relative h-44 w-full overflow-hidden bg-slate-100">
              <img
                src={show.image}
                alt={show.artist}
                className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-300"
              />

              {/* Date Badge in Top Left */}
              <div className="absolute top-3 left-3 bg-[#1F3347] text-white rounded-xl px-2.5 py-1.5 text-center shadow-md min-w-[42px]">
                <div className="text-sm font-black leading-none">{show.day}</div>
                <div className="text-[9px] font-semibold tracking-wider text-amber-200 uppercase mt-0.5">
                  {show.month}
                </div>
              </div>
            </div>

            {/* Card Body */}
            <div className="p-4 flex-1 flex flex-col justify-between space-y-4">
              <div className="space-y-1.5">
                <span className="text-[10px] font-bold text-[#4E7A9C] tracking-wider uppercase">
                  {show.category}
                </span>

                <h3 className="text-base font-bold text-[#1F3347] leading-tight">
                  {show.artist}
                </h3>

                <div className="space-y-1 text-xs text-slate-500 pt-1">
                  <div className="flex items-center space-x-1.5">
                    <MapPin className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{show.location}</span>
                  </div>
                  <div className="flex items-center space-x-1.5">
                    <Clock className="w-3.5 h-3.5 text-slate-400 shrink-0" />
                    <span>{show.time}</span>
                  </div>
                </div>
              </div>

              {/* Action Button */}
              <button
                onClick={() => onSelectShow?.(show.artist)}
                className="w-full py-2 px-3 rounded-lg bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-semibold flex items-center justify-center space-x-2 transition-colors focus:outline-none"
              >
                <Music2 className="w-3.5 h-3.5 text-amber-300" />
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
