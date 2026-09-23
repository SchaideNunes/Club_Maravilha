import React from 'react';
import entertainmentImg from '../../assets/leisure_entertainment.jpg';
import eventsImg from '../../assets/leisure_events.jpg';

interface LeisureActivitiesSectionProps {
  onSelectActivity?: (activityTitle: string) => void;
}

export const LeisureActivitiesSection: React.FC<LeisureActivitiesSectionProps> = ({
  onSelectActivity
}) => {
  const activities = [
    {
      id: 'entretenimento',
      title: 'Entretenimento',
      image: entertainmentImg
    },
    {
      id: 'eventos',
      title: 'Eventos',
      image: eventsImg
    }
  ];

  return (
    <section className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 py-8">
      {/* Centered Section Title */}
      <h2 className="text-2xl sm:text-3xl font-bold text-[#1B3B54] text-center mb-8">
        Atividades de Lazer
      </h2>

      {/* 2 Big Highlight Cards */}
      <div className="grid grid-cols-1 md:grid-cols-2 gap-6 sm:gap-8 max-w-4xl mx-auto">
        {activities.map((act) => (
          <div
            key={act.id}
            onClick={() => onSelectActivity?.(act.title)}
            className="group cursor-pointer bg-[#EBF1F6] hover:bg-[#E2ECF4] rounded-2xl p-4 sm:p-5 flex flex-col items-center transition-all duration-300 shadow-sm hover:shadow-md transform hover:-translate-y-1"
          >
            {/* Title at Top */}
            <h3 className="text-lg sm:text-xl font-bold text-[#1B3B54] text-center mb-3">
              {act.title}
            </h3>

            {/* Photo */}
            <div className="w-full h-44 sm:h-52 rounded-xl overflow-hidden shadow-inner">
              <img
                src={act.image}
                alt={act.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
