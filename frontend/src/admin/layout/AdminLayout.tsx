import React from 'react';
import { NavLink, Outlet, useNavigate } from 'react-router-dom';
import { LayoutDashboard, Users, Layers, CreditCard, MessageSquare, LogOut } from 'lucide-react';
import { useQuery } from '@tanstack/react-query';
import { useAuth } from '../auth/AuthProvider';
import { apiClient } from '../api/client';
import { labelWhatsAppStatus } from '../utils/format';

const NAV_ITEMS = [
  { name: 'Dashboard', to: '/admin', end: true, icon: LayoutDashboard },
  { name: 'Associados', to: '/admin/associados', end: false, icon: Users },
  { name: 'Planos', to: '/admin/planos', end: false, icon: Layers },
  { name: 'Mensalidades', to: '/admin/mensalidades', end: false, icon: CreditCard },
  { name: 'WhatsApp & Configurações', to: '/admin/whatsapp', end: false, icon: MessageSquare },
];

export function AdminLayout(): React.ReactElement {
  const { usuario, logout } = useAuth();
  const navigate = useNavigate();

  const { data: whatsappData, isError } = useQuery({
    queryKey: ['whatsapp-status'],
    queryFn: async () => {
      const res = await apiClient.get<{ status: string }>('/whatsapp/status');
      return res.data;
    },
    refetchInterval: 15000,
  });

  const rawStatus = isError ? 'DESCONECTADO' : whatsappData?.status || 'DESCONECTADO';
  const statusFormatado = labelWhatsAppStatus(rawStatus);

  const handleSair = () => {
    logout();
    navigate('/admin/login', { replace: true });
  };

  return (
    <div className="min-h-screen flex bg-slate-50 text-slate-900 font-sans">
      {/* Sidebar Desktop */}
      <aside className="w-64 bg-white border-r border-slate-200 flex flex-col justify-between shrink-0">
        <div>
          {/* Header Sidebar */}
          <div className="h-16 flex items-center px-6 border-b border-slate-200">
            <span className="text-lg font-bold tracking-tight text-slate-900">
              Club Maravilha
            </span>
          </div>

          {/* Navegação Principal */}
          <nav aria-label="Menu principal" className="p-4 space-y-1">
            {NAV_ITEMS.map((item) => {
              const Icon = item.icon;
              return (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition duration-150 ease-out ${
                      isActive
                        ? 'bg-slate-100 text-slate-900 font-semibold'
                        : 'text-slate-600 hover:bg-slate-50 hover:text-slate-900'
                    }`
                  }
                >
                  <Icon className="w-5 h-5 shrink-0" />
                  <span>{item.name}</span>
                </NavLink>
              );
            })}
          </nav>
        </div>

        {/* Footer Sidebar: WhatsApp Indicator + User + Logout */}
        <div className="p-4 border-t border-slate-200 space-y-4">
          {/* WhatsApp Status Indicator */}
          <div
            data-testid="whatsapp-indicator"
            className="flex items-center gap-2 px-3 py-2 bg-slate-50 border border-slate-200 rounded-lg text-xs"
          >
            <span
              className={`w-2 h-2 rounded-full shrink-0 ${
                statusFormatado === 'Conectado'
                  ? 'bg-emerald-500'
                  : statusFormatado === 'Aguardando QR Code'
                  ? 'bg-amber-500'
                  : 'bg-rose-500'
              }`}
            />
            <span className="text-slate-600">WhatsApp:</span>
            <span className="font-medium text-slate-900">{statusFormatado}</span>
          </div>

          {/* User info & Logout */}
          <div className="flex items-center justify-between pt-2">
            <div className="min-w-0 pr-2">
              <p className="text-sm font-medium text-slate-900 truncate">
                {usuario?.nome || 'Administrador'}
              </p>
              <p className="text-xs text-slate-500 truncate">
                {usuario?.email || ''}
              </p>
            </div>
            <button
              onClick={handleSair}
              type="button"
              className="p-1.5 text-slate-500 hover:text-slate-900 hover:bg-slate-100 rounded-lg transition duration-150 ease-out"
              title="Sair do painel"
              aria-label="Sair"
            >
              <LogOut className="w-5 h-5" />
            </button>
          </div>
        </div>
      </aside>

      {/* Conteúdo Principal */}
      <main className="flex-1 flex flex-col min-w-0 overflow-y-auto">
        <Outlet />
      </main>
    </div>
  );
}

export default AdminLayout;
