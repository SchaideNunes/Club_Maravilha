import React from 'react';
import { Phone, Mail, Instagram, Facebook } from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';

interface FooterProps {
  onOpenPortal?: () => void;
  onNavigateSection?: (sectionId: string) => void;
}

export const Footer: React.FC<FooterProps> = () => {
  return (
    <footer className="bg-[#4E7A9C] text-white pt-14 pb-8 border-t border-slate-300/30">
      <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
        <div className="grid grid-cols-1 md:grid-cols-12 gap-8 pb-10 border-b border-white/20">
          {/* Col 1: Logo & Brand (5 cols) */}
          <div className="md:col-span-5 flex flex-col items-start justify-center">
            <ClubeMaravilhaLogo variant="light" size="lg" />
            <p className="text-xs text-white/80 mt-4 max-w-sm leading-relaxed">
              O espaço definitivo de esporte, lazer e convivência familiar no coração de Teofilândia - BA.
            </p>
          </div>

          {/* Col 2: Contato (4 cols) */}
          <div className="md:col-span-4 space-y-3">
            <h4 className="text-base font-bold text-white tracking-wide">
              Contato
            </h4>
            <ul className="space-y-2 text-sm text-white/90">
              <li>
                <a
                  href="tel:+557583285614"
                  className="hover:text-amber-200 transition-colors flex items-center space-x-2"
                >
                  <Phone className="w-4 h-4 text-amber-300" />
                  <span>(75) 8328-5614</span>
                </a>
              </li>
              <li>
                <a
                  href="https://wa.me/557583285614"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-amber-200 transition-colors flex items-center space-x-2"
                >
                  <span className="w-4 h-4 flex items-center justify-center font-bold text-xs text-amber-300">WA</span>
                  <span>WhatsApp Secretaria</span>
                </a>
              </li>
              <li>
                <a
                  href="mailto:contato@clubemaravilha.com.br"
                  className="hover:text-amber-200 transition-colors flex items-center space-x-2"
                >
                  <Mail className="w-4 h-4 text-amber-300" />
                  <span>contato@clubemaravilha.com.br</span>
                </a>
              </li>
            </ul>
          </div>

          {/* Col 3: Redes Sociais (3 cols) */}
          <div className="md:col-span-3 space-y-3">
            <h4 className="text-base font-bold text-white tracking-wide">
              Redes sociais
            </h4>
            <ul className="space-y-2 text-sm text-white/90">
              <li>
                <a
                  href="https://instagram.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-amber-200 transition-colors flex items-center space-x-2"
                >
                  <Instagram className="w-4 h-4 text-amber-300" />
                  <span>Instagram</span>
                </a>
              </li>
              <li>
                <a
                  href="https://facebook.com"
                  target="_blank"
                  rel="noreferrer"
                  className="hover:text-amber-200 transition-colors flex items-center space-x-2"
                >
                  <Facebook className="w-4 h-4 text-amber-300" />
                  <span>Facebook</span>
                </a>
              </li>
            </ul>
          </div>
        </div>

        {/* Bottom Sub-bar */}
        <div className="pt-6 flex flex-col sm:flex-row items-center justify-between text-xs text-white/70 space-y-2 sm:space-y-0">
          <p>© 2026 Clube Maravilha. Todos os direitos reservados.</p>
          <p>Teofilândia - Bahia</p>
        </div>
      </div>
    </footer>
  );
};
