import React, { useState } from 'react';
import { Menu, X, User, ChevronRight } from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';

export type PageRoute = 'home' | 'esportes' | 'cursos-esportivos' | 'lazer' | 'usuario';

interface NavbarProps {
  onOpenPortal: () => void;
  onNavigateSection?: (sectionId: string) => void;
  currentPage?: PageRoute;
  onNavigatePage?: (page: PageRoute) => void;
}

export const Navbar: React.FC<NavbarProps> = ({
  onOpenPortal,
  onNavigateSection,
  currentPage = 'home',
  onNavigatePage
}) => {
  const [mobileMenuOpen, setMobileMenuOpen] = useState(false);

  const handleLogoClick = () => {
    if (onNavigatePage) {
      onNavigatePage('home');
    } else {
      scrollTo('hero');
    }
  };

  const scrollTo = (id: string) => {
    if (currentPage !== 'home' && onNavigatePage) {
      onNavigatePage('home');
      setTimeout(() => {
        const element = document.getElementById(id);
        if (element) element.scrollIntoView({ behavior: 'smooth' });
      }, 100);
    } else if (onNavigateSection) {
      onNavigateSection(id);
    } else {
      const element = document.getElementById(id);
      if (element) {
        element.scrollIntoView({ behavior: 'smooth' });
      }
    }
    setMobileMenuOpen(false);
  };

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#4E7A9C] shadow-md transition-colors duration-200">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          {/* Brand Logo */}
          <button
            onClick={handleLogoClick}
            className="flex items-center space-x-2 focus:outline-none hover:opacity-95 transition-opacity cursor-pointer"
            aria-label="Clube Maravilha Início"
          >
            <ClubeMaravilhaLogo variant="light" size="md" />
          </button>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center space-x-6">
            <button
              onClick={() => {
                if (currentPage === 'home') scrollTo('programacao-esportes');
                else onNavigatePage?.('esportes');
              }}
              className="text-white text-sm font-medium hover:text-amber-200 transition-colors focus:outline-none cursor-pointer"
            >
              Programação
            </button>

            <button
              onClick={() => onNavigatePage ? onNavigatePage('usuario') : onOpenPortal()}
              className="px-6 py-2.5 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white text-sm font-medium tracking-wide shadow-md transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:outline-none cursor-pointer"
            >
              Área do associado
            </button>

            {/* Subtle Hamburger Menu for Additional Options */}
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-2 text-white hover:text-amber-200 focus:outline-none cursor-pointer"
              aria-label="Abrir Menu"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>

          {/* Mobile Right Buttons */}
          <div className="md:hidden flex items-center space-x-3">
            <button
              onClick={onOpenPortal}
              className="px-3.5 py-2 rounded-full bg-[#1F3347] text-white text-xs font-semibold shadow-sm"
            >
              Área do associado
            </button>
            <button
              onClick={() => setMobileMenuOpen(!mobileMenuOpen)}
              className="p-1.5 text-white hover:text-amber-200"
              aria-label="Menu"
            >
              {mobileMenuOpen ? <X className="w-6 h-6" /> : <Menu className="w-6 h-6 text-white" />}
            </button>
          </div>
        </div>
      </header>

      {/* Mobile Drawer Navigation */}
      {mobileMenuOpen && (
        <div
          className="fixed inset-0 bg-black/50 backdrop-blur-sm z-50 md:hidden"
          onClick={() => setMobileMenuOpen(false)}
        >
          <div
            className="absolute top-0 right-0 w-[80%] max-w-[320px] h-full bg-[#4E7A9C] text-white p-6 shadow-2xl flex flex-col justify-between"
            onClick={(e) => e.stopPropagation()}
          >
            <div>
              <div className="flex items-center justify-between pb-6 border-b border-white/20">
                <ClubeMaravilhaLogo variant="light" size="sm" />
                <button
                  onClick={() => setMobileMenuOpen(false)}
                  className="p-1 text-white hover:text-amber-200"
                >
                  <X className="w-6 h-6" />
                </button>
              </div>

              <nav className="mt-6 space-y-3">
                <button
                  onClick={() => {
                    onNavigatePage ? onNavigatePage('home') : scrollTo('hero');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-left py-2.5 text-sm font-medium flex items-center justify-between border-b border-white/10"
                >
                  <span>Início</span>
                  <ChevronRight className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => {
                    onNavigatePage ? onNavigatePage('esportes') : scrollTo('programacao-esportes');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-left py-2.5 text-sm font-medium flex items-center justify-between border-b border-white/10"
                >
                  <span>Esportes</span>
                  <ChevronRight className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => {
                    onNavigatePage ? onNavigatePage('cursos-esportivos') : scrollTo('experiencias');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-left py-2.5 text-sm font-medium flex items-center justify-between border-b border-white/10"
                >
                  <span>Cursos Esportivos</span>
                  <ChevronRight className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => {
                    onNavigatePage ? onNavigatePage('lazer') : scrollTo('programacao-lazer');
                    setMobileMenuOpen(false);
                  }}
                  className="w-full text-left py-2.5 text-sm font-medium flex items-center justify-between border-b border-white/10"
                >
                  <span>Lazer</span>
                  <ChevronRight className="w-4 h-4 text-white/70" />
                </button>
                <button
                  onClick={() => scrollTo('sobre')}
                  className="w-full text-left py-2.5 text-sm font-medium flex items-center justify-between border-b border-white/10"
                >
                  <span>Sobre o Clube</span>
                  <ChevronRight className="w-4 h-4 text-white/70" />
                </button>
              </nav>
            </div>

            <div className="pt-6 border-t border-white/20 space-y-3">
              <button
                onClick={() => {
                  setMobileMenuOpen(false);
                  if (onNavigatePage) onNavigatePage('usuario');
                  else onOpenPortal();
                }}
                className="w-full py-3 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-sm tracking-wide shadow-lg flex items-center justify-center space-x-2 cursor-pointer"
              >
                <User className="w-4 h-4" />
                <span>Acessar Área do Associado</span>
              </button>
              <p className="text-center text-xs text-white/80">Teofilândia - BA</p>
            </div>
          </div>
        </div>
      )}
    </>
  );
};
