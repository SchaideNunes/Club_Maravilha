import React from 'react';

export interface ModalityItem {
  id: string;
  title: string;
  imageSrc: string;
}

interface ModalitiesGridProps {
  sectionTitle: string;
  modalities: ModalityItem[];
  onSelectModality?: (title: string) => void;
}

export const ModalitiesGrid: React.FC<ModalitiesGridProps> = ({
  sectionTitle,
  modalities,
  onSelectModality
}) => {
  return (
    <section className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 py-8">
      {/* Centered Section Title */}
      <h2 className="text-2xl sm:text-3xl font-bold text-[#1B3B54] text-center mb-8">
        {sectionTitle}
      </h2>

      {/* 4 Cards Grid */}
      <div className="grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6">
        {modalities.map((item) => (
          <div
            key={item.id}
            onClick={() => onSelectModality?.(item.title)}
            className="group cursor-pointer bg-[#EBF1F6] hover:bg-[#E2ECF4] rounded-2xl p-3 sm:p-4 flex flex-col items-center transition-all duration-300 shadow-sm hover:shadow-md transform hover:-translate-y-1"
          >
            {/* Title at top */}
            <h3 className="text-base sm:text-lg lg:text-xl font-bold text-[#1B3B54] text-center mb-2.5 sm:mb-3">
              {item.title}
            </h3>

            {/* Photo Container below */}
            <div className="w-full h-28 sm:h-36 rounded-xl overflow-hidden shadow-inner">
              <img
                src={item.imageSrc}
                alt={item.title}
                className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
