import React from 'react';
import { ArrowRight } from 'lucide-react';

interface ExperiencesSectionProps {
  onSelectExperience?: (experienceName: string) => void;
  onViewFullSchedule?: () => void;
}

export const ExperiencesSection: React.FC<ExperiencesSectionProps> = ({
  onSelectExperience,
  onViewFullSchedule
}) => {
  return (
    <section id="experiencias" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
      {/* Section Header */}
      <div className="flex items-center justify-between mb-6">
        <h2 className="text-xl sm:text-2xl font-black tracking-wider text-[#1F3347] uppercase font-sans">
          EXPERIÊNCIAS
        </h2>

        <button
          onClick={onViewFullSchedule}
          className="inline-flex items-center space-x-1.5 px-4 py-1.5 rounded-full bg-white border border-slate-300 hover:border-[#1F3347] text-slate-700 hover:text-[#1F3347] text-xs font-medium shadow-sm transition-colors"
        >
          <span>Ver agenda completa</span>
          <ArrowRight className="w-3.5 h-3.5" />
        </button>
      </div>

      {/* 3 Experience Cards Grid */}
      <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
        {/* Card 1: Cursos Esportivos */}
        <div className="bg-[#1B3B54] rounded-2xl p-6 flex flex-col justify-between shadow-lg shadow-slate-900/10 min-h-[260px] transform hover:-translate-y-1 transition-transform duration-300">
          <h3 className="text-xl font-bold text-white tracking-wide">
            Cursos Esportivos
          </h3>

          {/* Centered White Dumbbell Icon */}
          <div className="flex items-center justify-center my-6">
            <svg
              className="w-20 h-20 text-white fill-current"
              viewBox="0 0 100 100"
              fill="none"
              xmlns="http://www.w3.org/2000/svg"
            >
              <g transform="rotate(-45 50 50)">
                {/* Left Weight */}
                <rect x="18" y="32" width="10" height="36" rx="4" fill="white" />
                <rect x="28" y="38" width="6" height="24" rx="2" fill="white" />
                {/* Center Bar */}
                <rect x="34" y="46" width="32" height="8" rx="2" fill="white" />
                {/* Right Weight */}
                <rect x="66" y="38" width="6" height="24" rx="2" fill="white" />
                <rect x="72" y="32" width="10" height="36" rx="4" fill="white" />
              </g>
            </svg>
          </div>

          <button
            onClick={() => onSelectExperience?.('Cursos Esportivos')}
            className="w-full py-3 rounded-full bg-[#EFA73D] hover:bg-[#E29A2F] text-[#1F3347] font-bold text-sm tracking-wide shadow-md transition-colors focus:outline-none"
          >
            Saiba mais
          </button>
        </div>

        {/* Card 2: Esporte */}
        <div className="bg-[#1B3B54] rounded-2xl p-6 flex flex-col justify-between shadow-lg shadow-slate-900/10 min-h-[260px] transform hover:-translate-y-1 transition-transform duration-300">
          <h3 className="text-xl font-bold text-white tracking-wide">
            Esporte
          </h3>

          {/* Centered White Whistle Icon */}
          <div className="flex items-center justify-center my-6">
            <svg
              className="w-20 h-20 text-white fill-current"
              viewBox="0 0 100 100"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Whistle Body */}
              <circle cx="60" cy="55" r="20" fill="white" />
              <path d="M60 35H30C24 35 20 39 20 45V55H40C40 45 48 37 60 35Z" fill="white" />
              <rect x="14" y="45" width="10" height="8" rx="2" fill="white" />
              <circle cx="60" cy="55" r="8" fill="#1B3B54" />
              <rect x="42" y="33" width="8" height="6" rx="1" fill="#1B3B54" />
              {/* Sound waves / whistle air accents */}
              <path d="M48 24C44 20 40 18 34 18" stroke="white" strokeWidth="4" strokeLinecap="round" />
              <path d="M58 20C55 14 50 10 42 8" stroke="white" strokeWidth="4" strokeLinecap="round" />
            </svg>
          </div>

          <button
            onClick={() => onSelectExperience?.('Esporte')}
            className="w-full py-3 rounded-full bg-[#EFA73D] hover:bg-[#E29A2F] text-[#1F3347] font-bold text-sm tracking-wide shadow-md transition-colors focus:outline-none"
          >
            Saiba mais
          </button>
        </div>

        {/* Card 3: Lazer */}
        <div className="bg-[#1B3B54] rounded-2xl p-6 flex flex-col justify-between shadow-lg shadow-slate-900/10 min-h-[260px] transform hover:-translate-y-1 transition-transform duration-300">
          <h3 className="text-xl font-bold text-white tracking-wide">
            Lazer
          </h3>

          {/* Centered White Swimming Goggles / Sunglasses Icon */}
          <div className="flex items-center justify-center my-6">
            <svg
              className="w-20 h-20 text-white fill-current"
              viewBox="0 0 100 100"
              xmlns="http://www.w3.org/2000/svg"
            >
              {/* Left Lens */}
              <path
                d="M20 45C20 38 27 34 37 34C47 34 50 40 48 52C46 62 37 66 28 66C21 66 20 56 20 45Z"
                fill="white"
              />
              {/* Right Lens */}
              <path
                d="M80 45C80 38 73 34 63 34C53 34 50 40 52 52C54 62 63 66 72 66C79 66 80 56 80 45Z"
                fill="white"
              />
              {/* Bridge */}
              <path
                d="M48 42C48 40 52 40 52 42"
                stroke="white"
                strokeWidth="5"
                strokeLinecap="round"
              />
              {/* Outer Strap */}
              <path d="M20 44L12 40" stroke="white" strokeWidth="4" strokeLinecap="round" />
              <path d="M80 44L88 40" stroke="white" strokeWidth="4" strokeLinecap="round" />
            </svg>
          </div>

          <button
            onClick={() => onSelectExperience?.('Lazer')}
            className="w-full py-3 rounded-full bg-[#EFA73D] hover:bg-[#E29A2F] text-[#1F3347] font-bold text-sm tracking-wide shadow-md transition-colors focus:outline-none"
          >
            Saiba mais
          </button>
        </div>
      </div>
    </section>
  );
};
