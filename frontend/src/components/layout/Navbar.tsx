import React, { useState, useEffect } from 'react';
import {
  Menu,
  X,
  User,
  ChevronRight,
  Home,
  Trophy,
  GraduationCap,
  Palmtree,
  Calendar,
  Info
} from 'lucide-react';
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
  const [menuOpen, setMenuOpen] = useState(false);

  // Close menu on Escape key press
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key === 'Escape') setMenuOpen(false);
    };
    if (menuOpen) {
      document.addEventListener('keydown', handleKeyDown);
      document.body.style.overflow = 'hidden';
    } else {
      document.body.style.overflow = '';
    }
    return () => {
      document.removeEventListener('keydown', handleKeyDown);
      document.body.style.overflow = '';
    };
  }, [menuOpen]);

  const handleLogoClick = () => {
    setMenuOpen(false);
    if (onNavigatePage) {
      onNavigatePage('home');
    } else {
      scrollTo('hero');
    }
  };

  const handlePageNavigation = (page: PageRoute) => {
    setMenuOpen(false);
    if (onNavigatePage) {
      onNavigatePage(page);
    }
  };

  const scrollTo = (id: string) => {
    setMenuOpen(false);
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
  };

  const menuItems = [
    {
      id: 'home',
      label: 'Início',
      icon: Home,
      action: () => handlePageNavigation('home'),
      active: currentPage === 'home'
    },
    {
      id: 'esportes',
      label: 'Esportes',
      icon: Trophy,
      action: () => handlePageNavigation('esportes'),
      active: currentPage === 'esportes'
    },
    {
      id: 'cursos-esportivos',
      label: 'Cursos Esportivos',
      icon: GraduationCap,
      action: () => handlePageNavigation('cursos-esportivos'),
      active: currentPage === 'cursos-esportivos'
    },
    {
      id: 'lazer',
      label: 'Lazer',
      icon: Palmtree,
      action: () => handlePageNavigation('lazer'),
      active: currentPage === 'lazer'
    },
    {
      id: 'programacao',
      label: 'Programação',
      icon: Calendar,
      action: () => {
        if (currentPage === 'home') scrollTo('programacao-esportes');
        else handlePageNavigation('esportes');
      },
      active: false
    },
    {
      id: 'usuario',
      label: 'Área do Associado',
      icon: User,
      action: () => handlePageNavigation('usuario'),
      active: currentPage === 'usuario'
    },
    {
      id: 'sobre',
      label: 'Sobre o Clube',
      icon: Info,
      action: () => scrollTo('sobre'),
      active: false
    }
  ];

  return (
    <>
      <header className="sticky top-0 z-40 bg-[#6899BA] shadow-sm transition-colors duration-200">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 h-20 flex items-center justify-between">
          {/* Brand Logo */}
          <button
            onClick={handleLogoClick}
            className="flex items-center space-x-2 focus:outline-none hover:opacity-95 transition-opacity cursor-pointer"
            aria-label="Clube Maravilha Início"
          >
            <ClubeMaravilhaLogo variant="on-blue" size="md" />
          </button>

          {/* Desktop Right Actions */}
          <div className="hidden md:flex items-center space-x-6">
            <button
              onClick={() => {
                if (currentPage === 'home') scrollTo('programacao-esportes');
                else onNavigatePage?.('esportes');
              }}
              className="text-white hover:text-amber-200 text-sm font-semibold transition-colors focus:outline-none cursor-pointer"
            >
              Programação
            </button>

            <button
              onClick={() => onNavigatePage ? onNavigatePage('usuario') : onOpenPortal()}
              className="px-6 py-2.5 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white text-sm font-semibold tracking-wide shadow-md transition-all transform hover:-translate-y-0.5 active:translate-y-0 focus:outline-none cursor-pointer"
            >
              Área do associado
            </button>

            {/* Desktop Hamburger Button */}
            <button
              onClick={() => setMenuOpen(true)}
              className="p-2 text-white hover:text-amber-200 hover:bg-white/10 rounded-xl focus:outline-none cursor-pointer transition-colors"
              aria-label="Abrir Menu de Navegação"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>

          {/* Mobile Right Buttons */}
          <div className="md:hidden flex items-center space-x-3">
            <button
              onClick={() => onNavigatePage ? onNavigatePage('usuario') : onOpenPortal()}
              className="px-3.5 py-2 rounded-full bg-[#1F3347] text-white text-xs font-semibold shadow-sm cursor-pointer"
            >
              Área do associado
            </button>
            <button
              onClick={() => setMenuOpen(true)}
              className="p-1.5 text-white hover:bg-white/10 rounded-lg cursor-pointer"
              aria-label="Menu"
            >
              <Menu className="w-6 h-6 text-white" />
            </button>
          </div>
        </div>
      </header>

      {/* Slide-over Backdrop (Fades in/out) */}
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-xs z-50 transition-opacity duration-300 ease-out ${
          menuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setMenuOpen(false)}
        aria-hidden={!menuOpen}
      >
        {/* Slide-over Panel (Slides in from right) */}
        <div
          className={`absolute top-0 right-0 w-[85%] max-w-[360px] h-full bg-[#132A3E] text-white p-6 sm:p-7 shadow-2xl flex flex-col justify-between transform transition-transform duration-300 ease-out ${
            menuOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <div>
            {/* Drawer Header with Logo and Close Button */}
            <div className="flex items-center justify-between pb-5 border-b border-white/20">
              <div className="bg-white/95 px-3 py-1.5 rounded-2xl shadow-xs">
                <ClubeMaravilhaLogo variant="default" size="sm" />
              </div>
              <button
                onClick={() => setMenuOpen(false)}
                className="p-2 rounded-lg text-white/80 hover:text-white hover:bg-white/10 transition-colors cursor-pointer"
                aria-label="Fechar Menu"
              >
                <X className="w-6 h-6" />
              </button>
            </div>

            {/* Navigation Menu List */}
            <nav className="mt-6 space-y-2">
              {menuItems.map((item) => {
                const Icon = item.icon;
                return (
                  <button
                    key={item.id}
                    onClick={item.action}
                    className={`w-full flex items-center justify-between px-3.5 py-3 rounded-xl text-sm font-semibold transition-all duration-200 cursor-pointer group ${
                      item.active
                        ? 'bg-white/20 text-white shadow-xs'
                        : 'text-white/90 hover:bg-white/10 hover:text-white hover:translate-x-1'
                    }`}
                  >
                    <div className="flex items-center space-x-3.5">
                      <Icon className={`w-5 h-5 ${item.active ? 'text-amber-300' : 'text-white/80 group-hover:text-amber-300 transition-colors'}`} />
                      <span>{item.label}</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/60 group-hover:text-white transition-colors" />
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Drawer Footer CTA */}
          <div className="pt-6 border-t border-white/20 space-y-3">
            <button
              onClick={() => handlePageNavigation('usuario')}
              className="w-full py-3 rounded-full bg-[#1F3347] hover:bg-[#162737] text-white font-bold text-sm tracking-wide shadow-lg flex items-center justify-center space-x-2 transition-all transform hover:-translate-y-0.5 active:translate-y-0 cursor-pointer"
            >
              <User className="w-4 h-4 text-amber-300" />
              <span>Acessar Área do Associado</span>
            </button>
            <p className="text-center text-xs text-white/70 tracking-wide">
              Clube Maravilha • Teofilândia - BA
            </p>
          </div>
        </div>
      </div>
    </>
  );
};

