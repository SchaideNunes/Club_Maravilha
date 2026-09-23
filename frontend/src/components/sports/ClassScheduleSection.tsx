import React from 'react';
import { ArrowRight, ArrowUpRight } from 'lucide-react';
import soccerImg from '../../assets/sports_soccer.jpg';
import futsalImg from '../../assets/sports_futsal.jpg';
import voleiImg from '../../assets/sports_volei.jpg';

interface ClassScheduleSectionProps {
  onSelectClass?: (classTitle: string) => void;
  onViewFullSchedule?: () => void;
}

export const ClassScheduleSection: React.FC<ClassScheduleSectionProps> = ({
  onSelectClass,
  onViewFullSchedule
}) => {
  const classes = [
    {
      id: 'aula-1',
      day: '12',
      month: 'SET',
      title: 'Futebol',
      location: 'Quadra x',
      time: '15:00 - 17:00',
      image: soccerImg
    },
    {
      id: 'aula-2',
      day: '12',
      month: 'SET',
      title: 'Futsal',
      location: 'Quadra Y',
      time: '15:00 - 17:00',
      image: futsalImg
    },
    {
      id: 'aula-3',
      day: '18',
      month: 'SET',
      title: 'Vôlei',
      location: 'Quadra x',
      time: '15:00 - 17:00',
      image: voleiImg
    },
    {
      id: 'aula-4',
      day: '20',
      month: 'SET',
      title: 'Vôlei',
      location: 'Quadra x',
      time: '15:00 - 17:00',
      image: voleiImg
    }
  ];

  return (
    <section id="programacao-aulas" className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 py-8">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-bold text-[#1F3347] font-sans">
          Programação Aulas
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
      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6">
        {classes.map((cls) => (
          <div
            key={cls.id}
            onClick={() => onSelectClass?.(cls.title)}
            className="group cursor-pointer bg-white rounded-2xl overflow-hidden border border-slate-200/80 shadow-sm hover:shadow-md hover:border-slate-300 transition-all duration-300 flex flex-col justify-between"
          >
            {/* Image with Date Badge */}
            <div className="relative h-44 w-full overflow-hidden bg-slate-100">
              <img
                src={cls.image}
                alt={cls.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />

              {/* Date Badge */}
              <div className="absolute top-3 left-3 bg-[#1F3347]/95 backdrop-blur-sm text-white px-2.5 py-1.5 rounded-lg flex flex-col items-center shadow-md">
                <span className="text-base font-bold leading-none text-amber-400">
                  {cls.day}
                </span>
                <span className="text-[10px] font-semibold tracking-wider text-slate-200">
                  {cls.month}
                </span>
              </div>
            </div>

            {/* Card Content & Action Arrow */}
            <div className="p-4 flex items-end justify-between">
              <div>
                <h3 className="font-bold text-[#1F3347] text-base mb-1">
                  {cls.title}
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  {cls.location}
                </p>
                <p className="text-xs text-slate-500">
                  {cls.time}
                </p>
              </div>

              {/* Subtle Arrow Button */}
              <div className="p-2 text-slate-400 group-hover:text-[#1F3347] group-hover:translate-x-1 transition-all">
                <ArrowUpRight className="w-5 h-5" />
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
