import React, { useState } from 'react';
import {
  Calendar,
  BookmarkCheck,
  Ticket,
  Users,
  CreditCard,
  ChevronDown,
  ArrowRight
} from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';
import { UserSidebar } from './UserSidebar';
import { Footer } from '../layout/Footer';

import showJoaoImg from '../../assets/show_joao_gomes.jpg';
import showCalypsoImg from '../../assets/show_calypso.jpg';
import showDorgivalImg from '../../assets/show_dorgival.jpg';

interface UserDashboardPageProps {
  onBackToHome: () => void;
  onOpenBookingModal: (courtName?: string) => void;
  onOpenPaymentModal: () => void;
}

export const UserDashboardPage: React.FC<UserDashboardPageProps> = ({
  onBackToHome,
  onOpenBookingModal,
  onOpenPaymentModal
}) => {
  const [currentTab, setCurrentTab] = useState('inicio');

  const highlightShows = [
    {
      id: 'show-joao',
      day: '12',
      month: 'SET',
      tag: 'SHOW',
      title: 'João Gomes',
      court: 'Quadra x',
      time: '15:00 - 17:00',
      image: showJoaoImg
    },
    {
      id: 'show-calypso',
      day: '18',
      month: 'SET',
      tag: 'SHOW',
      title: 'Calypso',
      court: 'Quadra x',
      time: '15:00 - 17:00',
      image: showCalypsoImg
    },
    {
      id: 'show-dorgival',
      day: '20',
      month: 'SET',
      tag: 'SHOW',
      title: 'Dorgival Dantas',
      court: 'Quadra x',
      time: '15:00 - 17:00',
      image: showDorgivalImg
    }
  ];

  return (
    <div className="min-h-screen bg-[#F8FAFC] flex flex-col justify-between">
      {/* 1. Header do Portal com Perfil Autenticado */}
      <header className="sticky top-0 z-40 bg-[#4E7A9C] shadow-md">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-20 flex items-center justify-between">
          <button
            onClick={onBackToHome}
            className="flex items-center space-x-2 focus:outline-none hover:opacity-95 transition-opacity"
            aria-label="Voltar para Início"
          >
            <ClubeMaravilhaLogo variant="light" size="md" />
          </button>

          {/* User Profile Dropdown Button */}
          <div className="flex items-center space-x-3">
            <div className="flex items-center space-x-2.5 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white cursor-pointer transition-colors">
              <div className="w-8 h-8 rounded-full bg-amber-400 text-slate-900 font-bold flex items-center justify-center text-xs shadow-sm">
                SN
              </div>
              <span className="text-sm font-semibold tracking-wide hidden sm:inline">
                Schaide Nunes
              </span>
              <ChevronDown className="w-4 h-4 text-white/80" />
            </div>
          </div>
        </div>
      </header>

      {/* 2. Container Principal com Sidebar e Conteúdo */}
      <div className="max-w-7xl mx-auto w-full px-4 sm:px-6 lg:px-8 py-8 flex flex-col md:flex-row gap-8 flex-1">
        {/* Sidebar Esquerda */}
        <UserSidebar
          currentTab={currentTab}
          onSelectTab={(tab) => {
            setCurrentTab(tab);
            if (tab === 'reservas') onOpenBookingModal();
            if (tab === 'financeiro') onOpenPaymentModal();
          }}
          onOpenBenefits={() => onOpenPaymentModal()}
        />

        {/* Conteúdo Central */}
        <main className="flex-1 min-w-0">
          {/* Saudação */}
          <div className="mb-8">
            <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight">
              Olá, Schaide
            </h1>
            <p className="text-slate-500 text-sm sm:text-base mt-1">
              Bem-vindo ao seu espaço Maravilha!!
            </p>
          </div>

          {/* 3 Cards de Ação Rápida */}
          <div className="grid grid-cols-1 sm:grid-cols-3 gap-5 mb-8">
            {/* Card 1: Minha Agenda */}
            <div
              onClick={() => onOpenBookingModal('Minha Agenda')}
              className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center mb-4 shadow-sm">
                  <Calendar className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-[#1B3B54] text-base mb-1">
                  Minha Agenda
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Confira todas as suas programações.
                </p>
              </div>
              <div className="mt-4 flex justify-end">
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#1B3B54] group-hover:translate-x-1 transition-all" />
              </div>
            </div>

            {/* Card 2: Reservas */}
            <div
              onClick={() => onOpenBookingModal()}
              className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center mb-4 shadow-sm">
                  <BookmarkCheck className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-[#1B3B54] text-base mb-1">
                  Reservas
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Confira todas as suas reservas.
                </p>
              </div>
              <div className="mt-4 flex justify-end">
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#1B3B54] group-hover:translate-x-1 transition-all" />
              </div>
            </div>

            {/* Card 3: Eventos */}
            <div
              onClick={() => onOpenBookingModal('Eventos')}
              className="bg-white p-5 rounded-2xl border border-slate-200/80 shadow-sm hover:shadow-md transition-all cursor-pointer group flex flex-col justify-between"
            >
              <div>
                <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center mb-4 shadow-sm">
                  <Ticket className="w-5 h-5" />
                </div>
                <h3 className="font-bold text-[#1B3B54] text-base mb-1">
                  Eventos
                </h3>
                <p className="text-xs text-slate-500 leading-relaxed">
                  Confira todos os eventos do clube.
                </p>
              </div>
              <div className="mt-4 flex justify-end">
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#1B3B54] group-hover:translate-x-1 transition-all" />
              </div>
            </div>
          </div>

          {/* 2 Cards de Status Operacional */}
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 mb-10">
            {/* Card Esquerdo: Próximas Atividades */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm">
              <div className="flex items-center space-x-3 mb-5">
                <div className="w-9 h-9 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
                  <Users className="w-5 h-5" />
                </div>
                <h2 className="font-bold text-[#1B3B54] text-base">
                  Próximas atividades
                </h2>
              </div>

              <div className="space-y-3">
                {['Vôlei - 20 Set', 'Vôlei - 22 Set', 'Vôlei - 26 Set'].map((item, idx) => (
                  <button
                    key={idx}
                    onClick={() => onOpenBookingModal(item)}
                    className="w-full flex items-center justify-between px-4 py-3 rounded-full border border-slate-200/90 hover:border-[#1B3B54] hover:bg-slate-50 text-sm font-medium text-[#1B3B54] transition-all group"
                  >
                    <span>{item}</span>
                    <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-[#1B3B54] group-hover:translate-x-0.5 transition-transform" />
                  </button>
                ))}
              </div>
            </div>

            {/* Card Direito: Minha Situação */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/80 shadow-sm flex flex-col justify-between">
              <div>
                <div className="flex items-center space-x-3 mb-3">
                  <div className="w-9 h-9 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
                    <CreditCard className="w-5 h-5" />
                  </div>
                  <h2 className="font-bold text-[#1B3B54] text-base">
                    Minha Situação
                  </h2>
                </div>

                <p className="text-xs text-slate-500 leading-relaxed mb-6">
                  Acompanhe seu plano, benefícios e situação cadastral.
                </p>
              </div>

              {/* Botão de Vencimento / Fatura */}
              <button
                onClick={onOpenPaymentModal}
                className="w-full flex items-center justify-between px-4 py-3 rounded-full border border-slate-200/90 hover:border-emerald-600 hover:bg-emerald-50/40 text-sm font-medium text-[#1B3B54] transition-all group"
              >
                <div className="flex items-center space-x-2">
                  <span className="w-2 h-2 rounded-full bg-emerald-500 animate-pulse"></span>
                  <span>Vencimento - 12 Dez</span>
                </div>
                <ArrowRight className="w-4 h-4 text-slate-400 group-hover:text-emerald-700 group-hover:translate-x-0.5 transition-transform" />
              </button>
            </div>
          </div>

          {/* Seção: EVENTOS EM DESTAQUE */}
          <div>
            <div className="flex items-center space-x-2.5 mb-6">
              <Calendar className="w-5 h-5 text-[#1B3B54]" />
              <h2 className="text-lg sm:text-xl font-black tracking-wider text-[#1B3B54] uppercase font-sans">
                EVENTOS EM DESTAQUE
              </h2>
            </div>

            {/* 3 Show Cards */}
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-6">
              {highlightShows.map((show) => (
                <div
                  key={show.id}
                  className="bg-white rounded-2xl overflow-hidden border border-slate-200/80 shadow-sm hover:shadow-md transition-all duration-300 flex flex-col justify-between"
                >
                  <div className="relative h-44 w-full overflow-hidden bg-slate-100">
                    <img
                      src={show.image}
                      alt={show.title}
                      className="w-full h-full object-cover group-hover:scale-105 transition-transform duration-500"
                    />
                    <div className="absolute top-3 left-3 bg-[#1F3347]/95 backdrop-blur-sm text-white px-2.5 py-1.5 rounded-lg flex flex-col items-center shadow-md">
                      <span className="text-base font-bold leading-none text-amber-400">
                        {show.day}
                      </span>
                      <span className="text-[10px] font-semibold tracking-wider text-slate-200">
                        {show.month}
                      </span>
                    </div>
                  </div>

                  <div className="p-4">
                    <span className="inline-block text-[10px] font-bold tracking-widest text-slate-400 uppercase mb-1">
                      {show.tag}
                    </span>
                    <h3 className="font-bold text-[#1F3347] text-base mb-2">
                      {show.title}
                    </h3>
                    <div className="space-y-1 mb-4 text-xs text-slate-500">
                      <p>{show.court}</p>
                      <p>{show.time}</p>
                    </div>

                    <button
                      onClick={() => onOpenBookingModal(`Ingresso Show: ${show.title}`)}
                      className="w-full py-2.5 rounded-lg bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-semibold tracking-wide flex items-center justify-center space-x-2 transition-colors shadow-xs"
                    >
                      <Ticket className="w-3.5 h-3.5 text-amber-400" />
                      <span>Saiba mais</span>
                      <ArrowRight className="w-3.5 h-3.5" />
                    </button>
                  </div>
                </div>
              ))}
            </div>
          </div>
        </main>
      </div>

      {/* 3. Rodapé Oficial */}
      <Footer onOpenPortal={() => onOpenPaymentModal()} />
    </div>
  );
};
