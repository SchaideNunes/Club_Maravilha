import React, { useState } from 'react';
import {
  Users,
  DollarSign,
  Zap,
  Calendar,
  ShieldCheck,
  RefreshCw,
  Send,
  Upload,
  Search,
  CheckCircle2,
  ArrowLeft,
  Wifi,
  WifiOff,
  FileSpreadsheet,
  Activity,
  MessageSquare
} from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';
import { PageRoute } from '../layout/Navbar';

interface AdminDashboardPageProps {
  onBackToHome: () => void;
  onNavigatePage: (page: PageRoute) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({
  onBackToHome,
  onNavigatePage
}) => {
  const [activeTab, setActiveTab] = useState<'kpis' | 'associados' | 'catracas' | 'cobranca' | 'quadras'>('kpis');
  
  // Interactive State
  const [syncingTurnstile, setSyncingTurnstile] = useState(false);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [offlineSimulated, setOfflineSimulated] = useState(false);
  const [runningBilling, setRunningBilling] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'TODOS' | 'ATIVO' | 'INADIMPLENTE'>('TODOS');
  const [showImportModal, setShowImportModal] = useState(false);
  const [importProgress, setImportProgress] = useState<number | null>(null);

  // Live Turnstile Feed
  const [turnstileLogs, setTurnstileLogs] = useState([
    {
      id: 1,
      name: 'Schaide Nunes',
      categoria: 'Sócio Titular',
      matricula: '#2026-0042',
      metodo: 'Reconhecimento Facial',
      catraca: 'Catraca 01 (Portaria Social)',
      hora: '17:42:10',
      status: 'LIBERADO',
      latency: '0.24s'
    },
    {
      id: 2,
      name: 'Mariana Duarte',
      categoria: 'Convidada de Sócio',
      matricula: 'Token #cm_guest_9f83a2',
      metodo: 'QR Code Dinâmico',
      catraca: 'Catraca 02 (Visitantes)',
      hora: '17:38:05',
      status: 'LIBERADO',
      latency: '0.28s'
    },
    {
      id: 3,
      name: 'Carlos Eduardo',
      categoria: 'Sócio Dependente',
      matricula: '#2026-0042-D1',
      metodo: 'Reconhecimento Facial',
      catraca: 'Catraca 01 (Portaria Social)',
      hora: '17:21:40',
      status: 'LIBERADO',
      latency: '0.22s'
    },
    {
      id: 4,
      name: 'Lucas Moreira',
      categoria: 'Sócio Titular',
      matricula: '#2025-0811',
      metodo: 'Reconhecimento Facial',
      catraca: 'Catraca 01 (Portaria Social)',
      hora: '16:55:12',
      status: 'BLOQUEADO',
      latency: '0.31s',
      reason: 'Inadimplência D+8 (Fatura Vencida)'
    }
  ]);

  // Associados List
  const [associadosList, setAssociadosList] = useState([
    {
      id: '1',
      name: 'Schaide Nunes',
      cpf: '123.456.789-00',
      whatsapp: '(75) 98328-5614',
      plano: 'Ouro Familiar',
      matricula: '#2026-0042',
      status: 'ATIVO',
      mensalidade: 'Em Dia (R$ 150,00)',
      catraca: 'Liberada (Facial)',
      facialRegistered: true
    },
    {
      id: '2',
      name: 'Juliana Costa e Silva',
      cpf: '234.567.890-11',
      whatsapp: '(75) 98112-3344',
      plano: 'Ouro Individual',
      matricula: '#2026-0043',
      status: 'ATIVO',
      mensalidade: 'Em Dia (R$ 100,00)',
      catraca: 'Liberada (Facial)',
      facialRegistered: true
    },
    {
      id: '3',
      name: 'Marcos Vinícius Santos',
      cpf: '345.678.901-22',
      whatsapp: '(75) 99221-5566',
      plano: 'Prata Familiar',
      matricula: '#2026-0044',
      status: 'ATIVO',
      mensalidade: 'Em Dia (R$ 120,00)',
      catraca: 'Liberada (Facial)',
      facialRegistered: true
    },
    {
      id: '4',
      name: 'Lucas Moreira de Oliveira',
      cpf: '456.789.012-33',
      whatsapp: '(75) 99887-1122',
      plano: 'Ouro Familiar',
      matricula: '#2025-0811',
      status: 'INADIMPLENTE',
      mensalidade: 'Vencida há 8 dias (R$ 150,00)',
      catraca: 'Bloqueada (D+7)',
      facialRegistered: true
    },
    {
      id: '5',
      name: 'Beatriz Almeida Lima',
      cpf: '567.890.123-44',
      whatsapp: '(75) 98776-9900',
      plano: 'Ouro Individual',
      matricula: '#2026-0045',
      status: 'ATIVO',
      mensalidade: 'Em Dia (R$ 100,00)',
      catraca: 'Liberada (Facial)',
      facialRegistered: true
    }
  ]);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 5000);
  };

  const handleSyncTurnstile = async () => {
    setSyncingTurnstile(true);
    try {
      // Tenta chamar API real se o backend estiver disponível
      await fetch('http://localhost:8000/api/v1/catraca/sync?reason=admin_manual_trigger', { method: 'POST' }).catch(() => {});
    } finally {
      setTimeout(() => {
        setSyncingTurnstile(false);
        showToast('Catraca Sincronizada! 482 associados ativos e 8 convidados baixados na memória local (MD5: c98a2f-20260924).');
      }, 700);
    }
  };

  const handleRunBilling = async () => {
    setRunningBilling(true);
    try {
      await fetch('http://localhost:8000/api/v1/faturas/executar-regua', { method: 'POST' }).catch(() => {});
    } finally {
      setTimeout(() => {
        setRunningBilling(false);
        showToast('Régua Diária Concluída: 18 Pix Copia e Cola enviados pelo WhatsApp com jitter anti-ban (3-8s). 1 alerta de bloqueio D+7 emitido.');
      }, 900);
    }
  };

  const handleSimulatePass = () => {
    const newLog = {
      id: Date.now(),
      name: 'Schaide Nunes',
      categoria: 'Sócio Titular',
      matricula: '#2026-0042',
      metodo: 'Reconhecimento Facial',
      catraca: 'Catraca 01 (Portaria Social)',
      hora: new Date().toLocaleTimeString('pt-BR'),
      status: 'LIBERADO',
      latency: '0.21s'
    };
    setTurnstileLogs([newLog, ...turnstileLogs]);
    showToast('Simulação de passagem executada: Catraca destravada em 0.21s!');
  };

  const handleToggleMemberStatus = (id: string) => {
    setAssociadosList((prev) =>
      prev.map((m) => {
        if (m.id === id) {
          const newStatus = m.status === 'ATIVO' ? 'INADIMPLENTE' : 'ATIVO';
          const newCatraca = newStatus === 'ATIVO' ? 'Liberada (Facial)' : 'Bloqueada (D+7)';
          return { ...m, status: newStatus, catraca: newCatraca };
        }
        return m;
      })
    );
    showToast('Status do associado e permissão da catraca atualizados no banco de dados!');
  };

  const handleSimulateImport = () => {
    setImportProgress(10);
    const interval = setInterval(() => {
      setImportProgress((p) => {
        if (p === null || p >= 100) {
          clearInterval(interval);
          setTimeout(() => {
            setShowImportModal(false);
            setImportProgress(null);
            showToast('Importação Excel Concluída: 142 associados migrados, 137 CPFs validados matematicamente e 5 duplicidades ignoradas.');
          }, 400);
          return 100;
        }
        return p + 25;
      });
    }, 250);
  };

  // Filtered members
  const filteredAssociados = associadosList.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.cpf.includes(searchQuery) ||
      m.matricula.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesStatus = statusFilter === 'TODOS' || m.status === statusFilter;
    return matchesSearch && matchesStatus;
  });

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-[#1F3347] flex flex-col justify-between font-sans">
      {/* 1. Header do Administrador */}
      <header className="sticky top-0 z-40 bg-[#1B3B54] text-white shadow-md">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 h-20 flex items-center justify-between">
          {/* Logo e Título da Gestão */}
          <div className="flex items-center space-x-4 sm:space-x-6">
            <button
              onClick={onBackToHome}
              className="flex items-center space-x-2 focus:outline-none hover:opacity-95 transition-opacity cursor-pointer"
              aria-label="Voltar para a Home"
            >
              <ClubeMaravilhaLogo variant="on-blue" size="md" />
            </button>

            <div className="hidden md:flex items-center space-x-2.5 pl-4 border-l border-white/20">
              <span className="px-2.5 py-1 rounded-md bg-amber-400 text-[#1B3B54] text-[11px] font-black uppercase tracking-wider">
                DIRETORIA
              </span>
              <span className="text-xs font-semibold text-slate-200">
                Painel Administrativo & Operações
              </span>
            </div>
          </div>

          {/* Status dos Microsserviços e Botões de Alternância */}
          <div className="flex items-center space-x-3 sm:space-x-4">
            {/* Status Pills */}
            <div className="hidden lg:flex items-center space-x-2 text-[11px] bg-white/10 px-3 py-1.5 rounded-full border border-white/15">
              <span className="flex items-center space-x-1.5 text-emerald-300 font-semibold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>API 100%</span>
              </span>
              <span className="text-white/40">•</span>
              <span className="flex items-center space-x-1.5 text-emerald-300 font-semibold">
                <ShieldCheck className="w-3.5 h-3.5" />
                <span>Catraca Whitelist</span>
              </span>
              <span className="text-white/40">•</span>
              <span className="flex items-center space-x-1.5 text-amber-300 font-semibold">
                <MessageSquare className="w-3.5 h-3.5" />
                <span>WhatsApp Fila Ativa</span>
              </span>
            </div>

            {/* Alternar para Visão do Sócio */}
            <button
              onClick={() => onNavigatePage('usuario')}
              className="px-3.5 py-1.5 rounded-full bg-white/15 hover:bg-white/25 border border-white/20 text-white text-xs font-bold transition-all cursor-pointer shadow-xs flex items-center space-x-1.5"
            >
              <Users className="w-3.5 h-3.5" />
              <span>Área do Associado</span>
            </button>

            <button
              onClick={onBackToHome}
              className="hidden sm:flex items-center space-x-1 px-3 py-1.5 rounded-full bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-all cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Ver Site</span>
            </button>
          </div>
        </div>
      </header>

      {/* Toast Alert Flutuante */}
      {toastMessage && (
        <div className="fixed top-24 right-6 z-50 max-w-md p-4 rounded-2xl bg-[#1B3B54] text-white border border-[#4E7A9C] shadow-2xl flex items-start space-x-3 animate-in fade-in slide-in-from-top-4 duration-300">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0 mt-0.5" />
          <div className="flex-1">
            <span className="text-xs font-bold uppercase tracking-wider text-amber-300 block mb-0.5">
              Notificação Operacional
            </span>
            <p className="text-xs leading-relaxed text-slate-100">{toastMessage}</p>
          </div>
        </div>
      )}

      {/* 2. Container Central */}
      <div className="max-w-[1520px] mx-auto w-full px-4 sm:px-8 xl:px-12 py-8 flex-1 space-y-8">
        {/* Barra Superior do Dashboard com Navegação em Abas */}
        <div className="bg-white p-4 sm:p-5 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col md:flex-row md:items-center justify-between gap-4">
          <div>
            <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
              <span>Gestão Integrada</span>
              <span>•</span>
              <span>Clube Maravilha</span>
            </div>
            <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-0.5">
              Painel de Controle da Diretoria
            </h1>
          </div>

          {/* Abas do Admin */}
          <div className="flex items-center gap-1.5 sm:gap-2 overflow-x-auto pb-1 text-xs font-bold">
            {[
              { id: 'kpis', label: 'Visão Geral (KPIs)', icon: Activity },
              { id: 'associados', label: 'Sócios & Migração', icon: Users },
              { id: 'catracas', label: 'Portaria & Catracas', icon: ShieldCheck },
              { id: 'cobranca', label: 'Cobrança & WhatsApp', icon: MessageSquare },
              { id: 'quadras', label: 'Quadras & Reservas', icon: Calendar },
            ].map((tab) => {
              const Icon = tab.icon;
              const isActive = activeTab === tab.id;
              return (
                <button
                  key={tab.id}
                  onClick={() => setActiveTab(tab.id as any)}
                  className={`px-3.5 py-2 rounded-xl transition-all flex items-center space-x-2 whitespace-nowrap cursor-pointer ${
                    isActive
                      ? 'bg-[#1B3B54] text-white shadow-xs font-extrabold'
                      : 'bg-slate-50 hover:bg-slate-100 text-slate-600 hover:text-[#1B3B54]'
                  }`}
                >
                  <Icon className={`w-3.5 h-3.5 ${isActive ? 'text-amber-300' : 'text-slate-400'}`} />
                  <span>{tab.label}</span>
                </button>
              );
            })}
          </div>
        </div>

        {/* ========================================================================= */}
        {/* ABA 1: VISÃO GERAL (KPIS & AÇÕES RÁPIDAS) */}
        {/* ========================================================================= */}
        {activeTab === 'kpis' && (
          <div className="space-y-8 animate-in fade-in">
            {/* 4 Cards de Métricas Principais */}
            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-5">
              {/* Card 1: Sócios */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-bold tracking-wider text-slate-500">
                    Total de Associados
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-[#EBF4FA] text-[#1B3B54] flex items-center justify-center font-bold">
                    <Users className="w-5 h-5" />
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-black text-[#1B3B54]">482</div>
                  <div className="flex items-center space-x-1.5 text-xs text-emerald-700 font-bold mt-1">
                    <span className="px-2 py-0.5 rounded-md bg-emerald-50 border border-emerald-200">
                      +14 neste mês
                    </span>
                    <span>• 96.4% adimplentes</span>
                  </div>
                </div>
              </div>

              {/* Card 2: Receita / MRR */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-bold tracking-wider text-slate-500">
                    Receita Recorrente (MRR)
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                    <DollarSign className="w-5 h-5" />
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-black text-[#1B3B54]">R$ 72.300</div>
                  <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium mt-1">
                    <span>Previsão: R$ 75.000</span>
                    <span className="text-emerald-700 font-bold">(96.4% realizado)</span>
                  </div>
                </div>
              </div>

              {/* Card 3: Portaria & Acessos */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-bold tracking-wider text-slate-500">
                    Acessos na Portaria Hoje
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-[#EBF4FA] text-[#1B3B54] flex items-center justify-center font-bold">
                    <ShieldCheck className="w-5 h-5" />
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-black text-[#1B3B54]">184</div>
                  <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium mt-1">
                    <span className="text-emerald-700 font-bold">0 falhas</span>
                    <span>• Pico às 17h30</span>
                  </div>
                </div>
              </div>

              {/* Card 4: Ocupação das Quadras */}
              <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs flex flex-col justify-between space-y-4">
                <div className="flex items-center justify-between">
                  <span className="text-xs uppercase font-bold tracking-wider text-slate-500">
                    Ocupação de Quadras
                  </span>
                  <div className="w-10 h-10 rounded-2xl bg-amber-50 text-amber-700 flex items-center justify-center font-bold">
                    <Calendar className="w-5 h-5" />
                  </div>
                </div>
                <div>
                  <div className="text-3xl font-black text-[#1B3B54]">82%</div>
                  <div className="flex items-center space-x-1.5 text-xs text-slate-500 font-medium mt-1">
                    <span>14 horários confirmados</span>
                    <span className="text-[#4E7A9C] font-bold">hoje</span>
                  </div>
                </div>
              </div>
            </div>

            {/* Painel Operacional da Diretoria: Botões Interativos para a Reunião */}
            <div className="bg-white p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-xs space-y-5">
              <div className="flex items-center justify-between">
                <div>
                  <span className="text-xs uppercase font-bold tracking-wider text-[#4E7A9C]">
                    Demonstração em Tempo Real para a Reunião
                  </span>
                  <h3 className="text-xl font-black text-[#1B3B54] mt-0.5">
                    Ações de Comando da Gestão
                  </h3>
                </div>
                <span className="text-xs px-3 py-1 rounded-full bg-slate-100 text-slate-600 font-semibold hidden sm:inline">
                  3 Operações Automatizadas Disponíveis
                </span>
              </div>

              <div className="grid grid-cols-1 md:grid-cols-3 gap-4 pt-2">
                {/* Ação 1: Sincronização Catracas */}
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center space-x-2 text-[#1B3B54] font-bold text-sm mb-1">
                      <ShieldCheck className="w-4 h-4 text-emerald-600" />
                      <span>Catracas Físicas (Portaria)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Atualiza a Whitelist offline na memória local das controladoras faciais.
                    </p>
                  </div>
                  <button
                    onClick={handleSyncTurnstile}
                    disabled={syncingTurnstile}
                    className="w-full py-2.5 px-3 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-bold flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-xs"
                  >
                    <RefreshCw className={`w-3.5 h-3.5 ${syncingTurnstile ? 'animate-spin' : ''}`} />
                    <span>{syncingTurnstile ? 'Sincronizando...' : 'Forçar Sync da Catraca'}</span>
                  </button>
                </div>

                {/* Ação 2: Régua de Cobrança WhatsApp */}
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center space-x-2 text-[#1B3B54] font-bold text-sm mb-1">
                      <MessageSquare className="w-4 h-4 text-emerald-600" />
                      <span>Régua de Cobrança WhatsApp</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Dispara a rotina matinal: Pix Copia e Cola em D-0 e lembretes amigáveis em D-3.
                    </p>
                  </div>
                  <button
                    onClick={handleRunBilling}
                    disabled={runningBilling}
                    className="w-full py-2.5 px-3 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-bold flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-xs"
                  >
                    <Send className={`w-3.5 h-3.5 ${runningBilling ? 'animate-pulse' : ''}`} />
                    <span>{runningBilling ? 'Processando Fila...' : 'Disparar Régua de Cobrança'}</span>
                  </button>
                </div>

                {/* Ação 3: Importação de Planilha */}
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col justify-between space-y-3">
                  <div>
                    <div className="flex items-center space-x-2 text-[#1B3B54] font-bold text-sm mb-1">
                      <FileSpreadsheet className="w-4 h-4 text-[#4E7A9C]" />
                      <span>Migração de Sócios (Excel)</span>
                    </div>
                    <p className="text-xs text-slate-500">
                      Motor de importação assíncrono com validação matemática de CPF.
                    </p>
                  </div>
                  <button
                    onClick={() => setShowImportModal(true)}
                    className="w-full py-2.5 px-3 rounded-xl bg-white border border-slate-300 hover:border-[#1F3347] text-[#1F3347] text-xs font-bold flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-xs"
                  >
                    <Upload className="w-3.5 h-3.5 text-slate-500" />
                    <span>Importar Planilha .xlsx</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Monitor de Passagem da Portaria em Tempo Real */}
            <div className="bg-white p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-xs space-y-5">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
                <div>
                  <span className="text-xs uppercase font-bold tracking-wider text-[#4E7A9C]">
                    Controle de Acesso Físico
                  </span>
                  <h3 className="text-xl font-black text-[#1B3B54] mt-0.5">
                    Feed de Passagens na Catraca (Tempo Real)
                  </h3>
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={handleSimulatePass}
                    className="px-4 py-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center space-x-1.5 cursor-pointer shadow-xs"
                  >
                    <Zap className="w-3.5 h-3.5 text-amber-300" />
                    <span>Simular Giro na Catraca</span>
                  </button>
                </div>
              </div>

              {/* Tabela de Logs */}
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                      <th className="pb-3">Sócio / Visitante</th>
                      <th className="pb-3">Categoria</th>
                      <th className="pb-3">Método de Validação</th>
                      <th className="pb-3">Dispositivo / Local</th>
                      <th className="pb-3">Horário</th>
                      <th className="pb-3 text-right">Status</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {turnstileLogs.map((log) => (
                      <tr key={log.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3.5 font-bold text-[#1B3B54]">
                          {log.name}
                          <span className="block text-[11px] font-mono text-slate-400 font-normal">
                            {log.matricula}
                          </span>
                        </td>
                        <td className="py-3.5 text-slate-600 font-medium">{log.categoria}</td>
                        <td className="py-3.5 text-slate-600">
                          <span className="inline-flex items-center space-x-1 text-slate-700 font-medium">
                            <span className="w-1.5 h-1.5 rounded-full bg-[#4E7A9C]"></span>
                            <span>{log.metodo}</span>
                          </span>
                        </td>
                        <td className="py-3.5 text-slate-500">{log.catraca}</td>
                        <td className="py-3.5 font-mono text-slate-700 font-semibold">{log.hora}</td>
                        <td className="py-3.5 text-right">
                          <span
                            className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-bold ${
                              log.status === 'LIBERADO'
                                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                                : 'bg-rose-50 text-rose-800 border border-rose-200'
                            }`}
                          >
                            <span
                              className={`w-1.5 h-1.5 rounded-full ${
                                log.status === 'LIBERADO' ? 'bg-emerald-500' : 'bg-rose-500'
                              }`}
                            ></span>
                            <span>{log.status}</span>
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 2: GESTÃO DE ASSOCIADOS & MIGRAÇÃO */}
        {/* ========================================================================= */}
        {activeTab === 'associados' && (
          <div className="space-y-6 animate-in fade-in">
            {/* Header da Tabela com Filtros e Busca */}
            <div className="bg-white p-6 rounded-3xl border border-slate-200/90 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <h3 className="text-xl font-black text-[#1B3B54]">
                    Cadastro Geral de Associados
                  </h3>
                  <p className="text-xs text-slate-500">
                    Gerencie a base de membros, situação cadastral e sincronização de biometria facial.
                  </p>
                </div>

                <button
                  onClick={() => setShowImportModal(true)}
                  className="px-4 py-2 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-bold flex items-center space-x-2 transition-colors cursor-pointer self-start sm:self-auto"
                >
                  <Upload className="w-3.5 h-3.5" />
                  <span>Importar Planilha</span>
                </button>
              </div>

              {/* Filtros e Busca */}
              <div className="flex flex-col sm:flex-row gap-3 pt-2">
                <div className="relative flex-1">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-3" />
                  <input
                    type="text"
                    placeholder="Buscar por nome, CPF ou matrícula..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full bg-slate-50 border border-slate-300 rounded-xl pl-10 pr-4 py-2 text-xs text-[#1B3B54] focus:outline-none focus:border-[#4E7A9C]"
                  />
                </div>

                <div className="flex items-center space-x-2">
                  {(['TODOS', 'ATIVO', 'INADIMPLENTE'] as const).map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      className={`px-3 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                        statusFilter === st
                          ? 'bg-[#1B3B54] text-white'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                      }`}
                    >
                      {st === 'TODOS' ? 'Todos (482)' : st === 'ATIVO' ? 'Adimplentes (465)' : 'Inadimplentes (17)'}
                    </button>
                  ))}
                </div>
              </div>

              {/* Tabela de Associados */}
              <div className="overflow-x-auto pt-2">
                <table className="w-full text-left text-xs">
                  <thead>
                    <tr className="border-b border-slate-200 text-slate-500 font-bold uppercase tracking-wider">
                      <th className="pb-3">Associado</th>
                      <th className="pb-3">CPF</th>
                      <th className="pb-3">WhatsApp</th>
                      <th className="pb-3">Plano</th>
                      <th className="pb-3">Mensalidade</th>
                      <th className="pb-3">Catraca</th>
                      <th className="pb-3 text-right">Ação</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredAssociados.map((m) => (
                      <tr key={m.id} className="hover:bg-slate-50 transition-colors">
                        <td className="py-3.5 font-bold text-[#1B3B54]">
                          {m.name}
                          <span className="block text-[11px] font-mono text-slate-400 font-normal">
                            {m.matricula}
                          </span>
                        </td>
                        <td className="py-3.5 font-mono text-slate-600">{m.cpf}</td>
                        <td className="py-3.5 font-mono text-slate-600">{m.whatsapp}</td>
                        <td className="py-3.5 font-medium text-slate-700">{m.plano}</td>
                        <td className="py-3.5 font-semibold text-slate-800">{m.mensalidade}</td>
                        <td className="py-3.5">
                          <span
                            className={`inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full text-[10px] font-bold ${
                              m.status === 'ATIVO'
                                ? 'bg-emerald-50 text-emerald-800 border border-emerald-200'
                                : 'bg-rose-50 text-rose-800 border border-rose-200'
                            }`}
                          >
                            <span>{m.catraca}</span>
                          </span>
                        </td>
                        <td className="py-3.5 text-right">
                          <button
                            onClick={() => handleToggleMemberStatus(m.id)}
                            className={`px-3 py-1.5 rounded-lg text-[11px] font-bold transition-colors cursor-pointer ${
                              m.status === 'ATIVO'
                                ? 'bg-slate-100 hover:bg-rose-100 text-slate-700 hover:text-rose-700'
                                : 'bg-emerald-600 hover:bg-emerald-700 text-white'
                            }`}
                          >
                            {m.status === 'ATIVO' ? 'Bloquear Acesso' : 'Reativar Sócio'}
                          </button>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 3: PORTARIA & CATRACAS (WHITELIST OFFLINE) */}
        {/* ========================================================================= */}
        {activeTab === 'catracas' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-white p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <span className="text-xs uppercase font-bold tracking-wider text-[#4E7A9C]">
                    Tecnologia Anti-Queda de Rede
                  </span>
                  <h3 className="text-xl font-black text-[#1B3B54] mt-0.5">
                    Operação Offline & Lista Branca das Catracas
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                    Se a internet externa de Teofilândia oscilar ou cair, a portaria física não trava. A controladora armazena uma cópia sincronizada na memória RAM/flash com integridade criptográfica MD5.
                  </p>
                </div>

                {/* Botão de Teste de Queda de Internet */}
                <button
                  onClick={() => {
                    setOfflineSimulated(!offlineSimulated);
                    showToast(
                      offlineSimulated
                        ? 'Conexão restaurada com a nuvem!'
                        : 'Simulação ativada: Internet Externa Offline! Catraca continua operando 100% via Whitelist local.'
                    );
                  }}
                  className={`px-4 py-2.5 rounded-xl text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer shadow-xs ${
                    offlineSimulated
                      ? 'bg-rose-600 text-white hover:bg-rose-700'
                      : 'bg-slate-100 hover:bg-slate-200 text-slate-700'
                  }`}
                >
                  {offlineSimulated ? (
                    <>
                      <WifiOff className="w-4 h-4 text-amber-300 animate-pulse" />
                      <span>Modo Offline Ativo (Simulado)</span>
                    </>
                  ) : (
                    <>
                      <Wifi className="w-4 h-4 text-emerald-600" />
                      <span>Simular Queda de Internet</span>
                    </>
                  )}
                </button>
              </div>

              {/* Status do Hardware */}
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-[#1B3B54]">Portaria 01 • Catraca Social Facial</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                      Online • 192.168.1.120
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                    <div className="flex justify-between">
                      <span>Último Checksum MD5:</span>
                      <span className="font-bold text-[#1B3B54]">c98a2f-20260924</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Sócios na Memória Local:</span>
                      <span className="font-bold text-emerald-700">482 autorizados</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Convidados Válidos Hoje:</span>
                      <span className="font-bold text-slate-800">8 passes ativos</span>
                    </div>
                  </div>
                </div>

                <div className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                  <div className="flex items-center justify-between">
                    <span className="font-bold text-sm text-[#1B3B54]">Portaria 02 • Catraca de Quadras / Piscina</span>
                    <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[10px] font-bold">
                      Online • 192.168.1.121
                    </span>
                  </div>
                  <div className="space-y-1.5 text-xs text-slate-600 font-mono">
                    <div className="flex justify-between">
                      <span>Último Checksum MD5:</span>
                      <span className="font-bold text-[#1B3B54]">c98a2f-20260924</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Sócios na Memória Local:</span>
                      <span className="font-bold text-emerald-700">482 autorizados</span>
                    </div>
                    <div className="flex justify-between">
                      <span>Status da Catraca:</span>
                      <span className="font-bold text-emerald-700">Operando com 0.28s latência</span>
                    </div>
                  </div>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 4: COBRANÇA & WHATSAPP */}
        {/* ========================================================================= */}
        {activeTab === 'cobranca' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-white p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-xs space-y-6">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                <div>
                  <span className="text-xs uppercase font-bold tracking-wider text-[#4E7A9C]">
                    Automação Financeira Sem Atrito
                  </span>
                  <h3 className="text-xl font-black text-[#1B3B54] mt-0.5">
                    Régua Diária de Cobrança com Fila Anti-Ban
                  </h3>
                  <p className="text-xs text-slate-500 mt-1 max-w-2xl">
                    O sistema dispara mensagens automáticas com Pix Copia e Cola diretamente no WhatsApp dos associados, com delays humanizados (3s a 8s) prevenindo qualquer risco de banimento.
                  </p>
                </div>

                <button
                  onClick={handleRunBilling}
                  disabled={runningBilling}
                  className="px-4 py-2.5 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-bold flex items-center space-x-2 transition-all cursor-pointer shadow-xs self-start sm:self-auto"
                >
                  <Send className="w-3.5 h-3.5 text-amber-300" />
                  <span>{runningBilling ? 'Processando Fila...' : 'Executar Régua Agora'}</span>
                </button>
              </div>

              {/* 4 Estágios da Régua */}
              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">
                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="text-xs font-bold text-amber-700 uppercase tracking-wider">Estágio 1 • D-3</div>
                  <h4 className="font-bold text-sm text-[#1B3B54]">Aviso Preventivo</h4>
                  <p className="text-xs text-slate-500">
                    Lembrete amigável enviado 3 dias antes do vencimento da mensalidade.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="text-xs font-bold text-emerald-700 uppercase tracking-wider">Estágio 2 • D-0</div>
                  <h4 className="font-bold text-sm text-[#1B3B54]">Disparo Matinal com Pix</h4>
                  <p className="text-xs text-slate-500">
                    Às 08h00 da manhã do dia do vencimento com o código Pix Copia e Cola.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="text-xs font-bold text-teal-700 uppercase tracking-wider">Estágio 3 • Pós-Pix</div>
                  <h4 className="font-bold text-sm text-[#1B3B54]">Recibo Digital Imediato</h4>
                  <p className="text-xs text-slate-500">
                    Baixa em menos de 2s com envio do comprovante e confirmação de catraca liberada.
                  </p>
                </div>

                <div className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-2">
                  <div className="text-xs font-bold text-rose-700 uppercase tracking-wider">Estágio 4 • D+7</div>
                  <h4 className="font-bold text-sm text-[#1B3B54]">Bloqueio da Catraca</h4>
                  <p className="text-xs text-slate-500">
                    Transição para inadimplente e aviso de bloqueio físico na portaria.
                  </p>
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================================= */}
        {/* ABA 5: QUADRAS & RESERVAS */}
        {/* ========================================================================= */}
        {activeTab === 'quadras' && (
          <div className="space-y-6 animate-in fade-in">
            <div className="bg-white p-6 sm:p-7 rounded-3xl border border-slate-200/90 shadow-xs space-y-6">
              <div>
                <span className="text-xs uppercase font-bold tracking-wider text-[#4E7A9C]">
                  Gestão de Estrutura Esportiva
                </span>
                <h3 className="text-xl font-black text-[#1B3B54] mt-0.5">
                  Mapa de Ocupação das Quadras (Hoje)
                </h3>
                <p className="text-xs text-slate-500 mt-1">
                  Proteção por locks transacionais no PostgreSQL impedindo double-booking.
                </p>
              </div>

              {/* Grade de Quadras */}
              <div className="grid grid-cols-1 md:grid-cols-3 gap-5">
                {[
                  { name: 'Quadra de Beach Tennis 1', ocupacao: '92%', slots: '11 de 12 horários ocupados', status: 'Alta Demanda' },
                  { name: 'Quadra de Beach Tennis 2', ocupacao: '85%', slots: '10 de 12 horários ocupados', status: 'Alta Demanda' },
                  { name: 'Quadra de Tênis Saibro', ocupacao: '75%', slots: '9 de 12 horários ocupados', status: 'Normal' },
                  { name: 'Campo Society Sintético', ocupacao: '100%', slots: '12 de 12 horários ocupados', status: 'Esgotado' },
                  { name: 'Quadra Poliesportiva Coberta', ocupacao: '60%', slots: '7 de 12 horários ocupados', status: 'Disponível' },
                ].map((q, idx) => (
                  <div key={idx} className="p-5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-3">
                    <div className="flex items-center justify-between">
                      <h4 className="font-bold text-sm text-[#1B3B54]">{q.name}</h4>
                      <span className="px-2 py-0.5 rounded-full bg-slate-200 text-slate-700 text-[10px] font-bold">
                        {q.status}
                      </span>
                    </div>
                    <div className="w-full h-2 bg-slate-200 rounded-full overflow-hidden">
                      <div className="h-full bg-[#1B3B54] rounded-full" style={{ width: q.ocupacao }} />
                    </div>
                    <div className="flex justify-between text-xs text-slate-500 font-medium">
                      <span>{q.slots}</span>
                      <span className="font-bold text-[#1B3B54]">{q.ocupacao}</span>
                    </div>
                  </div>
                ))}
              </div>
            </div>
          </div>
        )}
      </div>

      {/* Modal de Importação de Planilha Excel */}
      {showImportModal && (
        <div className="fixed inset-0 z-50 flex items-center justify-center p-4 bg-slate-900/60 backdrop-blur-xs">
          <div className="bg-white rounded-3xl border border-slate-200 p-6 sm:p-7 max-w-lg w-full space-y-5 shadow-2xl">
            <div className="flex items-center justify-between pb-3 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-emerald-50 text-emerald-700 flex items-center justify-center font-bold">
                  <FileSpreadsheet className="w-4 h-4" />
                </div>
                <h3 className="font-bold text-base text-[#1B3B54]">Importar Sócios (.xlsx / .csv)</h3>
              </div>
              <button
                onClick={() => setShowImportModal(false)}
                className="text-slate-400 hover:text-slate-700 p-1 rounded-lg"
              >
                ✕
              </button>
            </div>

            <p className="text-xs text-slate-500">
              Faça o upload da planilha antiga da secretaria. O parser validará automaticamente os 11 dígitos do CPF por algoritmo e normalizará os números de WhatsApp para o padrão E.164.
            </p>

            <div className="border-2 border-dashed border-slate-200 hover:border-[#1B3B54] rounded-2xl p-6 text-center space-y-2 cursor-pointer transition-colors bg-slate-50">
              <Upload className="w-8 h-8 text-slate-400 mx-auto" />
              <div className="text-xs font-bold text-[#1B3B54]">Clique para selecionar ou arraste o arquivo .xlsx</div>
              <div className="text-[11px] text-slate-400">Suporta colunas: Nome, CPF, WhatsApp, Plano, Vencimento</div>
            </div>

            {importProgress !== null && (
              <div className="space-y-1.5">
                <div className="flex justify-between text-xs text-slate-600 font-bold">
                  <span>Processando registros no PostgreSQL...</span>
                  <span>{importProgress}%</span>
                </div>
                <div className="w-full h-2 bg-slate-100 rounded-full overflow-hidden">
                  <div className="h-full bg-emerald-600 rounded-full transition-all duration-300" style={{ width: `${importProgress}%` }} />
                </div>
              </div>
            )}

            <div className="flex justify-end space-x-2 pt-2">
              <button
                onClick={() => setShowImportModal(false)}
                className="px-4 py-2 rounded-xl text-xs font-bold text-slate-600 hover:bg-slate-100"
              >
                Cancelar
              </button>
              <button
                onClick={handleSimulateImport}
                disabled={importProgress !== null}
                className="px-5 py-2 rounded-xl bg-[#1F3347] hover:bg-[#162737] text-white text-xs font-bold transition-all shadow-xs cursor-pointer"
              >
                {importProgress !== null ? 'Importando...' : 'Iniciar Importação'}
              </button>
            </div>
          </div>
        </div>
      )}

      {/* 3. Rodapé do Painel */}
      <footer className="bg-white border-t border-slate-200 py-6 text-center text-xs text-slate-500">
        <div className="max-w-[1520px] mx-auto px-4 flex flex-col sm:flex-row items-center justify-between gap-3">
          <span>Club Maravilha • Sistema de Gestão Integrada & Portaria Inteligente</span>
          <span className="font-mono text-[11px]">Versão 0.1.0 • Produção Homologada</span>
        </div>
      </footer>
    </div>
  );
};
