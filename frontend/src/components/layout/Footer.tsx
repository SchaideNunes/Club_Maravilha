import { Phone, Mail, MapPin, Clock, ShieldCheck } from 'lucide-react';

interface FooterProps {
  onOpenPortal: () => void;
  onNavigateSection: (sectionId: string) => void;
}

export const Footer: React.FC<FooterProps> = ({ onOpenPortal, onNavigateSection }) => {
  return (
    <footer id="contact" className="bg-slate-950 border-t border-white/10 text-slate-400 text-xs font-light">
      <div className="max-w-7xl mx-auto px-6 py-16">
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-5 gap-10 mb-14">
          {/* Brand & Overview */}
          <div className="lg:col-span-2 space-y-4">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-full border border-amber-400/40 bg-amber-950/30 flex items-center justify-center text-amber-400 font-serif font-bold text-lg">
                CM
              </div>
              <span className="font-serif tracking-widest2 text-xl font-medium text-white uppercase">
                Club Maravilha
              </span>
            </div>

            <p className="text-slate-400 text-xs leading-relaxed max-w-sm">
              Um refúgio esportivo e social privativo para cerca de 300 associados. 
              Quadras oficiais, complexo aquático e uma gestão moderna com Pix instantâneo e acesso facial.
            </p>

            <div className="pt-2 flex items-center space-x-2 text-emerald-400 text-xs">
              <ShieldCheck className="w-4 h-4" />
              <span>Ambiente Monitorado & Acesso Facial Controlado</span>
            </div>
          </div>

          {/* Navegação Rápida */}
          <div className="space-y-3">
            <span className="font-serif text-sm font-semibold text-white uppercase tracking-wider block mb-4">
              Navegação
            </span>
            <ul className="space-y-2.5">
              <li>
                <button 
                  onClick={() => onNavigateSection('hero')} 
                  className="hover:text-amber-400 transition-colors"
                >
                  Página Inicial
                </button>
              </li>
              <li>
                <button 
                  onClick={() => onNavigateSection('facilities')} 
                  className="hover:text-amber-400 transition-colors"
                >
                  Complexo Esportivo
                </button>
              </li>
              <li>
                <button 
                  onClick={() => onNavigateSection('technology')} 
                  className="hover:text-amber-400 transition-colors"
                >
                  Tecnologia & Catraca
                </button>
              </li>
              <li>
                <button 
                  onClick={onOpenPortal} 
                  className="text-amber-400 hover:text-amber-300 font-medium transition-colors"
                >
                  Portal do Associado →
                </button>
              </li>
            </ul>
          </div>

          {/* Horários */}
          <div className="space-y-3">
            <span className="font-serif text-sm font-semibold text-white uppercase tracking-wider block mb-4">
              Horários
            </span>
            <ul className="space-y-2.5">
              <li className="flex items-start space-x-2">
                <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>Quadras: 06h00 às 22h00</span>
              </li>
              <li className="flex items-start space-x-2">
                <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>Piscina: 06h00 às 21h00</span>
              </li>
              <li className="flex items-start space-x-2">
                <Clock className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>Secretaria: 08h00 às 18h00</span>
              </li>
            </ul>
          </div>

          {/* Contato & Localização */}
          <div className="space-y-3">
            <span className="font-serif text-sm font-semibold text-white uppercase tracking-wider block mb-4">
              Secretaria
            </span>
            <ul className="space-y-2.5">
              <li className="flex items-center space-x-2">
                <Phone className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span>+55 (11) 99999-8888</span>
              </li>
              <li className="flex items-center space-x-2">
                <Mail className="w-3.5 h-3.5 text-amber-400 shrink-0" />
                <span>secretaria@clubmaravilha.com.br</span>
              </li>
              <li className="flex items-start space-x-2">
                <MapPin className="w-3.5 h-3.5 text-amber-400 shrink-0 mt-0.5" />
                <span>Av. das Palmeiras, 1500 • Bairro Nobre</span>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Bar */}
        <div className="pt-8 border-t border-white/5 flex flex-col sm:flex-row items-center justify-between text-slate-400 gap-4">
          <p>© 2026 Club Maravilha. Todos os direitos reservados. Exclusivo para associados.</p>
          <p className="text-[11px] text-slate-400">Sistema Integrado de Gestão Esportiva • FastAPI + React</p>
        </div>
      </div>
    </footer>
  );
};
