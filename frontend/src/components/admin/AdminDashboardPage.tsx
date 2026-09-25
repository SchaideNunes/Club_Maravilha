import React, { useState } from 'react';
import {
  Users,
  Search,
  CheckCircle2,
  ArrowLeft,
  MessageSquare,
  Plus,
  Edit2,
  Trash2,
  Phone,
  Mail,
  Calendar,
  DollarSign,
  Send,
  Copy,
  X
} from 'lucide-react';
import { ClubeMaravilhaLogo } from '../common/ClubeMaravilhaLogo';
import { PageRoute } from '../layout/Navbar';

export interface Member {
  id: string;
  matricula: string;
  name: string;
  cpf: string;
  phone: string;
  email: string;
  plano: 'Sócio Titular' | 'Familiar Ouro' | 'Individual Esportivo' | 'Sênior';
  vencimento: string;
  status: 'Ativo' | 'Pendente' | 'Inativo';
  cadastradoEm: string;
  observacoes?: string;
}

// Helper para renderizar a mensagem com formatação autêntica do WhatsApp
const renderWhatsAppFormattedContent = (content: string) => {
  if (!content) return null;

  const lines = content.split('\n');

  return lines.map((line, lineIndex) => {
    // Linha vazia vira espaçador
    if (!line.trim()) {
      return <div key={lineIndex} className="h-1.5" />;
    }

    // Se for o código Pix Copia e Cola (código longo EMVCo ou linha do Pix)
    const isPixCode =
      line.trim().startsWith('00020126') ||
      (line.trim().length > 40 && !line.includes(' '));

    if (isPixCode) {
      return (
        <div
          key={lineIndex}
          className="my-2 p-2.5 rounded-xl bg-slate-50 border border-slate-200/90 text-slate-800 select-all shadow-2xs overflow-hidden"
        >
          <div className="flex items-center justify-between text-[10px] font-sans font-bold text-slate-500 uppercase tracking-wider mb-1.5">
            <span className="flex items-center space-x-1">
              <span>💳</span>
              <span>Chave Pix Copia e Cola</span>
            </span>
            <span className="text-emerald-700 font-semibold text-[9px] bg-emerald-100 px-1.5 py-0.5 rounded">
              Toque para copiar
            </span>
          </div>
          <div className="font-mono text-[10px] leading-relaxed break-all bg-white p-2 rounded-lg border border-slate-200 text-slate-700 select-all">
            {line.trim()}
          </div>
        </div>
      );
    }

    // Renderiza linha normal formatando *negrito* e links
    const parts = line.split(/(\*[^*]+\*|https?:\/\/[^\s]+)/g);

    return (
      <div key={lineIndex} className="leading-relaxed break-words break-all text-xs text-slate-800 font-sans">
        {parts.map((part, partIdx) => {
          if (part.startsWith('*') && part.endsWith('*') && part.length > 2) {
            return (
              <strong key={partIdx} className="font-bold text-slate-950">
                {part.slice(1, -1)}
              </strong>
            );
          }
          if (part.startsWith('http://') || part.startsWith('https://')) {
            return (
              <span
                key={partIdx}
                className="text-sky-600 underline font-medium break-all"
              >
                {part}
              </span>
            );
          }
          return <span key={partIdx}>{part}</span>;
        })}
      </div>
    );
  });
};

interface AdminDashboardPageProps {
  onBackToHome: () => void;
  onNavigatePage: (page: PageRoute) => void;
}

export const AdminDashboardPage: React.FC<AdminDashboardPageProps> = ({
  onBackToHome,
  onNavigatePage
}) => {
  // Tabs: 'cadastros' (Administração de Sócios), 'whatsapp' (Estilo da Mensagem WhatsApp), 'reservas' (Quadras), 'resumo' (Visão Geral)
  const [activeTab, setActiveTab] = useState<'cadastros' | 'whatsapp' | 'reservas' | 'resumo'>('cadastros');

  // Feedback Toast
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Base inicial de associados
  const [members, setMembers] = useState<Member[]>([
    {
      id: '1',
      matricula: '#2026-0042',
      name: 'Schaide Nunes',
      cpf: '123.456.789-00',
      phone: '(75) 99876-5432',
      email: 'schaide.nunes@email.com',
      plano: 'Sócio Titular',
      vencimento: 'Dia 10',
      status: 'Ativo',
      cadastradoEm: '12/01/2026',
      observacoes: 'Diretoria / Titular'
    },
    {
      id: '2',
      matricula: '#2026-0043',
      name: 'Ana Clara Silva',
      cpf: '234.567.890-11',
      phone: '(75) 99123-4567',
      email: 'ana.clara@email.com',
      plano: 'Familiar Ouro',
      vencimento: 'Dia 10',
      status: 'Ativo',
      cadastradoEm: '15/01/2026',
      observacoes: '3 dependentes incluídos'
    },
    {
      id: '3',
      matricula: '#2026-0044',
      name: 'Roberto Mendes',
      cpf: '345.678.901-22',
      phone: '(75) 99234-5678',
      email: 'roberto.mendes@email.com',
      plano: 'Individual Esportivo',
      vencimento: 'Dia 15',
      status: 'Ativo',
      cadastradoEm: '02/02/2026',
      observacoes: 'Frequenta Beach Tennis e Natação'
    },
    {
      id: '4',
      matricula: '#2026-0045',
      name: 'Carlos Eduardo Santos',
      cpf: '456.789.012-33',
      phone: '(75) 99345-6789',
      email: 'carlos.santos@email.com',
      plano: 'Familiar Ouro',
      vencimento: 'Dia 05',
      status: 'Pendente',
      cadastradoEm: '10/02/2026',
      observacoes: 'Aguardando confirmação de pagamento Pix'
    },
    {
      id: '5',
      matricula: '#2026-0046',
      name: 'Juliana Paiva',
      cpf: '567.890.123-44',
      phone: '(75) 99456-7890',
      email: 'juliana.paiva@email.com',
      plano: 'Sênior',
      vencimento: 'Dia 20',
      status: 'Ativo',
      cadastradoEm: '18/02/2026',
      observacoes: 'Hidroginástica terças e quintas'
    },
    {
      id: '6',
      matricula: '#2026-0047',
      name: 'Lucas Fernandes',
      cpf: '678.901.234-55',
      phone: '(75) 99567-8901',
      email: 'lucas.fernandes@email.com',
      plano: 'Individual Esportivo',
      vencimento: 'Dia 10',
      status: 'Ativo',
      cadastradoEm: '24/02/2026',
      observacoes: 'Futebol Society semanal'
    },
    {
      id: '7',
      matricula: '#2026-0048',
      name: 'Beatriz Moreira',
      cpf: '789.012.345-66',
      phone: '(75) 99678-9012',
      email: 'beatriz.moreira@email.com',
      plano: 'Sócio Titular',
      vencimento: 'Dia 05',
      status: 'Inativo',
      cadastradoEm: '05/01/2026',
      observacoes: 'Solicitou trancamento temporário'
    }
  ]);

  // Filtros e busca de associados
  const [searchQuery, setSearchQuery] = useState('');
  const [statusFilter, setStatusFilter] = useState<'TODOS' | 'Ativo' | 'Pendente' | 'Inativo'>('TODOS');

  // Modais de Criação e Edição
  const [isNewModalOpen, setIsNewModalOpen] = useState(false);
  const [editingMember, setEditingMember] = useState<Member | null>(null);

  // Form State para Novo/Editar
  const [formData, setFormData] = useState<{
    name: string;
    cpf: string;
    phone: string;
    email: string;
    plano: 'Sócio Titular' | 'Familiar Ouro' | 'Individual Esportivo' | 'Sênior';
    vencimento: string;
    status: 'Ativo' | 'Pendente' | 'Inativo';
    observacoes: string;
  }>({
    name: '',
    cpf: '',
    phone: '',
    email: '',
    plano: 'Sócio Titular',
    vencimento: 'Dia 10',
    status: 'Ativo',
    observacoes: ''
  });

  // Estado da aba WhatsApp
  const [selectedMemberForWhatsApp, setSelectedMemberForWhatsApp] = useState<Member>(members[0]);
  const [messageTemplate, setMessageTemplate] = useState<'boas_vindas' | 'mensalidade_pix' | 'reserva_quadra' | 'comunicado'>('mensalidade_pix');
  const [customMessage, setCustomMessage] = useState<string>('');

  // Sincroniza a mensagem customizada quando troca o template ou o associado selecionado
  React.useEffect(() => {
    const memberName = selectedMemberForWhatsApp?.name || 'Associado';
    const memberPlan = selectedMemberForWhatsApp?.plano || 'Sócio Titular';
    const memberMatricula = selectedMemberForWhatsApp?.matricula || '#2026-0042';
    const memberVencimento = selectedMemberForWhatsApp?.vencimento || 'Dia 10';

    if (messageTemplate === 'boas_vindas') {
      setCustomMessage(
        `Olá, *${memberName}*! 👋 Seja muito bem-vindo(a) ao *Clube Maravilha*!\n\n` +
        `Seu cadastro no plano *${memberPlan}* foi confirmado com sucesso. Sua matrícula é *${memberMatricula}*.\n\n` +
        `Você já pode usufruir de todas as instalações (piscinas, quadras e áreas de convivência) e acessar o portal do sócio:\n` +
        `👉 https://clubmaravilha.com.br/#/usuario\n\n` +
        `Qualquer dúvida, nossa secretaria está à sua disposição!`
      );
    } else if (messageTemplate === 'mensalidade_pix') {
      setCustomMessage(
        `Olá, *${memberName}*! Tudo bem?\n\n` +
        `Lembramos que a mensalidade do *Clube Maravilha* referente ao plano *${memberPlan}* vence no *${memberVencimento}*.\n\n` +
        `💰 *Valor:* R$ 150,00\n\n` +
        `Para sua comodidade, pague diretamente pelo *Pix Copia e Cola*:\n` +
        `00020126580014br.gov.bcb.pix0136clube-maravilha-pix-759987654325204000053039865405150005802BR5915CLUBEMARAVILHA6009TEOFILANDIA62070503***6304\n\n` +
        `A baixa é confirmada no sistema em poucos instantes após o pagamento! 🚀`
      );
    } else if (messageTemplate === 'reserva_quadra') {
      setCustomMessage(
        `Olá, *${memberName}*! 🎾\n\n` +
        `Sua reserva de espaço no *Clube Maravilha* está confirmada!\n\n` +
        `📍 *Local:* Quadra de Beach Tennis 01\n` +
        `📅 *Data:* Sábado às 16:00 (1 hora)\n` +
        `👥 *Modalidade:* Uso Livre do Associado\n\n` +
        `Aproveite seu jogo e tenha uma excelente experiência!`
      );
    } else if (messageTemplate === 'comunicado') {
      setCustomMessage(
        `Prezado(a) associado(a) *${memberName}*,\n\n` +
        `Neste fim de semana teremos o nosso tradicional *Torneio Interno de Integração & Música ao Vivo* na área das piscinas! 🎶🏊‍♂️\n\n` +
        `Traga sua família para curtir um dia agradável no Clube Maravilha a partir das 15h. Esperamos por você!`
      );
    }
  }, [messageTemplate, selectedMemberForWhatsApp]);

  // Abertura do Modal de Novo Cadastro
  const handleOpenNewModal = () => {
    setFormData({
      name: '',
      cpf: '',
      phone: '',
      email: '',
      plano: 'Sócio Titular',
      vencimento: 'Dia 10',
      status: 'Ativo',
      observacoes: ''
    });
    setIsNewModalOpen(true);
  };

  // Abertura do Modal de Edição
  const handleOpenEditModal = (member: Member) => {
    setEditingMember(member);
    setFormData({
      name: member.name,
      cpf: member.cpf,
      phone: member.phone,
      email: member.email,
      plano: member.plano,
      vencimento: member.vencimento,
      status: member.status,
      observacoes: member.observacoes || ''
    });
  };

  // Salvar Novo Associado
  const handleSaveNewMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!formData.name.trim()) {
      showToast('Por favor, informe o nome do associado.');
      return;
    }

    const nextNumber = members.length + 42;
    const newMember: Member = {
      id: Date.now().toString(),
      matricula: `#2026-00${nextNumber}`,
      name: formData.name.trim(),
      cpf: formData.cpf.trim() || '000.000.000-00',
      phone: formData.phone.trim() || '(75) 99999-9999',
      email: formData.email.trim() || 'socio@clubmaravilha.com.br',
      plano: formData.plano,
      vencimento: formData.vencimento,
      status: formData.status,
      cadastradoEm: new Date().toLocaleDateString('pt-BR'),
      observacoes: formData.observacoes.trim()
    };

    setMembers([newMember, ...members]);
    setIsNewModalOpen(false);
    showToast(`Associado "${newMember.name}" cadastrado com sucesso!`);
  };

  // Salvar Edição de Associado
  const handleSaveEditMember = (e: React.FormEvent) => {
    e.preventDefault();
    if (!editingMember) return;

    const updated = members.map((m) => {
      if (m.id === editingMember.id) {
        return {
          ...m,
          name: formData.name.trim(),
          cpf: formData.cpf.trim(),
          phone: formData.phone.trim(),
          email: formData.email.trim(),
          plano: formData.plano,
          vencimento: formData.vencimento,
          status: formData.status,
          observacoes: formData.observacoes.trim()
        };
      }
      return m;
    });

    setMembers(updated);
    setEditingMember(null);
    showToast(`Cadastro de "${formData.name}" atualizado.`);
  };

  // Alternar Status Direto
  const handleToggleStatus = (memberId: string) => {
    setMembers((prev) =>
      prev.map((m) => {
        if (m.id === memberId) {
          const nextStatus = m.status === 'Ativo' ? 'Inativo' : 'Ativo';
          showToast(`Status de ${m.name} alterado para ${nextStatus}.`);
          return { ...m, status: nextStatus };
        }
        return m;
      })
    );
  };

  // Remover associado
  const handleDeleteMember = (member: Member) => {
    if (window.confirm(`Deseja realmente remover o cadastro de ${member.name}?`)) {
      setMembers((prev) => prev.filter((m) => m.id !== member.id));
      showToast(`Cadastro de ${member.name} removido.`);
    }
  };

  // Ir para WhatsApp com o associado selecionado
  const handleGoToWhatsAppForMember = (member: Member) => {
    setSelectedMemberForWhatsApp(member);
    setActiveTab('whatsapp');
  };

  // Filtragem da lista
  const filteredMembers = members.filter((m) => {
    const matchesSearch =
      m.name.toLowerCase().includes(searchQuery.toLowerCase()) ||
      m.cpf.includes(searchQuery) ||
      m.phone.includes(searchQuery) ||
      m.matricula.toLowerCase().includes(searchQuery.toLowerCase());

    const matchesStatus =
      statusFilter === 'TODOS' ? true : m.status === statusFilter;

    return matchesSearch && matchesStatus;
  });

  // Estatísticas calculadas
  const totalCadastros = members.length;
  const totalAtivos = members.filter((m) => m.status === 'Ativo').length;
  const totalPendentes = members.filter((m) => m.status === 'Pendente').length;
  const totalInativos = members.filter((m) => m.status === 'Inativo').length;

  return (
    <div className="min-h-screen bg-[#F8FAFC] text-slate-800 flex flex-col font-sans">
      {/* Toast Notification */}
      {toastMessage && (
        <div className="fixed bottom-6 right-6 z-50 bg-[#1B3B54] text-white px-5 py-3.5 rounded-2xl shadow-xl border border-slate-700/50 flex items-center space-x-3 text-sm animate-in fade-in slide-in-from-bottom-4 duration-200">
          <CheckCircle2 className="w-5 h-5 text-emerald-400 shrink-0" />
          <span className="font-medium">{toastMessage}</span>
        </div>
      )}

      {/* 1. Header do Painel Administrativo */}
      <header className="sticky top-0 z-40 bg-[#1B3B54] text-white border-b border-slate-700/60 shadow-sm">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12 h-20 flex items-center justify-between">
          <div className="flex items-center space-x-4">
            <button
              onClick={onBackToHome}
              className="flex items-center space-x-2 focus:outline-none hover:opacity-90 transition-opacity cursor-pointer"
            >
              <ClubeMaravilhaLogo variant="on-blue" size="md" />
            </button>
            <div className="h-6 w-px bg-white/20 hidden sm:block"></div>
            <div>
              <span className="text-xs uppercase font-extrabold tracking-wider text-amber-300 block">
                Painel Administrativo
              </span>
              <span className="text-sm font-semibold text-white/90">
                Gestão do Clube Maravilha
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-3">
            <button
              onClick={onBackToHome}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-white/10 hover:bg-white/20 text-white text-xs font-semibold transition-colors cursor-pointer"
            >
              <ArrowLeft className="w-3.5 h-3.5" />
              <span>Voltar ao Site</span>
            </button>
            <button
              onClick={() => onNavigatePage('usuario')}
              className="flex items-center space-x-1.5 px-3.5 py-1.5 rounded-xl bg-[#6899BA] hover:bg-[#5b89a8] text-white text-xs font-semibold transition-colors cursor-pointer shadow-xs"
            >
              <Users className="w-3.5 h-3.5" />
              <span>Ver Visão do Sócio</span>
            </button>
          </div>
        </div>
      </header>

      {/* 2. Barra de Navegação de Abas */}
      <div className="bg-white border-b border-slate-200">
        <div className="max-w-[1520px] mx-auto px-4 sm:px-8 xl:px-12">
          <div className="flex space-x-2 sm:space-x-8 overflow-x-auto scrollbar-none py-3">
            <button
              onClick={() => setActiveTab('cadastros')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors cursor-pointer shrink-0 ${
                activeTab === 'cadastros'
                  ? 'bg-[#1B3B54] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Users className="w-4 h-4" />
              <span>Administração de Cadastros</span>
              <span className={`text-xs px-2 py-0.5 rounded-full font-semibold ${
                activeTab === 'cadastros' ? 'bg-white/20 text-white' : 'bg-slate-200 text-slate-700'
              }`}>
                {members.length}
              </span>
            </button>

            <button
              onClick={() => setActiveTab('whatsapp')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors cursor-pointer shrink-0 ${
                activeTab === 'whatsapp'
                  ? 'bg-[#1B3B54] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <MessageSquare className="w-4 h-4 text-emerald-500" />
              <span>Estilo da Mensagem no WhatsApp</span>
            </button>

            <button
              onClick={() => setActiveTab('reservas')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors cursor-pointer shrink-0 ${
                activeTab === 'reservas'
                  ? 'bg-[#1B3B54] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <Calendar className="w-4 h-4" />
              <span>Reservas das Quadras</span>
            </button>

            <button
              onClick={() => setActiveTab('resumo')}
              className={`flex items-center space-x-2 px-3 py-2 rounded-xl text-sm font-bold transition-colors cursor-pointer shrink-0 ${
                activeTab === 'resumo'
                  ? 'bg-[#1B3B54] text-white shadow-xs'
                  : 'text-slate-600 hover:text-slate-900 hover:bg-slate-100'
              }`}
            >
              <DollarSign className="w-4 h-4" />
              <span>Visão Geral & Indicadores</span>
            </button>
          </div>
        </div>
      </div>

      {/* 3. Conteúdo Principal */}
      <main className="max-w-[1520px] mx-auto w-full px-4 sm:px-8 xl:px-12 py-8 flex-1">
        {/* ========================================================
            ABA 1: ADMINISTRAÇÃO DE CADASTROS (FOCO PRINCIPAL)
        ======================================================== */}
        {activeTab === 'cadastros' && (
          <div className="space-y-6">
            {/* Cards de Resumo Rápido de Cadastros */}
            <div className="grid grid-cols-2 lg:grid-cols-4 gap-4">
              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 block">Total de Cadastros</span>
                <span className="text-2xl font-black text-[#1B3B54] mt-1 block">{totalCadastros}</span>
                <span className="text-[11px] text-slate-400">Associados registrados</span>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 block">Ativos / Em Dia</span>
                <span className="text-2xl font-black text-emerald-600 mt-1 block">{totalAtivos}</span>
                <span className="text-[11px] text-emerald-700 font-medium">{Math.round((totalAtivos / totalCadastros) * 100)}% da base</span>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 block">Pagamento Pendente</span>
                <span className="text-2xl font-black text-amber-600 mt-1 block">{totalPendentes}</span>
                <span className="text-[11px] text-amber-700 font-medium">Aguardando mensalidade</span>
              </div>
              <div className="bg-white p-4 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-semibold text-slate-500 block">Inativos / Trancados</span>
                <span className="text-2xl font-black text-slate-500 mt-1 block">{totalInativos}</span>
                <span className="text-[11px] text-slate-400">Suspensos ou cancelados</span>
              </div>
            </div>

            {/* Cabeçalho de Ações: Busca, Filtros e Botão Novo Associado */}
            <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs space-y-4">
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
                <div>
                  <h2 className="text-lg font-bold text-[#1B3B54]">Gestão de Associados</h2>
                  <p className="text-xs text-slate-500">
                    Cadastre novos sócios, atualize informações de contato e consulte o status da mensalidade.
                  </p>
                </div>

                <button
                  onClick={handleOpenNewModal}
                  className="inline-flex items-center justify-center space-x-2 px-4 py-2.5 rounded-xl bg-[#1B3B54] hover:bg-[#152e42] text-white text-xs font-bold transition-colors cursor-pointer shadow-xs"
                >
                  <Plus className="w-4 h-4 text-amber-300" />
                  <span>Novo Associado</span>
                </button>
              </div>

              {/* Barra de Filtro e Busca */}
              <div className="flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-3 pt-3 border-t border-slate-100">
                <div className="relative flex-1 max-w-md">
                  <Search className="w-4 h-4 text-slate-400 absolute left-3.5 top-1/2 -translate-y-1/2" />
                  <input
                    type="text"
                    placeholder="Buscar por nome, CPF, WhatsApp ou matrícula..."
                    value={searchQuery}
                    onChange={(e) => setSearchQuery(e.target.value)}
                    className="w-full pl-9 pr-4 py-2 rounded-xl border border-slate-200 text-xs focus:outline-none focus:border-[#4E7A9C] bg-slate-50/50"
                  />
                  {searchQuery && (
                    <button
                      onClick={() => setSearchQuery('')}
                      className="absolute right-3 top-1/2 -translate-y-1/2 text-slate-400 hover:text-slate-600 text-xs"
                    >
                      Limpar
                    </button>
                  )}
                </div>

                <div className="flex items-center space-x-1.5 overflow-x-auto scrollbar-none">
                  {(['TODOS', 'Ativo', 'Pendente', 'Inativo'] as const).map((st) => (
                    <button
                      key={st}
                      onClick={() => setStatusFilter(st)}
                      className={`px-3 py-1.5 rounded-lg text-xs font-semibold transition-colors cursor-pointer ${
                        statusFilter === st
                          ? 'bg-[#1B3B54] text-white'
                          : 'bg-slate-100 hover:bg-slate-200 text-slate-600'
                      }`}
                    >
                      {st === 'TODOS' ? 'Todos os Status' : st}
                    </button>
                  ))}
                </div>
              </div>
            </div>

            {/* Tabela de Associados */}
            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200/90 text-slate-500 font-bold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Matrícula</th>
                      <th className="py-3 px-4">Nome do Sócio</th>
                      <th className="py-3 px-4">Contato (WhatsApp / E-mail)</th>
                      <th className="py-3 px-4">Plano / Categoria</th>
                      <th className="py-3 px-4">Vencimento</th>
                      <th className="py-3 px-4">Status</th>
                      <th className="py-3 px-4 text-right">Ações</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    {filteredMembers.length === 0 ? (
                      <tr>
                        <td colSpan={7} className="py-12 text-center text-slate-400">
                          Nenhum associado encontrado para os filtros selecionados.
                        </td>
                      </tr>
                    ) : (
                      filteredMembers.map((m) => (
                        <tr key={m.id} className="hover:bg-slate-50/70 transition-colors">
                          <td className="py-3.5 px-4 font-mono font-bold text-slate-700">
                            {m.matricula}
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="font-bold text-slate-900">{m.name}</div>
                            <div className="text-[11px] text-slate-400 font-mono">CPF: {m.cpf}</div>
                          </td>
                          <td className="py-3.5 px-4">
                            <div className="flex items-center space-x-1.5 text-slate-700 font-medium">
                              <Phone className="w-3 h-3 text-slate-400" />
                              <span>{m.phone}</span>
                            </div>
                            <div className="text-[11px] text-slate-400 flex items-center space-x-1.5 mt-0.5">
                              <Mail className="w-3 h-3 text-slate-400" />
                              <span className="truncate max-w-[160px]">{m.email}</span>
                            </div>
                          </td>
                          <td className="py-3.5 px-4">
                            <span className="inline-block px-2.5 py-1 rounded-md bg-slate-100 text-slate-700 font-semibold text-[11px]">
                              {m.plano}
                            </span>
                            {m.observacoes && (
                              <div className="text-[10px] text-slate-400 mt-0.5 truncate max-w-[160px]" title={m.observacoes}>
                                {m.observacoes}
                              </div>
                            )}
                          </td>
                          <td className="py-3.5 px-4 text-slate-600 font-medium">
                            {m.vencimento}
                          </td>
                          <td className="py-3.5 px-4">
                            <button
                              onClick={() => handleToggleStatus(m.id)}
                              className={`inline-flex items-center space-x-1 px-2.5 py-1 rounded-full text-[11px] font-bold transition-opacity hover:opacity-80 cursor-pointer ${
                                m.status === 'Ativo'
                                  ? 'bg-emerald-100 text-emerald-800'
                                  : m.status === 'Pendente'
                                  ? 'bg-amber-100 text-amber-800'
                                  : 'bg-slate-200 text-slate-700'
                              }`}
                              title="Clique para alternar o status do associado"
                            >
                              <span className={`w-1.5 h-1.5 rounded-full ${
                                m.status === 'Ativo' ? 'bg-emerald-500' : m.status === 'Pendente' ? 'bg-amber-500' : 'bg-slate-400'
                              }`}></span>
                              <span>{m.status}</span>
                            </button>
                          </td>
                          <td className="py-3.5 px-4 text-right">
                            <div className="inline-flex items-center space-x-1">
                              {/* Botão Ver no WhatsApp */}
                              <button
                                onClick={() => handleGoToWhatsAppForMember(m)}
                                className="p-1.5 rounded-lg text-emerald-600 hover:bg-emerald-50 transition-colors cursor-pointer"
                                title="Ver estilo da mensagem no WhatsApp para este associado"
                              >
                                <MessageSquare className="w-4 h-4" />
                              </button>

                              {/* Botão Editar */}
                              <button
                                onClick={() => handleOpenEditModal(m)}
                                className="p-1.5 rounded-lg text-blue-600 hover:bg-blue-50 transition-colors cursor-pointer"
                                title="Editar dados cadastrais"
                              >
                                <Edit2 className="w-4 h-4" />
                              </button>

                              {/* Botão Excluir */}
                              <button
                                onClick={() => handleDeleteMember(m)}
                                className="p-1.5 rounded-lg text-rose-500 hover:bg-rose-50 transition-colors cursor-pointer"
                                title="Remover associado"
                              >
                                <Trash2 className="w-4 h-4" />
                              </button>
                            </div>
                          </td>
                        </tr>
                      ))
                    )}
                  </tbody>
                </table>
              </div>
              <div className="p-4 bg-slate-50 border-t border-slate-200 text-xs text-slate-500 flex items-center justify-between">
                <span>Exibindo {filteredMembers.length} de {members.length} associados</span>
                <span className="text-[11px] text-slate-400">
                  Dica: Para cadastrar ou editar sem afetar o sistema, use os botões na tabela.
                </span>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================
            ABA 2: ESTILO DA MENSAGEM NO WHATSAPP (PEDIDO EXPLÍCITO)
        ======================================================== */}
        {activeTab === 'whatsapp' && (
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
            {/* Coluna Esquerda: Controles, Templates e Configurações */}
            <div className="lg:col-span-6 space-y-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-5">
                <div>
                  <div className="flex items-center space-x-2 text-emerald-600 font-bold text-xs uppercase tracking-wider">
                    <MessageSquare className="w-4 h-4" />
                    <span>Notificações Automáticas</span>
                  </div>
                  <h2 className="text-xl font-black text-[#1B3B54] mt-1">
                    Estilo da Mensagem que Chega no WhatsApp
                  </h2>
                  <p className="text-xs text-slate-500 mt-1">
                    Veja exatamente como o associado visualiza a mensagem no celular dele.
                  </p>
                </div>

                {/* Seleção do Associado de Exemplo */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">
                    Associado Selecionado para a Demonstração:
                  </label>
                  <select
                    value={selectedMemberForWhatsApp?.id}
                    onChange={(e) => {
                      const found = members.find((m) => m.id === e.target.value);
                      if (found) setSelectedMemberForWhatsApp(found);
                    }}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 text-xs font-semibold bg-slate-50 focus:outline-none focus:border-[#4E7A9C]"
                  >
                    {members.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.name} ({m.plano} • Vencimento: {m.vencimento})
                      </option>
                    ))}
                  </select>
                </div>

                {/* Seletor de Modelos de Mensagens */}
                <div>
                  <label className="block text-xs font-bold text-slate-700 mb-1.5">
                    Selecione o Tipo de Mensagem:
                  </label>
                  <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5">
                    <button
                      onClick={() => setMessageTemplate('mensalidade_pix')}
                      className={`p-3 rounded-xl border text-left text-xs transition-colors cursor-pointer ${
                        messageTemplate === 'mensalidade_pix'
                          ? 'border-emerald-500 bg-emerald-50/50 text-emerald-950 font-bold'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <span className="block font-bold">💳 Mensalidade & Pix</span>
                      <span className="text-[11px] text-slate-500">Lembrete com código Pix Copia e Cola</span>
                    </button>

                    <button
                      onClick={() => setMessageTemplate('boas_vindas')}
                      className={`p-3 rounded-xl border text-left text-xs transition-colors cursor-pointer ${
                        messageTemplate === 'boas_vindas'
                          ? 'border-emerald-500 bg-emerald-50/50 text-emerald-950 font-bold'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <span className="block font-bold">👋 Boas-Vindas & Acesso</span>
                      <span className="text-[11px] text-slate-500">Enviada após novo cadastro</span>
                    </button>

                    <button
                      onClick={() => setMessageTemplate('reserva_quadra')}
                      className={`p-3 rounded-xl border text-left text-xs transition-colors cursor-pointer ${
                        messageTemplate === 'reserva_quadra'
                          ? 'border-emerald-500 bg-emerald-50/50 text-emerald-950 font-bold'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <span className="block font-bold">🎾 Reserva de Quadra</span>
                      <span className="text-[11px] text-slate-500">Confirmação de Beach Tennis</span>
                    </button>

                    <button
                      onClick={() => setMessageTemplate('comunicado')}
                      className={`p-3 rounded-xl border text-left text-xs transition-colors cursor-pointer ${
                        messageTemplate === 'comunicado'
                          ? 'border-emerald-500 bg-emerald-50/50 text-emerald-950 font-bold'
                          : 'border-slate-200 hover:border-slate-300 text-slate-700'
                      }`}
                    >
                      <span className="block font-bold">📢 Comunicado de Evento</span>
                      <span className="text-[11px] text-slate-500">Aviso sobre shows e finais de semana</span>
                    </button>
                  </div>
                </div>

                {/* Editor Interativo do Texto da Mensagem */}
                <div>
                  <div className="flex items-center justify-between mb-1.5">
                    <label className="text-xs font-bold text-slate-700">
                      Editar Texto da Mensagem:
                    </label>
                    <span className="text-[10px] text-slate-400">
                      Altere o texto e veja o balão do WhatsApp mudar ao vivo
                    </span>
                  </div>
                  <textarea
                    rows={5}
                    value={customMessage}
                    onChange={(e) => setCustomMessage(e.target.value)}
                    className="w-full p-3 rounded-xl border border-slate-200 text-xs font-mono bg-slate-50/50 focus:outline-none focus:border-[#4E7A9C]"
                  />
                </div>

                {/* Botões de Ação */}
                <div className="flex items-center space-x-3 pt-2">
                  <button
                    onClick={() => {
                      navigator.clipboard.writeText(customMessage);
                      showToast('Texto da mensagem copiado para a área de transferência!');
                    }}
                    className="flex-1 py-2.5 px-4 rounded-xl border border-slate-200 hover:bg-slate-50 text-slate-700 text-xs font-bold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer"
                  >
                    <Copy className="w-3.5 h-3.5" />
                    <span>Copiar Mensagem</span>
                  </button>

                  <button
                    onClick={() => {
                      showToast(`Mensagem de teste disparada para ${selectedMemberForWhatsApp.phone}!`);
                    }}
                    className="flex-1 py-2.5 px-4 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white text-xs font-bold flex items-center justify-center space-x-1.5 transition-colors cursor-pointer shadow-xs"
                  >
                    <Send className="w-3.5 h-3.5" />
                    <span>Simular Envio ao Sócio</span>
                  </button>
                </div>
              </div>
            </div>

            {/* Coluna Direita: O Mockup Autêntico do WhatsApp (Smartphone Frame) */}
            <div className="lg:col-span-6 flex justify-center">
              <div className="w-full max-w-[390px] rounded-[36px] bg-slate-900 p-3 shadow-2xl border-4 border-slate-800">
                {/* Dynamic Island / Notch do celular */}
                <div className="w-28 h-4 bg-black rounded-full mx-auto mb-2"></div>

                {/* Tela do Celular com Interface do WhatsApp */}
                <div className="bg-[#EFEAE2] rounded-[28px] overflow-hidden flex flex-col h-[580px] shadow-inner relative border border-slate-300">
                  {/* WhatsApp Topbar */}
                  <div className="bg-[#075E54] text-white px-3.5 py-2.5 flex items-center justify-between shrink-0 shadow-xs">
                    <div className="flex items-center space-x-2.5">
                      <ArrowLeft className="w-4 h-4 cursor-pointer text-white/90" />
                      <div className="w-9 h-9 rounded-full bg-amber-400 text-slate-900 font-bold flex items-center justify-center text-xs shadow-xs">
                        CM
                      </div>
                      <div>
                        <div className="flex items-center space-x-1">
                          <span className="font-bold text-xs leading-tight">Clube Maravilha</span>
                          <span className="w-3 h-3 rounded-full bg-emerald-400 text-[8px] text-slate-900 font-black inline-flex items-center justify-center">
                            ✓
                          </span>
                        </div>
                        <span className="text-[10px] text-white/80 block leading-tight">
                          Conta Comercial Oficial
                        </span>
                      </div>
                    </div>

                    <div className="flex items-center space-x-3 text-white/90">
                      <Phone className="w-4 h-4" />
                      <div className="w-1 h-3 flex flex-col justify-between">
                        <span className="w-1 h-1 bg-white rounded-full"></span>
                        <span className="w-1 h-1 bg-white rounded-full"></span>
                        <span className="w-1 h-1 bg-white rounded-full"></span>
                      </div>
                    </div>
                  </div>

                  {/* Fundo do Chat (Estilo WhatsApp) */}
                  <div className="flex-1 p-3.5 overflow-y-auto space-y-3 flex flex-col justify-end">
                    {/* Badge de Data */}
                    <div className="text-center my-1">
                      <span className="px-2.5 py-0.5 rounded-md bg-white/80 text-[10px] font-semibold text-slate-600 shadow-xs">
                        HOJE
                      </span>
                    </div>

                    {/* Aviso de Criptografia do WhatsApp */}
                    <div className="p-2 rounded-lg bg-[#FCF4CB] text-[#54656F] text-[10px] text-center shadow-xs border border-amber-200/50">
                      🔒 As mensagens são protegidas com a criptografia de ponta a ponta do WhatsApp Oficial.
                    </div>

                    {/* Balão da Mensagem Recebida do Clube */}
                    <div className="self-start max-w-[90%] bg-white rounded-2xl rounded-tl-none p-3.5 shadow-sm border border-slate-200/70 relative animate-in fade-in zoom-in-95 duration-200">
                      {/* Rabicho estilo WhatsApp recebido */}
                      <div className="absolute top-0 -left-1.5 w-0 h-0 border-t-[8px] border-t-white border-l-[8px] border-l-transparent"></div>

                      {/* Remetente Interno */}
                      <div className="flex items-center space-x-1.5 pb-1.5 mb-2 border-b border-slate-100 text-[10px] text-emerald-700 font-bold">
                        <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                        <span>Clube Maravilha • Secretaria</span>
                      </div>

                      {/* Conteúdo com Formatação Real do WhatsApp */}
                      <div className="space-y-0.5">
                        {renderWhatsAppFormattedContent(customMessage)}
                      </div>

                      {/* Hora da mensagem (mensagem recebida no WhatsApp mostra apenas o horário) */}
                      <div className="flex items-center justify-end space-x-1 mt-1.5 text-[10px] text-slate-400 font-sans">
                        <span>10:42</span>
                      </div>
                    </div>
                  </div>

                  {/* WhatsApp Input Bar Simulado */}
                  <div className="bg-[#F0F2F5] px-2.5 py-2 flex items-center space-x-2 shrink-0 border-t border-slate-200">
                    <div className="flex-1 bg-white rounded-full px-3.5 py-1.5 text-xs text-slate-400 border border-slate-200">
                      Mensagem
                    </div>
                    <div className="w-8 h-8 rounded-full bg-[#00A884] text-white flex items-center justify-center">
                      <Send className="w-3.5 h-3.5 ml-0.5" />
                    </div>
                  </div>
                </div>

                <div className="text-center mt-2 text-[11px] text-slate-400">
                  Visualização da tela do sócio ({selectedMemberForWhatsApp?.phone})
                </div>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================
            ABA 3: RESERVAS DE QUADRAS (SEM CATRACAS)
        ======================================================== */}
        {activeTab === 'reservas' && (
          <div className="space-y-6">
            <div className="bg-white p-5 rounded-2xl border border-slate-200/90 shadow-xs flex flex-col sm:flex-row items-stretch sm:items-center justify-between gap-4">
              <div>
                <h2 className="text-lg font-bold text-[#1B3B54]">Agenda de Reservas de Hoje</h2>
                <p className="text-xs text-slate-500">
                  Consulte os horários agendados pelos sócios para as quadras esportivas.
                </p>
              </div>

              <div className="flex items-center space-x-2 text-xs">
                <span className="font-bold text-slate-700">Data:</span>
                <span className="px-3 py-1.5 rounded-lg bg-slate-100 font-semibold text-slate-800">
                  Hoje • Sábado
                </span>
              </div>
            </div>

            <div className="bg-white rounded-2xl border border-slate-200/90 shadow-xs overflow-hidden">
              <div className="overflow-x-auto">
                <table className="w-full text-left text-xs">
                  <thead className="bg-slate-50 border-b border-slate-200/90 text-slate-500 font-bold uppercase tracking-wider">
                    <tr>
                      <th className="py-3 px-4">Horário</th>
                      <th className="py-3 px-4">Quadra / Espaço</th>
                      <th className="py-3 px-4">Associado Titular</th>
                      <th className="py-3 px-4">WhatsApp</th>
                      <th className="py-3 px-4">Status da Reserva</th>
                    </tr>
                  </thead>
                  <tbody className="divide-y divide-slate-100">
                    <tr className="hover:bg-slate-50/70">
                      <td className="py-3.5 px-4 font-bold text-slate-800">08:00 - 09:00</td>
                      <td className="py-3.5 px-4 font-semibold text-[#1B3B54]">Beach Tennis • Quadra 01</td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">Schaide Nunes</td>
                      <td className="py-3.5 px-4 text-slate-500">(75) 99876-5432</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                          Confirmada
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/70">
                      <td className="py-3.5 px-4 font-bold text-slate-800">09:00 - 10:00</td>
                      <td className="py-3.5 px-4 font-semibold text-[#1B3B54]">Tênis de Saibro • Quadra 01</td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">Roberto Mendes</td>
                      <td className="py-3.5 px-4 text-slate-500">(75) 99234-5678</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                          Confirmada
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/70">
                      <td className="py-3.5 px-4 font-bold text-slate-800">16:00 - 17:00</td>
                      <td className="py-3.5 px-4 font-semibold text-[#1B3B54]">Beach Tennis • Quadra 02</td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">Ana Clara Silva</td>
                      <td className="py-3.5 px-4 text-slate-500">(75) 99123-4567</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                          Confirmada
                        </span>
                      </td>
                    </tr>
                    <tr className="hover:bg-slate-50/70">
                      <td className="py-3.5 px-4 font-bold text-slate-800">18:00 - 19:00</td>
                      <td className="py-3.5 px-4 font-semibold text-[#1B3B54]">Campo Society 01</td>
                      <td className="py-3.5 px-4 font-medium text-slate-800">Lucas Fernandes</td>
                      <td className="py-3.5 px-4 text-slate-500">(75) 99567-8901</td>
                      <td className="py-3.5 px-4">
                        <span className="px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 text-[11px] font-bold">
                          Confirmada
                        </span>
                      </td>
                    </tr>
                  </tbody>
                </table>
              </div>
            </div>
          </div>
        )}

        {/* ========================================================
            ABA 4: VISÃO GERAL & INDICADORES SIMPLES
        ======================================================== */}
        {activeTab === 'resumo' && (
          <div className="space-y-6">
            <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
              <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Total de Associados</span>
                <div className="text-3xl font-black text-[#1B3B54] mt-2">{totalCadastros}</div>
                <div className="mt-3 text-xs text-emerald-600 font-semibold flex items-center space-x-1">
                  <span>96% de adimplência este mês</span>
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Receita de Mensalidades</span>
                <div className="text-3xl font-black text-[#1B3B54] mt-2">R$ 72.300</div>
                <div className="mt-3 text-xs text-slate-500">
                  Previsão mensal com base nos planos ativos
                </div>
              </div>

              <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs">
                <span className="text-xs font-bold uppercase tracking-wider text-slate-400">Reservas de Quadras</span>
                <div className="text-3xl font-black text-[#1B3B54] mt-2">24 hoje</div>
                <div className="mt-3 text-xs text-emerald-600 font-semibold">
                  Horários nobres preenchidos
                </div>
              </div>
            </div>

            {/* Avisos do Clube */}
            <div className="bg-white p-6 rounded-2xl border border-slate-200/90 shadow-xs space-y-4">
              <h3 className="font-bold text-[#1B3B54] text-base">Avisos e Comunicação com os Sócios</h3>
              <div className="grid grid-cols-1 md:grid-cols-2 gap-4 text-xs">
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="font-bold text-slate-800 block mb-1">Manutenção da Piscina Semiolímpica</span>
                  <span className="text-slate-500">
                    Programada para toda terça-feira no turno da manhã. Os associados são avisados automaticamente pelo WhatsApp.
                  </span>
                </div>
                <div className="p-4 rounded-xl bg-slate-50 border border-slate-200/80">
                  <span className="font-bold text-slate-800 block mb-1">Torneio de Beach Tennis</span>
                  <span className="text-slate-500">
                    Inscrições abertas na secretaria ou direto pelo portal do sócio. 32 duplas confirmadas até o momento.
                  </span>
                </div>
              </div>
            </div>
          </div>
        )}
      </main>

      {/* ========================================================
          MODAL: NOVO ASSOCIADO
      ======================================================== */}
      {isNewModalOpen && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-7 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-[#1B3B54] text-amber-300 flex items-center justify-center">
                  <Plus className="w-4 h-4" />
                </div>
                <h3 className="text-base font-bold text-[#1B3B54]">Cadastrar Novo Associado</h3>
              </div>
              <button
                onClick={() => setIsNewModalOpen(false)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveNewMember} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Nome Completo *</label>
                <input
                  type="text"
                  required
                  placeholder="Ex: Carlos Eduardo de Oliveira"
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">CPF</label>
                  <input
                    type="text"
                    placeholder="000.000.000-00"
                    value={formData.cpf}
                    onChange={(e) => setFormData({ ...formData, cpf: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">WhatsApp / Telefone</label>
                  <input
                    type="text"
                    placeholder="(75) 99999-9999"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                  />
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Plano / Categoria</label>
                  <select
                    value={formData.plano}
                    onChange={(e) => setFormData({ ...formData, plano: e.target.value as any })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C] bg-white font-medium"
                  >
                    <option value="Sócio Titular">Sócio Titular</option>
                    <option value="Familiar Ouro">Familiar Ouro</option>
                    <option value="Individual Esportivo">Individual Esportivo</option>
                    <option value="Sênior">Sênior</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Dia do Vencimento</label>
                  <select
                    value={formData.vencimento}
                    onChange={(e) => setFormData({ ...formData, vencimento: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C] bg-white font-medium"
                  >
                    <option value="Dia 05">Todo dia 05</option>
                    <option value="Dia 10">Todo dia 10</option>
                    <option value="Dia 15">Todo dia 15</option>
                    <option value="Dia 20">Todo dia 20</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">E-mail</label>
                <input
                  type="email"
                  placeholder="socio@email.com"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Observações (opcional)</label>
                <input
                  type="text"
                  placeholder="Ex: Dependentes, esportes preferidos..."
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setIsNewModalOpen(false)}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#1B3B54] hover:bg-[#152e42] text-white font-bold cursor-pointer shadow-xs"
                >
                  Salvar Cadastro
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* ========================================================
          MODAL: EDITAR ASSOCIADO
      ======================================================== */}
      {editingMember && (
        <div className="fixed inset-0 z-50 bg-black/50 backdrop-blur-xs flex items-center justify-center p-4">
          <div className="bg-white rounded-3xl max-w-lg w-full p-6 sm:p-7 shadow-2xl border border-slate-200 animate-in fade-in zoom-in-95 duration-150">
            <div className="flex items-center justify-between pb-4 border-b border-slate-100">
              <div className="flex items-center space-x-2.5">
                <div className="w-8 h-8 rounded-xl bg-blue-600 text-white flex items-center justify-center">
                  <Edit2 className="w-4 h-4" />
                </div>
                <div>
                  <h3 className="text-base font-bold text-[#1B3B54]">Editar Cadastro</h3>
                  <span className="text-[11px] text-slate-400 font-mono">{editingMember.matricula}</span>
                </div>
              </div>
              <button
                onClick={() => setEditingMember(null)}
                className="p-1 rounded-lg text-slate-400 hover:text-slate-600 transition-colors cursor-pointer"
              >
                <X className="w-5 h-5" />
              </button>
            </div>

            <form onSubmit={handleSaveEditMember} className="mt-5 space-y-4 text-xs">
              <div>
                <label className="block font-bold text-slate-700 mb-1">Nome Completo</label>
                <input
                  type="text"
                  required
                  value={formData.name}
                  onChange={(e) => setFormData({ ...formData, name: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">WhatsApp</label>
                  <input
                    type="text"
                    value={formData.phone}
                    onChange={(e) => setFormData({ ...formData, phone: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                  />
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Status</label>
                  <select
                    value={formData.status}
                    onChange={(e) => setFormData({ ...formData, status: e.target.value as any })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C] bg-white font-medium"
                  >
                    <option value="Ativo">Ativo</option>
                    <option value="Pendente">Pendente</option>
                    <option value="Inativo">Inativo</option>
                  </select>
                </div>
              </div>

              <div className="grid grid-cols-2 gap-3">
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Plano</label>
                  <select
                    value={formData.plano}
                    onChange={(e) => setFormData({ ...formData, plano: e.target.value as any })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C] bg-white font-medium"
                  >
                    <option value="Sócio Titular">Sócio Titular</option>
                    <option value="Familiar Ouro">Familiar Ouro</option>
                    <option value="Individual Esportivo">Individual Esportivo</option>
                    <option value="Sênior">Sênior</option>
                  </select>
                </div>
                <div>
                  <label className="block font-bold text-slate-700 mb-1">Vencimento</label>
                  <select
                    value={formData.vencimento}
                    onChange={(e) => setFormData({ ...formData, vencimento: e.target.value })}
                    className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C] bg-white font-medium"
                  >
                    <option value="Dia 05">Todo dia 05</option>
                    <option value="Dia 10">Todo dia 10</option>
                    <option value="Dia 15">Todo dia 15</option>
                    <option value="Dia 20">Todo dia 20</option>
                  </select>
                </div>
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">E-mail</label>
                <input
                  type="email"
                  value={formData.email}
                  onChange={(e) => setFormData({ ...formData, email: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div>
                <label className="block font-bold text-slate-700 mb-1">Observações</label>
                <input
                  type="text"
                  value={formData.observacoes}
                  onChange={(e) => setFormData({ ...formData, observacoes: e.target.value })}
                  className="w-full px-3.5 py-2.5 rounded-xl border border-slate-200 focus:outline-none focus:border-[#4E7A9C]"
                />
              </div>

              <div className="flex items-center justify-end space-x-2 pt-4 border-t border-slate-100">
                <button
                  type="button"
                  onClick={() => setEditingMember(null)}
                  className="px-4 py-2 rounded-xl text-slate-600 hover:bg-slate-100 font-semibold cursor-pointer"
                >
                  Cancelar
                </button>
                <button
                  type="submit"
                  className="px-5 py-2 rounded-xl bg-[#1B3B54] hover:bg-[#152e42] text-white font-bold cursor-pointer shadow-xs"
                >
                  Salvar Alterações
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  );
};
