import React from 'react';
import familyBg from '../../assets/family_club.jpg';

interface AboutBannerSectionProps {
  onExploreClub?: () => void;
}

export const AboutBannerSection: React.FC<AboutBannerSectionProps> = ({ onExploreClub }) => {
  return (
    <section id="sobre" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10">
      <div className="relative w-full h-[380px] sm:h-[440px] md:h-[480px] rounded-2xl md:rounded-3xl overflow-hidden shadow-xl border border-slate-200/60 bg-slate-900">
        {/* Background Image: Family walking outdoors */}
        <img
          src={familyBg}
          alt="Tradição, esporte e convivência no Clube Maravilha em Teofilândia"
          className="w-full h-full object-cover object-center"
        />

        {/* Dark Gradient Overlay for Readability on the Left */}
        <div className="absolute inset-0 bg-gradient-to-r from-black/80 via-black/50 to-transparent md:w-[65%] w-full" />

        {/* Content Box */}
        <div className="absolute inset-y-0 left-0 flex items-center p-6 sm:p-10 md:p-14 z-10 max-w-xl">
          <div className="space-y-4 sm:space-y-5">
            <h2 className="text-2xl sm:text-3xl md:text-4xl font-black text-white leading-tight font-sans">
              Tradição, esporte e convivência em um só lugar
            </h2>

            <p className="text-sm sm:text-base text-white/90 font-normal leading-relaxed max-w-md">
              O Clube Maravilha é um espaço pensado para reunir a comunidade de Teofilândia. Conheça nossa estrutura, atividades e tudo o que acontece por aqui.
            </p>

            <div className="pt-2">
              <button
                onClick={onExploreClub}
                className="px-7 py-3 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-xs sm:text-sm tracking-wide shadow-lg transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:outline-none"
              >
                Conheça o clube
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
