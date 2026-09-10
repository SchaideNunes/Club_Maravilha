import React, { useEffect, useState } from 'react';
import { 
  Users, 
  QrCode, 
  Calendar, 
  CreditCard, 
  MessageSquare, 
  ShieldCheck, 
  CheckCircle2, 
  Clock, 
  Server,
  ArrowRight
} from 'lucide-react';
import { api } from './services/api';

interface HealthStatus {
  status: string;
  database: string;
  service: string;
  version: string;
}

export default function App() {
  const [health, setHealth] = useState<HealthStatus | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    async function checkBackendHealth() {
      try {
        const response = await api.get<HealthStatus>('/health');
        setHealth(response.data);
        setError(null);
      } catch (err: any) {
        setError(err.message || 'Falha ao conectar com o backend');
      } finally {
        setLoading(false);
      }
    }
    checkBackendHealth();
  }, []);

  const modules = [
    {
      title: '1. Gestão de Associados',
      desc: 'CRUD de ~300 sócios, controle de status (Ativo/Inadimplente/Bloqueado) e importação via planilha.',
      icon: Users,
      badge: 'MVP Pronto',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      action: 'Ver Sócios'
    },
    {
      title: '2. Financeiro & Pix Dinâmico',
      desc: 'Geração de Pix com txid único, webhook com baixa em 2s e desbloqueio instantâneo.',
      icon: CreditCard,
      badge: 'Modelagem Pronta',
      badgeColor: 'bg-blue-500/10 text-blue-400 border-blue-500/20',
      action: 'Ver Faturas'
    },
    {
      title: '3. Automação de WhatsApp',
      desc: 'Régua diária: lembrete D-3, Pix matinal D-0, recibo pós-baixa e alertas D+3 e D+7.',
      icon: MessageSquare,
      badge: 'Fase 4',
      badgeColor: 'bg-amber-500/10 text-amber-400 border-amber-500/20',
      action: 'Configurar'
    },
    {
      title: '4. Agendamento de Quadras',
      desc: 'Grade de Tênis, Beach Tennis e Futebol com trava contra inadimplência e concorrência atômica.',
      icon: Calendar,
      badge: 'MVP Pronto',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      action: 'Ver Grade'
    },
    {
      title: '5. Controle de Convidados',
      desc: 'Franquia de 8 convites mensais gratuitos com QR Code temporário e faturamento de excedentes.',
      icon: QrCode,
      badge: 'MVP Pronto',
      badgeColor: 'bg-emerald-500/10 text-emerald-400 border-emerald-500/20',
      action: 'Emitir Convite'
    },
    {
      title: '6. Catraca Facial (Rede Local)',
      desc: 'Sincronização periódica da lista branca offline com biometria facial e QR Code de visitantes.',
      icon: ShieldCheck,
      badge: 'Endpoint Pronto',
      badgeColor: 'bg-purple-500/10 text-purple-400 border-purple-500/20',
      action: 'Ver Whitelist'
    },
  ];

  return (
    <div className="min-h-screen bg-slate-950 text-slate-100 flex flex-col">
      {/* Header */}
      <header className="border-b border-slate-800/80 bg-slate-900/60 backdrop-blur-md sticky top-0 z-50">
        <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between">
          <div className="flex items-center space-x-3">
            <div className="h-10 w-10 rounded-xl bg-gradient-to-tr from-brand-600 to-emerald-400 flex items-center justify-center font-bold text-white shadow-lg shadow-emerald-900/20 text-lg">
              CM
            </div>
            <div>
              <span className="text-lg font-bold tracking-tight text-white">Club Maravilha</span>
              <span className="ml-2 text-xs font-medium px-2 py-0.5 rounded-full bg-brand-500/10 text-brand-400 border border-brand-500/20">
                MVP v0.1
              </span>
            </div>
          </div>

          <div className="flex items-center space-x-4">
            {/* Status do Backend */}
            <div className="flex items-center space-x-2 text-xs px-3 py-1.5 rounded-full bg-slate-800/80 border border-slate-700/60">
              <Server className="w-3.5 h-3.5 text-slate-400" />
              {loading ? (
                <span className="text-slate-400 flex items-center">
                  <Clock className="w-3 h-3 animate-spin mr-1" /> Conectando...
                </span>
              ) : health ? (
                <span className="text-emerald-400 flex items-center">
                  <span className="w-2 h-2 rounded-full bg-emerald-400 mr-1.5 animate-pulse"></span>
                  API Online ({health.service})
                </span>
              ) : (
                <span className="text-rose-400 flex items-center">
                  <span className="w-2 h-2 rounded-full bg-rose-400 mr-1.5"></span>
                  {error || 'API Offline'}
                </span>
              )}
            </div>

            <a
              href="http://localhost:8000/docs"
              target="_blank"
              rel="noreferrer"
              className="text-xs font-semibold px-3 py-1.5 rounded-lg bg-slate-800 hover:bg-slate-700 text-slate-200 transition-colors"
            >
              Swagger Docs ↗
            </a>
          </div>
        </div>
      </header>

      {/* Main Content */}
      <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-10 flex-1 flex flex-col justify-center">
        {/* Banner de Boas-Vindas e Transição */}
        <div className="mb-10 text-center max-w-3xl mx-auto">
          <div className="inline-flex items-center space-x-2 px-3.5 py-1 rounded-full bg-brand-500/10 border border-brand-500/20 text-brand-400 text-xs font-medium mb-4">
            <CheckCircle2 className="w-3.5 h-3.5" />
            <span>Etapa 1 Concluída: Scaffolding, Docker & Modelos de Banco de Dados</span>
          </div>
          <h1 className="text-4xl sm:text-5xl font-extrabold tracking-tight text-white mb-4">
            Sistema Integrado de Gestão do <span className="text-transparent bg-clip-text bg-gradient-to-r from-brand-400 to-emerald-300">Club Maravilha</span>
          </h1>
          <p className="text-base text-slate-400 leading-relaxed">
            Fundação arquitetural do monorepo operacional com FastAPI, PostgreSQL 16, React e Docker Compose. 
            Pronto para o desenvolvimento do design do portal na <strong className="text-slate-200">Etapa 2</strong>.
          </p>
        </div>

        {/* Grade de Módulos */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6 mb-12">
          {modules.map((mod, idx) => {
            const IconComponent = mod.icon;
            return (
              <div 
                key={idx}
                className="bg-slate-900/60 border border-slate-800/80 hover:border-slate-700/80 rounded-2xl p-6 transition-all duration-200 flex flex-col justify-between group shadow-sm hover:shadow-md"
              >
                <div>
                  <div className="flex items-center justify-between mb-4">
                    <div className="h-10 w-10 rounded-xl bg-slate-800 flex items-center justify-center text-brand-400 group-hover:scale-105 transition-transform duration-200">
                      <IconComponent className="w-5 h-5" />
                    </div>
                    <span className={`text-[11px] font-semibold px-2.5 py-0.5 rounded-full border ${mod.badgeColor}`}>
                      {mod.badge}
                    </span>
                  </div>
                  <h3 className="text-base font-bold text-white mb-2">{mod.title}</h3>
                  <p className="text-sm text-slate-400 leading-relaxed mb-6">{mod.desc}</p>
                </div>

                <div className="pt-4 border-t border-slate-800/60 flex items-center justify-between text-xs font-medium text-slate-400">
                  <span>Módulo {idx + 1} de 6</span>
                  <span className="text-brand-400 group-hover:translate-x-1 transition-transform duration-200 flex items-center space-x-1">
                    <span>{mod.action}</span>
                    <ArrowRight className="w-3.5 h-3.5" />
                  </span>
                </div>
              </div>
            );
          })}
        </div>

        {/* Card Informativo para Etapa 2 */}
        <div className="rounded-2xl bg-gradient-to-r from-slate-900 via-slate-900 to-slate-800 border border-brand-500/20 p-6 sm:p-8 flex flex-col sm:flex-row items-center justify-between gap-6">
          <div>
            <span className="text-xs uppercase tracking-wider text-brand-400 font-bold">Próximo Passo</span>
            <h2 className="text-xl font-bold text-white mt-1">Etapa 2: Design do Portal do Clube</h2>
            <p className="text-sm text-slate-400 mt-1 max-w-xl">
              Criação da interface moderna para os sócios consultarem situação financeira, copiarem código Pix, reservarem quadras e emitirem convites com QR Code.
            </p>
          </div>
          <button 
            type="button"
            className="w-full sm:w-auto px-6 py-3 rounded-xl bg-brand-600 hover:bg-brand-500 font-semibold text-white text-sm shadow-lg shadow-brand-600/20 transition-all duration-200 whitespace-nowrap"
          >
            Iniciar Design (Etapa 2) →
          </button>
        </div>
      </main>

      {/* Footer */}
      <footer className="border-t border-slate-800/80 py-6 text-center text-xs text-slate-400">
        <p>Club Maravilha © 2026 • Sistema de Gestão Esportiva • FastAPI + React + PostgreSQL + Docker</p>
      </footer>
    </div>
  );
}
