import React from 'react';
import {
  Home,
  Calendar,
  Activity,
  BookmarkCheck,
  Ticket,
  CreditCard,
  Users,
  Gift,
  Contact,
  Settings,
  ArrowRight
} from 'lucide-react';

interface UserSidebarProps {
  currentTab: string;
  onSelectTab: (tabId: string) => void;
  onOpenBenefits?: () => void;
}

export const UserSidebar: React.FC<UserSidebarProps> = ({
  currentTab,
  onSelectTab,
  onOpenBenefits
}) => {
  const menuItems = [
    { id: 'inicio', label: 'Início', icon: Home },
    { id: 'agenda', label: 'Minha Agenda', icon: Calendar },
    { id: 'atividades', label: 'Atividades', icon: Activity },
    { id: 'reservas', label: 'Reservas', icon: BookmarkCheck },
    { id: 'eventos', label: 'Eventos', icon: Ticket },
    { id: 'financeiro', label: 'Financeiro', icon: CreditCard },
    { id: 'familia', label: 'Família', icon: Users },
    { id: 'beneficios', label: 'Benefícios', icon: Gift },
    { id: 'carteirinha', label: 'Carteirinha', icon: Contact },
    { id: 'conta', label: 'Minha conta', icon: Settings },
  ];

  return (
    <aside className="w-full md:w-64 bg-white border-r border-slate-200/80 p-4 sm:p-5 flex flex-col justify-between shrink-0">
      <div>
        {/* Navigation List */}
        <nav className="space-y-1">
          {menuItems.map((item) => {
            const Icon = item.icon;
            const isActive = currentTab === item.id;

            return (
              <button
                key={item.id}
                onClick={() => onSelectTab(item.id)}
                className={`w-full flex items-center space-x-3.5 px-3.5 py-2.5 rounded-xl text-sm font-medium transition-all duration-200 ${
                  isActive
                    ? 'bg-[#D9EDFD] text-[#1B3B54] font-bold shadow-xs'
                    : 'text-slate-600 hover:text-[#1B3B54] hover:bg-slate-50'
                }`}
              >
                <Icon className={`w-4 h-4 ${isActive ? 'text-[#1B3B54]' : 'text-slate-500'}`} />
                <span>{item.label}</span>
              </button>
            );
          })}
        </nav>
      </div>

      {/* Promotional Benefit Box at bottom */}
      <div className="mt-8 pt-4 border-t border-slate-100">
        <div className="bg-[#92C6FA] text-[#1B3B54] rounded-2xl p-4 shadow-sm relative overflow-hidden">
          <div className="w-9 h-9 rounded-xl bg-white/70 flex items-center justify-center mb-3">
            <Ticket className="w-5 h-5 text-[#1B3B54]" />
          </div>
          <p className="font-bold text-sm leading-snug mb-3">
            Aproveite os benefícios do seu clube!
          </p>
          <button
            onClick={onOpenBenefits}
            className="inline-flex items-center space-x-1.5 text-xs font-bold text-[#1B3B54] hover:text-slate-900 transition-colors"
          >
            <span>Ver mais</span>
            <ArrowRight className="w-3.5 h-3.5" />
          </button>
        </div>
      </div>
    </aside>
  );
};
