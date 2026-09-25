import React, { useState, useEffect } from 'react';
import {
  ChevronDown,
  Menu,
  X,
  Home,
  Trophy,
  GraduationCap,
  Palmtree,
  User,
  ArrowLeft,
  ChevronRight,
  ShieldCheck
} from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';
import { UserSidebar } from './UserSidebar';
import { Footer } from '../layout/Footer';
import { PageRoute } from '../layout/Navbar';

// Subcomponentes de abas
import { UserOverviewTab } from './UserOverviewTab';
import { UserCarteirinhaTab } from './UserCarteirinhaTab';
import { UserFinanceiroTab } from './UserFinanceiroTab';
import { UserReservasTab } from './UserReservasTab';
import { UserFamiliaTab } from './UserFamiliaTab';
import { UserEventosTab } from './UserEventosTab';
import { UserBeneficiosTab } from './UserBeneficiosTab';
import { UserContaTab } from './UserContaTab';

interface UserDashboardPageProps {
  onBackToHome: () => void;
  onNavigatePage?: (page: PageRoute) => void;
  onOpenBookingModal: (courtName?: string) => void;
  onOpenPaymentModal: () => void;
}

export const UserDashboardPage: React.FC<UserDashboardPageProps> = ({
  onBackToHome,
  onNavigatePage,
  onOpenBookingModal,
  onOpenPaymentModal
}) => {
  const [currentTab, setCurrentTab] = useState('inicio');
  const [menuOpen, setMenuOpen] = useState(false);

  // Fecha o menu hamburguer com a tecla ESC
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

  const handlePageNavigation = (page: PageRoute) => {
    setMenuOpen(false);
    if (onNavigatePage) {
      onNavigatePage(page);
    } else if (page === 'home') {
      onBackToHome();
    }
  };

  const menuItems = [
    {
      id: 'home',
      label: 'Início (Portal)',
      icon: Home,
      action: () => handlePageNavigation('home')
    },
    {
      id: 'esportes',
      label: 'Esportes',
      icon: Trophy,
      action: () => handlePageNavigation('esportes')
    },
    {
      id: 'cursos-esportivos',
      label: 'Cursos Esportivos',
      icon: GraduationCap,
      action: () => handlePageNavigation('cursos-esportivos')
    },
    {
      id: 'lazer',
      label: 'Lazer & Shows',
      icon: Palmtree,
      action: () => handlePageNavigation('lazer')
    },
    {
      id: 'usuario',
      label: 'Área do Associado',
      icon: User,
      action: () => setMenuOpen(false),
      active: true
    },
    {
      id: 'admin',
      label: 'Painel da Diretoria (Admin)',
      icon: ShieldCheck,
      action: () => handlePageNavigation('admin')
    }
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-between">
      {/* 1. Header do Portal com Navegação e Perfil */}
      <header className="sticky top-0 z-40 bg-[#6899BA] shadow-sm transition-colors duration-200">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 h-20 flex items-center justify-between">
          {/* Logo e Botão Voltar */}
          <div className="flex items-center space-x-4 sm:space-x-6">
            <button
              onClick={onBackToHome}
              className="flex items-center space-x-2 focus:outline-none hover:opacity-95 transition-opacity cursor-pointer"
              aria-label="Clube Maravilha Início"
            >
              <ClubeMaravilhaLogo variant="on-blue" size="md" />
            </button>

            <button
              onClick={onBackToHome}
              className="hidden lg:flex items-center space-x-1.5 px-3.5 py-1.5 rounded-full bg-white/15 hover:bg-white/25 border border-white/20 text-white text-xs font-semibold transition-all cursor-pointer shadow-xs"
            >
              <ArrowLeft className="w-3.5 h-3.5 text-white" />
              <span>Voltar ao Portal</span>
            </button>
          </div>

          {/* Ações da Direita: Perfil + Atalho Admin + Menu Hamburguer */}
          <div className="flex items-center space-x-3 sm:space-x-4">
            {onNavigatePage && (
              <button
                onClick={() => onNavigatePage('admin')}
                className="hidden sm:flex items-center space-x-1.5 px-3 py-1.5 rounded-full bg-[#1B3B54] hover:bg-[#152e42] border border-white/20 text-amber-300 hover:text-amber-200 text-xs font-semibold transition-all cursor-pointer shadow-xs"
                title="Acessar Painel Administrativo"
              >
                <ShieldCheck className="w-3.5 h-3.5 text-amber-400" />
                <span>Painel da Diretoria</span>
              </button>
            )}

            {/* Chip de Perfil do Sócio */}
            <div
              onClick={() => setCurrentTab('carteirinha')}
              className="flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-white/15 hover:bg-white/25 border border-white/20 text-white cursor-pointer transition-colors shadow-xs"
              title="Clique para ver sua Carteirinha Digital"
            >
              <div className="w-8 h-8 rounded-full bg-amber-400 text-slate-900 font-black flex items-center justify-center text-xs shadow-sm">
                SN
              </div>
              <div className="hidden sm:flex flex-col text-left">
                <span className="text-xs font-bold leading-tight tracking-wide text-white">
                  Schaide Nunes
                </span>
                <span className="text-[10px] text-emerald-300 font-semibold flex items-center space-x-1">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-400 animate-pulse"></span>
                  <span>Sócio Ativo</span>
                </span>
              </div>
              <ChevronDown className="w-3.5 h-3.5 text-white/80 hidden sm:block" />
            </div>

            {/* Botão Menu Hamburguer */}
            <button
              onClick={() => setMenuOpen(true)}
              className="p-2 rounded-xl text-white hover:text-amber-200 hover:bg-white/10 focus:outline-none cursor-pointer transition-colors"
              aria-label="Abrir Menu de Navegação"
            >
              <Menu className="w-6 h-6" />
            </button>
          </div>
        </div>
      </header>

      {/* Slide-over Drawer Backdrop */}
      <div
        className={`fixed inset-0 bg-black/60 backdrop-blur-xs z-50 transition-opacity duration-300 ease-out ${
          menuOpen ? 'opacity-100 pointer-events-auto' : 'opacity-0 pointer-events-none'
        }`}
        onClick={() => setMenuOpen(false)}
        aria-hidden={!menuOpen}
      >
        {/* Slide-over Panel */}
        <div
          className={`absolute top-0 right-0 w-[85%] max-w-[360px] h-full bg-[#132A3E] text-white p-6 sm:p-7 shadow-2xl flex flex-col justify-between transform transition-transform duration-300 ease-out ${
            menuOpen ? 'translate-x-0' : 'translate-x-full'
          }`}
          onClick={(e) => e.stopPropagation()}
        >
          <div>
            {/* Drawer Header */}
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
                    className={`w-full flex items-center justify-between px-4 py-3 rounded-xl text-left text-sm font-semibold transition-colors cursor-pointer ${
                      item.active
                        ? 'bg-white/20 text-white shadow-inner'
                        : 'text-white/90 hover:text-white hover:bg-white/10'
                    }`}
                  >
                    <div className="flex items-center space-x-3">
                      <Icon className="w-4 h-4 text-amber-300" />
                      <span>{item.label}</span>
                    </div>
                    <ChevronRight className="w-4 h-4 text-white/50" />
                  </button>
                );
              })}
            </nav>
          </div>

          {/* Drawer Footer com Status */}
          <div className="pt-6 border-t border-white/20">
            <div className="flex items-center space-x-3 bg-white/10 p-3.5 rounded-2xl">
              <div className="w-8 h-8 rounded-xl bg-amber-400 text-slate-900 font-bold flex items-center justify-center text-xs">
                SN
              </div>
              <div>
                <span className="text-xs font-bold block text-white">Schaide Nunes</span>
                <span className="text-[10px] text-emerald-300 font-medium">Sócio Ouro • Matrícula #0042</span>
              </div>
            </div>
          </div>
        </div>
      </div>

      {/* 2. Container Principal com Sidebar e Conteúdo Dinâmico */}
      <div className="max-w-[1520px] mx-auto w-full px-4 sm:px-8 xl:px-12 py-8 flex flex-col md:flex-row gap-8 flex-1">
        {/* Sidebar Esquerda */}
        <UserSidebar
          currentTab={currentTab}
          onSelectTab={(tab) => {
            setCurrentTab(tab);
          }}
          onOpenBenefits={() => setCurrentTab('beneficios')}
        />

        {/* Conteúdo Central Dinâmico baseado na aba selecionada */}
        <main className="flex-1 min-w-0">
          {currentTab === 'inicio' && (
            <UserOverviewTab
              onSelectTab={setCurrentTab}
              onOpenBookingModal={onOpenBookingModal}
            />
          )}

          {currentTab === 'carteirinha' && <UserCarteirinhaTab />}

          {currentTab === 'financeiro' && <UserFinanceiroTab />}

          {(currentTab === 'reservas' || currentTab === 'agenda' || currentTab === 'atividades') && (
            <UserReservasTab />
          )}

          {currentTab === 'familia' && <UserFamiliaTab />}

          {currentTab === 'eventos' && <UserEventosTab />}

          {currentTab === 'beneficios' && <UserBeneficiosTab />}

          {currentTab === 'conta' && <UserContaTab />}
        </main>
      </div>

      {/* 3. Rodapé Oficial */}
      <Footer onOpenPortal={() => onOpenPaymentModal()} />
    </div>
  );
};
