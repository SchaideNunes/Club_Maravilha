import { useState } from 'react';
import { 
  Trophy, 
  SunMedium, 
  Waves, 
  Activity, 
  Sparkles, 
  CheckCircle2, 
  ArrowRight,
  Clock
} from 'lucide-react';
import poolImg from '../../assets/Image1.png';

interface FacilitiesSectionProps {
  onSelectCourtForBooking: (courtName: string) => void;
}

export const FacilitiesSection: React.FC<FacilitiesSectionProps> = ({ 
  onSelectCourtForBooking 
}) => {
  const [activeTab, setActiveTab] = useState<'aquatico' | 'beach' | 'tenis' | 'society'>('aquatico');

  const facilitiesData = {
    aquatico: {
      title: 'Complexo Aquático & Deck Molhado',
      category: 'Lazer & Natação',
      desc: 'Piscina semi-olímpica com raias exclusivas para natação matinal, deck molhado com espreguiçadeiras imersas e lounge gourmet com serviço de bar ao pôr do sol.',
      features: [
        'Raias oficiais para treinamento e natação livre',
        'Deck molhado com pergolado em madeira nobre e sofás integrados',
        'Tratamento com ozônio suave para pele e olhos',
        'Espaço bistrô com cardápio leve e bebidas artesanais',
      ],
      hours: '06h00 às 22h00 • Todos os dias',
      actionText: 'Ver Regras de Acesso',
    },
    beach: {
      title: 'Arena de Beach Tennis & Futevôlei',
      category: 'Esportes de Areia',
      desc: 'Duas quadras de areia branca selecionada com drenagem de alta absorção e iluminação profissional em LED, perfeitas para partidas diurnas ou ao entardecer.',
      features: [
        '2 quadras oficiais com redes profissionais regulamentares',
        'Iluminação de 500 lux sem pontos cegos para jogos noturnos',
        'Ducha privativa e quiosque de hidratação exclusivo',
        'Sistema de agendamento online com confirmação imediata',
      ],
      hours: '06h00 às 22h00 • Reserva pelo portal',
      actionText: 'Reservar Beach Tennis',
    },
    tenis: {
      title: 'Quadras Oficiais de Tênis',
      category: 'Tênis Clássico',
      desc: 'Piso rápido e saibro com manutenção diária especializada, oferecendo velocidade ideal e proteção às articulações dos associados.',
      features: [
        'Quadras com medidas oficiais da Federação Internacional de Tênis',
        'Fundo escuro contrastante para visibilidade máxima da bola',
        'Bancos de descanso sombreados e bebedouro refrigerado',
        'Trava de concorrência que impede double-booking de horários',
      ],
      hours: '06h00 às 22h00 • Agendamento com até 7 dias de antecedência',
      actionText: 'Reservar Tênis',
    },
    society: {
      title: 'Campo Society & Arena Poliesportiva',
      category: 'Futebol & Basquete',
      desc: 'Grama sintética de padrão FIFA com amortecimento especial e quadra acrílica poliesportiva para basquete e futsal entre amigos.',
      features: [
        'Grama sintética monofilamento com preenchimento em borracha ecológica',
        'Tabelas de basquete profissionais em vidro temperado',
        'Vestiários modernos com duchas aquecidas adjacentes',
        'Espaço para churrasco e confraternizações pós-jogo',
      ],
      hours: '07h00 às 22h00 • Reserva por períodos de 1h ou 2h',
      actionText: 'Reservar Society',
    },
  };

  const current = facilitiesData[activeTab];

  return (
    <section id="facilities" className="py-24 bg-slate-950 text-slate-100 relative">
      {/* Decorative Glow */}
      <div className="absolute top-0 right-1/4 w-96 h-96 bg-amber-500/5 rounded-full blur-3xl pointer-events-none" />
      <div className="absolute bottom-0 left-1/4 w-96 h-96 bg-emerald-500/5 rounded-full blur-3xl pointer-events-none" />

      <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 relative z-10">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <span className="text-amber-400 font-serif text-sm tracking-widest uppercase block mb-3 font-semibold">
            Infraestrutura de Alto Padrão
          </span>
          <h2 className="font-serif text-3xl sm:text-5xl font-normal tracking-tight text-white mb-6">
            Espaços Projetados para o Bem-Estar e a Performance
          </h2>
          <p className="text-slate-400 text-sm sm:text-base font-light leading-relaxed">
            Cada detalhe do Club Maravilha foi planejado para oferecer uma experiência exclusiva de lazer, 
            treinamento e convivência para os nossos ~300 associados e suas famílias.
          </p>
        </div>

        {/* Navigation Tabs */}
        <div className="flex items-center justify-center gap-2 sm:gap-3 flex-wrap mb-12">
          <button
            onClick={() => setActiveTab('aquatico')}
            className={`px-6 py-3 rounded-full text-xs uppercase tracking-wider font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'aquatico'
                ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-950/40'
                : 'bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 hover:bg-slate-800'
            }`}
          >
            <Waves className="w-3.5 h-3.5" />
            <span>Complexo Aquático</span>
          </button>

          <button
            onClick={() => setActiveTab('beach')}
            className={`px-6 py-3 rounded-full text-xs uppercase tracking-wider font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'beach'
                ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-950/40'
                : 'bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 hover:bg-slate-800'
            }`}
          >
            <SunMedium className="w-3.5 h-3.5" />
            <span>Beach Tennis</span>
          </button>

          <button
            onClick={() => setActiveTab('tenis')}
            className={`px-6 py-3 rounded-full text-xs uppercase tracking-wider font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'tenis'
                ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-950/40'
                : 'bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 hover:bg-slate-800'
            }`}
          >
            <Trophy className="w-3.5 h-3.5" />
            <span>Quadras de Tênis</span>
          </button>

          <button
            onClick={() => setActiveTab('society')}
            className={`px-6 py-3 rounded-full text-xs uppercase tracking-wider font-semibold transition-all duration-300 flex items-center space-x-2 ${
              activeTab === 'society'
                ? 'bg-amber-500 text-slate-950 shadow-lg shadow-amber-950/40'
                : 'bg-slate-900/80 text-slate-300 hover:text-white border border-white/10 hover:bg-slate-800'
            }`}
          >
            <Activity className="w-3.5 h-3.5" />
            <span>Campo Society</span>
          </button>
        </div>

        {/* Feature Detail Card */}
        <div className="bg-slate-900/60 border border-white/10 rounded-3xl overflow-hidden shadow-2xl backdrop-blur-md grid grid-cols-1 lg:grid-cols-12 items-center">
          {/* Visual Showcase (Photo) */}
          <div className="lg:col-span-7 h-80 sm:h-96 lg:h-[480px] relative overflow-hidden group">
            <img
              src={poolImg}
              alt="Instalações do Club Maravilha"
              className="w-full h-full object-cover object-center group-hover:scale-105 transition-transform duration-700 filter brightness-95"
            />
            <div className="absolute inset-0 bg-gradient-to-t from-slate-950 via-transparent to-transparent opacity-60" />
            
            <div className="absolute bottom-6 left-6 right-6 flex items-center justify-between text-xs text-white/90 bg-slate-950/70 backdrop-blur-md px-4 py-2.5 rounded-2xl border border-white/10">
              <span className="flex items-center space-x-2">
                <Clock className="w-4 h-4 text-amber-400" />
                <span>{current.hours}</span>
              </span>
              <span className="text-amber-400 font-medium">Exclusivo ~300 Sócios</span>
            </div>
          </div>

          {/* Text Description & Feature List */}
          <div className="lg:col-span-5 p-8 sm:p-10 flex flex-col justify-between">
            <div>
              <div className="flex items-center space-x-2 text-amber-400 text-xs uppercase tracking-widest font-semibold mb-2">
                <Sparkles className="w-3.5 h-3.5" />
                <span>{current.category}</span>
              </div>
              <h3 className="font-serif text-2xl sm:text-3xl text-white font-normal mb-4">
                {current.title}
              </h3>
              <p className="text-slate-300 text-sm font-light leading-relaxed mb-6">
                {current.desc}
              </p>

              <div className="space-y-3 mb-8">
                {current.features.map((feat, i) => (
                  <div key={i} className="flex items-start space-x-3 text-xs sm:text-sm text-slate-300">
                    <CheckCircle2 className="w-4 h-4 text-emerald-400 shrink-0 mt-0.5" />
                    <span>{feat}</span>
                  </div>
                ))}
              </div>
            </div>

            <button
              onClick={() => onSelectCourtForBooking(current.title)}
              className="w-full py-3.5 rounded-xl bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-semibold text-xs tracking-wider uppercase flex items-center justify-center space-x-2 shadow-lg shadow-amber-950/40 transition-all transform hover:-translate-y-0.5"
            >
              <span>{current.actionText}</span>
              <ArrowRight className="w-4 h-4" />
            </button>
          </div>
        </div>
      </div>
    </section>
  );
};
