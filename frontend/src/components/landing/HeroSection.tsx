import React from 'react';
import heroBg from '../../assets/Homepage.png';

interface HeroSectionProps {
  onOpenPortal: () => void;
  onExploreProgramming?: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ onOpenPortal }) => {
  return (
    <section id="hero" className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 pt-6 pb-12">
      {/* Outer Banner Container with Rounded Corners */}
      <div 
        className="relative w-full h-[400px] sm:h-[480px] md:h-[520px] rounded-2xl md:rounded-3xl overflow-hidden shadow-xl border border-slate-200/60 bg-slate-900"
      >
        {/* Background Image: Resort pool & cabana at dusk */}
        <img
          src={heroBg}
          alt="Clube Maravilha Complexo de Lazer e Esportes"
          className="w-full h-full object-cover object-center"
        />

        {/* Subtle Ambient Lightening Layer */}
        <div className="absolute inset-0 bg-gradient-to-r from-white/90 via-white/60 to-transparent md:w-[65%] w-full" />

        {/* Content Card Overlay on the Left (Pixel-perfect match to Figma) */}
        <div className="absolute inset-y-0 left-0 flex items-center p-6 sm:p-10 md:p-14 z-10 max-w-xl">
          <div className="space-y-4 sm:space-y-6">
            <h1 className="text-3xl sm:text-4xl md:text-5xl font-black tracking-tight text-[#1F3347] font-sans">
              CLUBE MARAVILHA
            </h1>

            <p className="text-sm sm:text-base md:text-lg text-slate-700 font-normal leading-relaxed max-w-md">
              Um espaço para encontrar pessoas, praticar esportes, participar da programação e aproveitar momentos em família.
            </p>

            <div className="pt-2">
              <button
                onClick={onOpenPortal}
                className="px-8 py-3.5 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-xs sm:text-sm tracking-wider uppercase shadow-lg shadow-slate-900/20 hover:shadow-slate-900/30 transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:outline-none"
              >
                QUERO SER SÓCIO
              </button>
            </div>
          </div>
        </div>
      </div>
    </section>
  );
};
