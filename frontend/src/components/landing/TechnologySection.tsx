import { 
  Zap, 
  ShieldCheck, 
  QrCode, 
  Cpu, 
  Check, 
  Smartphone,
  ArrowRight
} from 'lucide-react';

interface TechnologySectionProps {
  onOpenPortal: () => void;
}

export const TechnologySection: React.FC<TechnologySectionProps> = ({ onOpenPortal }) => {
  const techPillars = [
    {
      icon: Zap,
      badge: 'Tempo Real • < 2s',
      badgeColor: 'text-amber-400 bg-amber-400/10 border-amber-400/20',
      title: 'Baixa Pix Instantânea & Webhooks',
      desc: 'Pague sua mensalidade via Pix Dinâmico e tenha a baixa confirmada em menos de 2 segundos. Sem necessidade de enviar comprovantes pelo WhatsApp ou aguardar conferência manual da secretaria.',
      highlights: [
        'Chave Pix Copia e Cola gerada com txid exclusivo',
        'Conciliação automatizada por Webhook criptografado',
        'Desbloqueio imediato na catraca física pós-pagamento',
      ],
    },
    {
      icon: ShieldCheck,
      badge: 'Rede Local Offline',
      badgeColor: 'text-purple-400 bg-purple-400/10 border-purple-400/20',
      title: 'Catraca Facial com Lista Branca',
      desc: 'Acesso fluido e sem atritos através de biometria facial de alta precisão. A controladora opera em modo lista branca local sincronizada, garantindo abertura mesmo sem conexão com a internet externa.',
      highlights: [
        'Reconhecimento veloz em menos de 300ms',
        'Histórico transparente de acessos no portal do sócio',
        'Sincronização imediata de novos sócios e dependentes',
      ],
    },
    {
      icon: QrCode,
      badge: 'Franquia Mensal de 8',
      badgeColor: 'text-emerald-400 bg-emerald-400/10 border-emerald-400/20',
      title: 'Convites Digitais com QR Code',
      desc: 'Todo sócio titular tem direito a até 8 convites mensais gratuitos (reiniciados a cada dia 1º). Emita o passe do seu convidado em 1 minuto e envie o QR Code temporário diretamente pelo WhatsApp.',
      highlights: [
        'QR Code com token criptográfico de uso único',
        'Acesso restrito estritamente à data da visita marcada',
        'Faturamento de convites excedentes agregado no próximo Pix',
      ],
    },
  ];

  return (
    <section id="technology" className="py-24 bg-slate-900/60 border-y border-white/5 relative overflow-hidden">
      <div className="max-w-7xl mx-auto px-6 relative z-10">
        {/* Section Header */}
        <div className="text-center max-w-3xl mx-auto mb-16">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-emerald-500/10 border border-emerald-500/20 text-emerald-400 text-xs font-semibold uppercase tracking-widest mb-4">
            <Cpu className="w-3.5 h-3.5" />
            <span>Tecnologia & Gestão Invisível</span>
          </div>
          <h2 className="font-serif text-3xl sm:text-5xl font-normal tracking-tight text-white mb-6">
            O Clube Mais Conectado e Ágil do Brasil
          </h2>
          <p className="text-slate-400 text-sm sm:text-base font-light leading-relaxed">
            Eliminamos burocracias, filas na portaria e checagens manuais de comprovantes. 
            Toda a infraestrutura trabalha de forma silenciosa para que você aproveite o clube ao máximo.
          </p>
        </div>

        {/* 3 Pillars Grid */}
        <div className="grid grid-cols-1 md:grid-cols-3 gap-8 mb-16">
          {techPillars.map((item, idx) => {
            const Icon = item.icon;
            return (
              <div
                key={idx}
                className="bg-slate-950/70 border border-white/10 hover:border-amber-400/30 rounded-3xl p-8 transition-all duration-300 flex flex-col justify-between group shadow-xl hover:shadow-2xl"
              >
                <div>
                  <div className="flex items-center justify-between mb-6">
                    <div className="w-12 h-12 rounded-2xl bg-slate-900 border border-white/10 flex items-center justify-center text-amber-400 group-hover:scale-110 transition-transform duration-300 shadow-md">
                      <Icon className="w-6 h-6" />
                    </div>
                    <span className={`text-[11px] font-semibold px-3 py-1 rounded-full border ${item.badgeColor}`}>
                      {item.badge}
                    </span>
                  </div>

                  <h3 className="font-serif text-xl sm:text-2xl text-white font-normal mb-3">
                    {item.title}
                  </h3>

                  <p className="text-slate-400 text-xs sm:text-sm font-light leading-relaxed mb-6">
                    {item.desc}
                  </p>

                  <div className="space-y-2.5 pt-4 border-t border-white/5">
                    {item.highlights.map((point, pIdx) => (
                      <div key={pIdx} className="flex items-start space-x-2 text-xs text-slate-300">
                        <Check className="w-3.5 h-3.5 text-emerald-400 shrink-0 mt-0.5" />
                        <span>{point}</span>
                      </div>
                    ))}
                  </div>
                </div>

                <div className="pt-6 mt-6 border-t border-white/5 flex items-center justify-between text-xs text-amber-400 font-medium">
                  <span>Módulo Integrado</span>
                  <span className="group-hover:translate-x-1 transition-transform flex items-center space-x-1">
                    <span>Ver no Portal</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Interactive Banner to Open Portal */}
        <div className="bg-gradient-to-r from-slate-950 via-slate-900 to-amber-950/40 border border-amber-500/20 rounded-3xl p-8 sm:p-10 flex flex-col sm:flex-row items-center justify-between gap-6 shadow-2xl">
          <div className="space-y-2 text-center sm:text-left">
            <span className="text-amber-400 text-xs uppercase tracking-widest font-semibold block">
              Autoatendimento para Associados
            </span>
            <h3 className="font-serif text-2xl sm:text-3xl text-white font-normal">
              Experimente o Portal do Associado
            </h3>
            <p className="text-slate-400 text-xs sm:text-sm max-w-xl font-light">
              Acesse a grade de quadras, verifique o status da sua mensalidade com Pix Copia e Cola e emita convites de convidados com QR Code em tempo real.
            </p>
          </div>

          <button
            onClick={onOpenPortal}
            className="px-8 py-4 rounded-full bg-gradient-to-r from-amber-500 to-amber-600 hover:from-amber-400 hover:to-amber-500 text-slate-950 font-bold text-xs uppercase tracking-widest whitespace-nowrap shadow-xl shadow-amber-950/50 transition-all transform hover:scale-105 flex items-center space-x-2"
          >
            <Smartphone className="w-4 h-4" />
            <span>Acessar Portal do Sócio</span>
          </button>
        </div>
      </div>
    </section>
  );
};
