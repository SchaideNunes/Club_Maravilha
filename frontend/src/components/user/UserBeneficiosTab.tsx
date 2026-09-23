import {
  Waves,
  Trophy,
  Ticket,
  Users,
  Wifi,
  Sparkles,
  ShoppingBag,
  Flame,
  CheckCircle2
} from 'lucide-react';

export const UserBeneficiosTab: React.FC = () => {
  const benefits = [
    {
      icon: Waves,
      title: 'Parque Aquático Completo',
      desc: 'Acesso livre e irrestrito às piscinas adulto, toboágua infantil e raia semiolímpica para treinos e relaxamento.'
    },
    {
      icon: Trophy,
      title: 'Arenas & Quadras Esportivas',
      desc: 'Direito a agendar quadras de Beach Tennis de areia tratada, Campo Society e Quadra Poliesportiva Coberta.'
    },
    {
      icon: Users,
      title: '8 Convites Gratuitos / Mês',
      desc: 'Traga familiares e amigos todo mês sem custo extra. Uma economia garantida de até R$ 200,00 mensais.'
    },
    {
      icon: Ticket,
      title: '50% OFF em Grandes Shows',
      desc: 'Meia-entrada automática e fila VIP exclusiva em todos os eventos e festivais promovidos no Club Maravilha.'
    },
    {
      icon: Flame,
      title: 'Quiosques com Churrasqueira',
      desc: 'Espaços gourmet completos com freezer, mesas e churrasqueiras para celebrar momentos especiais em família.'
    },
    {
      icon: Wifi,
      title: 'Wi-Fi 6 de Alta Densidade',
      desc: 'Conexão ultraveloz em 100% da área do clube, permitindo trabalhar ou navegar com máxima estabilidade.'
    },
    {
      icon: ShoppingBag,
      title: 'Rede de Parcerias em Teofilândia',
      desc: 'Descontos de até 25% em academias parceiras, postos de combustível, farmácias e clínicas conveniadas.'
    },
    {
      icon: Sparkles,
      title: 'Acesso Facial sem Filas',
      desc: 'Portaria 100% automatizada por reconhecimento biométrico facial, dispensando crachás ou filas na recepção.'
    }
  ];

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Vantagens do Associado</span>
          <span>•</span>
          <span>Plano Ouro</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Benefícios & Vantagens Exclusivas
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Descubra todos os privilégios inclusos no seu plano e aproveite ao máximo a experiência no Club Maravilha.
        </p>
      </div>

      {/* Grid de Benefícios */}
      <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {benefits.map((b, idx) => {
          const Icon = b.icon;
          return (
            <div
              key={idx}
              className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-sm hover:shadow-md transition-all flex flex-col justify-between space-y-4"
            >
              <div className="space-y-3">
                <div className="w-12 h-12 rounded-2xl bg-[#EBF4FA] text-[#1B3B54] flex items-center justify-center shadow-xs">
                  <Icon className="w-6 h-6" />
                </div>
                <h3 className="font-bold text-[#1B3B54] text-base">{b.title}</h3>
                <p className="text-xs text-slate-500 leading-relaxed">{b.desc}</p>
              </div>

              <div className="pt-3 border-t border-slate-100 flex items-center space-x-1.5 text-xs text-emerald-700 font-bold">
                <CheckCircle2 className="w-4 h-4 text-emerald-600" />
                <span>Incluso no Plano Familiar</span>
              </div>
            </div>
          );
        })}
      </div>
    </div>
  );
};
