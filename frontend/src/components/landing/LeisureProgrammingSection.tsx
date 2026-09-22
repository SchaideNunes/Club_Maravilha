import { MapPin, Clock, ArrowRight, Ticket } from 'lucide-react';
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

      {/* 4 Shows Grid matching Figma Frame 60 (gap: 16px) */}
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
        {leisureShows.map((show) => (
          <div
            key={show.id}
            className="bg-white rounded-[32px] border border-black/30 overflow-hidden shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between"
          >
            {/* Top Image Container (Frame 56: h: 200px, bg: #0C1014) */}
            <div className="relative h-[200px] w-full overflow-hidden bg-[#0C1014]">
              <img
                src={show.image}
                alt={show.artist}
                className="w-full h-full object-cover transform hover:scale-105 transition-transform duration-500"
              />

              {/* Date Badge (Frame 113: w: 65px, h: 74px, left: 24.5px, top: 102.5px, bg: #2B3E4E, border: 1px solid #FFFFFF, rounded: 16px) */}
              <div className="absolute top-[102px] left-[24px] w-[65px] h-[74px] bg-[#2B3E4E] border border-white rounded-[16px] flex flex-col items-center justify-center shadow-lg pointer-events-none">
                <span className="text-[20px] font-bold leading-6 text-white text-center font-sans">
                  {show.day}
                </span>
                <span className="text-[20px] font-bold leading-6 text-white text-center font-sans">
                  {show.month}
                </span>
              </div>
            </div>

            {/* Card Body (Frame 57: padding: 16px, gap: 16px) */}
            <div className="p-4 flex-1 flex flex-col justify-between gap-4">
              <div className="flex flex-col gap-2">
                {/* Category tag: SHOW (font-bold 20px, #24537A) */}
                <span className="text-[20px] font-bold leading-6 text-[#24537A] font-sans">
                  {show.category}
                </span>

                {/* Artist Name: (font-bold 24px, #1B3D5A) */}
                <h3 className="text-[24px] font-bold leading-7 text-[#1B3D5A] font-sans">
                  {show.artist}
                </h3>

                {/* Info Rows (Frame 116 & 115: font-medium 18px, rgba(36, 83, 122, 0.8)) */}
                <div className="flex flex-col gap-2 pt-1 text-[18px] font-medium text-[rgba(36,83,122,0.8)] font-sans">
                  <div className="flex items-center gap-3">
                    <MapPin className="w-6 h-6 text-[rgba(36,83,122,0.8)] shrink-0" />
                    <span className="leading-snug">{show.location}</span>
                  </div>
                  <div className="flex items-center gap-3">
                    <Clock className="w-6 h-6 text-[rgba(36,83,122,0.8)] shrink-0" />
                    <span className="leading-snug">{show.time}</span>
                  </div>
                </div>
              </div>

              {/* Action Button (Frame 49: h: 48px, bg: #2B3E4E, rounded: 8px, padding: 8px 16px, gap: 8px) */}
              <button
                onClick={() => onSelectShow?.(show.artist)}
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
