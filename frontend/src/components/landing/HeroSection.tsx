import { ArrowRight, Calendar } from 'lucide-react';
import homepageImg from '../../assets/Homepage.png';

interface HeroSectionProps {
  onOpenPortal: () => void;
  onExploreFacilities: () => void;
}

export const HeroSection: React.FC<HeroSectionProps> = ({ 
  onOpenPortal, 
  onExploreFacilities 
}) => {
  return (
    <section id="hero" className="relative min-h-screen flex items-center justify-center overflow-hidden">
      {/* Background Image: Homepage.png */}
      <div className="absolute inset-0 z-0">
        <img
          src={homepageImg}
          alt="Club Maravilha ao pôr do sol"
          className="w-full h-full object-cover object-center scale-105 animate-fade-in filter brightness-[0.88]"
        />
        {/* Subtle Vignette & Gradient Overlays para Máximo Contraste e Leitura Sofisticada */}
        <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-slate-950/40 to-slate-950/60" />
        <div className="absolute inset-0 bg-radial-vignette opacity-50" />
      </div>

      {/* Conteúdo Central Hero (Estilo AMOJA: Nome do Clube em Destaque Imponente + CTA) */}
      <div className="relative z-10 max-w-5xl mx-auto px-6 text-center pt-28 pb-32 flex flex-col items-center">

        {/* Título Principal Imponente: CLUB MARAVILHA */}
        <h1 className="font-serif text-5xl sm:text-7xl md:text-8xl font-normal tracking-wide text-white drop-shadow-[0_10px_25px_rgba(0,0,0,0.8)] leading-[1.08] mb-6">
          Club Maravilha
        </h1>

        {/* Subtítulo Elegante */}
        <p className="max-w-2xl mx-auto text-base sm:text-xl text-slate-200/90 font-light tracking-wide leading-relaxed drop-shadow-md mb-10">
          Onde o alto rendimento esportivo encontra a tranquilidade de um resort exclusivo. 
          Quadras oficiais, complexo aquático e convivência para você e sua família.
        </p>

        {/* CTAs Centrais em Vidro & Âmbar */}
        <div className="flex flex-col sm:flex-row items-center justify-center gap-4 w-full max-w-md">
          <button
            onClick={onExploreFacilities}
            className="w-full sm:w-auto px-8 py-4 rounded-full bg-white/10 hover:bg-white/20 backdrop-blur-md border border-white/30 text-white font-medium text-xs tracking-widest uppercase transition-all duration-300 transform hover:scale-105 shadow-xl shadow-black/30 flex items-center justify-center space-x-2"
          >
            <span>Explorar Estrutura</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>

          <button
            onClick={onOpenPortal}
            className="w-full sm:w-auto px-8 py-4 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold text-xs tracking-widest uppercase transition-all duration-300 transform hover:scale-105 shadow-xl shadow-amber-950/40 flex items-center justify-center space-x-2"
          >
            <Calendar className="w-3.5 h-3.5" />
            <span>Reservar Quadra</span>
          </button>
        </div>
      </div>

      {/* Floating Bottom Bar: Métricas de Alto Nível */}
      <div className="absolute bottom-0 left-0 right-0 z-20 bg-gradient-to-t from-slate-950 via-slate-950/90 to-transparent pt-12 pb-6 px-6">
        <div className="max-w-6xl mx-auto grid grid-cols-2 md:grid-cols-4 gap-4 sm:gap-6 border-t border-white/10 pt-6">
          <div className="text-center sm:text-left">
            <span className="block font-serif text-2xl sm:text-3xl font-semibold text-amber-300">~300</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-light">Sócios Titulares</span>
          </div>

          <div className="text-center sm:text-left">
            <span className="block font-serif text-2xl sm:text-3xl font-semibold text-white">5 Quadras</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-light">Tênis, Beach & Futebol</span>
          </div>

          <div className="text-center sm:text-left">
            <span className="block font-serif text-2xl sm:text-3xl font-semibold text-white">Semi-Olímpica</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-light">Piscina & Deck Molhado</span>
          </div>

          <div className="text-center sm:text-left">
            <span className="block font-serif text-2xl sm:text-3xl font-semibold text-emerald-400">100% Digital</span>
            <span className="text-xs uppercase tracking-wider text-slate-400 font-light">Catraca Facial & Pix 2s</span>
          </div>
        </div>
      </div>
    </section>
  );
};
