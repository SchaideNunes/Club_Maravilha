import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  QrCode,
  Sparkles,
  Zap,
  Users
} from 'lucide-react';

export const UserCarteirinhaTab: React.FC = () => {
  const [turnstileState, setTurnstileState] = useState<'idle' | 'scanning' | 'granted'>('idle');
  const [timestamp, setTimestamp] = useState('');

  useEffect(() => {
    const updateTime = () => {
      const now = new Date();
      setTimestamp(
        now.toLocaleTimeString('pt-BR', {
          hour: '2-digit',
          minute: '2-digit',
          second: '2-digit'
        })
      );
    };
    updateTime();
    const interval = setInterval(updateTime, 1000);
    return () => clearInterval(interval);
  }, []);

  const handleSimulateTurnstile = () => {
    setTurnstileState('scanning');
    setTimeout(() => {
      setTurnstileState('granted');
      setTimeout(() => {
        setTurnstileState('idle');
      }, 5000);
    }, 1200);
  };

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Identificação Digital</span>
          <span>•</span>
          <span>Portaria Inteligente</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Carteirinha Digital do Sócio
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Apresente esta credencial ou utilize a biometria facial para acesso imediato às catracas e dependências do clube.
        </p>
      </div>

      {/* Grid com a Carteirinha e o Painel da Catraca */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Coluna Esquerda: A Carteirinha Digital Estilizada (Frente & Verso) */}
        <div className="lg:col-span-7 space-y-6">
          <div className="w-full max-w-md mx-auto rounded-3xl p-6 sm:p-7 bg-gradient-to-br from-[#122434] via-[#1B3B54] to-[#2B5475] text-white shadow-2xl border border-amber-400/30 relative overflow-hidden">
            {/* Efeito Glow Dourado */}
            <div className="absolute -top-16 -right-16 w-44 h-44 bg-amber-400/15 rounded-full blur-2xl pointer-events-none"></div>
            <div className="absolute -bottom-16 -left-16 w-44 h-44 bg-cyan-400/10 rounded-full blur-2xl pointer-events-none"></div>

            {/* Topbar da Carteirinha */}
            <div className="flex items-center justify-between pb-6 border-b border-white/15">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-400/20 border border-amber-400/40 flex items-center justify-center text-amber-300 font-serif font-black text-sm shadow-inner">
                  CM
                </div>
                <div>
                  <h3 className="font-serif tracking-widest font-black text-sm uppercase text-amber-200">
                    Club Maravilha
                  </h3>
                  <span className="text-[10px] text-slate-300 uppercase tracking-wider block -mt-0.5">
                    Teofilândia • Bahia
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/25 border border-emerald-400/50 text-emerald-300 text-[11px] font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>ADIMPLENTE</span>
              </div>
            </div>

            {/* Dados Centrais do Sócio */}
            <div className="py-6 flex items-center space-x-5">
              <div className="w-20 h-20 rounded-2xl bg-gradient-to-br from-amber-400 to-amber-600 p-0.5 shadow-lg shrink-0">
                <div className="w-full h-full rounded-2xl bg-[#1B3B54] flex flex-col items-center justify-center text-amber-300 font-bold">
                  <span className="text-2xl font-black">SN</span>
                  <span className="text-[9px] uppercase tracking-tighter text-amber-400/80">TITULAR</span>
                </div>
              </div>

              <div className="min-w-0">
                <span className="text-[10px] font-extrabold uppercase tracking-widest text-amber-300/90 block mb-0.5">
                  SÓCIO TITULAR OURO
                </span>
                <h2 className="text-xl font-black text-white truncate tracking-tight">
                  Schaide Nunes
                </h2>
                <p className="text-xs text-slate-300 mt-0.5">
                  CPF: <span className="font-mono">123.456.789-00</span>
                </p>
                <div className="mt-2 inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-md bg-white/10 text-white/90 text-[11px] font-semibold">
                  <Users className="w-3 h-3 text-amber-300" />
                  <span>Plano Ouro Familiar • 4 Vidas</span>
                </div>
              </div>
            </div>

            {/* Rodapé da Carteirinha com QR Code Dinâmico e Validade */}
            <div className="pt-4 border-t border-white/15 flex items-center justify-between text-xs">
              <div className="space-y-1">
                <div className="text-[10px] uppercase tracking-wider text-slate-300">
                  Matrícula Oficial
                </div>
                <div className="font-mono font-bold text-amber-300 text-sm">
                  #2026-0042
                </div>
                <div className="text-[10px] text-slate-300">
                  Validade: <span className="text-white font-semibold">31/12/2026</span>
                </div>
              </div>

              {/* QR Code Dinâmico com Watermark de Segurança */}
              <div className="flex flex-col items-center">
                <div className="p-2 bg-white rounded-xl shadow-md border border-amber-300/30 flex items-center justify-center">
                  <QrCode className="w-12 h-12 text-[#1B3B54]" />
                </div>
                <span className="text-[9px] font-mono text-amber-300/90 mt-1 font-semibold">
                  {timestamp || 'Sincronizado'}
                </span>
              </div>
            </div>

            {/* Selo de Biometria Facial Integrada */}
            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-300">
              <span className="flex items-center space-x-1.5 text-emerald-300 font-medium">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Biometria Facial Sincronizada</span>
              </span>
              <span className="text-slate-400 text-[10px]">
                Portaria 01 • Catraca Automática
              </span>
            </div>
          </div>

          {/* Dica para Apresentação */}
          <div className="p-4 rounded-2xl bg-amber-50 border border-amber-200 text-amber-900 text-xs flex items-start space-x-3">
            <Sparkles className="w-5 h-5 text-amber-600 shrink-0 mt-0.5" />
            <div>
              <span className="font-bold block mb-0.5">Destaque para a Reunião com a Diretoria:</span>
              O associado não precisa de cartão de plástico. A catraca reconhece o rosto do sócio em menos de 0.5 segundo ou lê o QR Code dinâmico anti-fraude diretamente pelo celular.
            </div>
          </div>
        </div>

        {/* Coluna Direita: Simulador Interativo da Catraca */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-5">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
                <Zap className="w-5 h-5" />
              </div>
              <div>
                <h3 className="font-bold text-[#1B3B54] text-base">
                  Simulador de Catraca Facial
                </h3>
                <p className="text-xs text-slate-500">
                  Teste em tempo real a validação da portaria social.
                </p>
              </div>
            </div>

            {/* Tela Virtual da Catraca */}
            <div className={`p-6 rounded-2xl transition-all duration-300 border ${
              turnstileState === 'granted'
                ? 'bg-emerald-950 text-emerald-100 border-emerald-500 shadow-lg shadow-emerald-500/10'
                : turnstileState === 'scanning'
                ? 'bg-amber-950 text-amber-100 border-amber-500'
                : 'bg-slate-900 text-slate-200 border-slate-800'
            }`}>
              <div className="text-center space-y-3">
                <div className="inline-flex items-center space-x-2 px-3 py-1 rounded-full bg-white/10 text-xs font-mono uppercase tracking-wider">
                  <span className={`w-2 h-2 rounded-full ${
                    turnstileState === 'granted' ? 'bg-emerald-400 animate-ping' : 'bg-slate-400'
                  }`}></span>
                  <span>Catraca 01 • Portaria Principal</span>
                </div>

                {turnstileState === 'idle' && (
                  <div className="py-4">
                    <p className="text-slate-400 text-xs">Sensor aguardando aproximação...</p>
                    <p className="text-lg font-bold text-white mt-1">APROXIME O ROSTO OU QR CODE</p>
                  </div>
                )}

                {turnstileState === 'scanning' && (
                  <div className="py-4">
                    <div className="w-8 h-8 border-3 border-amber-400 border-t-transparent rounded-full animate-spin mx-auto mb-2"></div>
                    <p className="text-amber-300 font-bold text-sm">Consultando Biometria & Mensalidade...</p>
                    <p className="text-[11px] text-amber-400/80">Validando com base do PostgreSQL</p>
                  </div>
                )}

                {turnstileState === 'granted' && (
                  <div className="py-4 space-y-2 animate-in fade-in zoom-in-95 duration-200">
                    <div className="w-12 h-12 rounded-full bg-emerald-500/20 border border-emerald-400 flex items-center justify-center mx-auto text-emerald-400">
                      <CheckCircle2 className="w-7 h-7" />
                    </div>
                    <h4 className="text-xl font-black text-emerald-300">
                      ACESSO LIBERADO!
                    </h4>
                    <p className="text-xs text-emerald-200 font-medium">
                      Bem-vindo(a), Schaide Nunes!
                    </p>
                    <div className="pt-2 text-[10px] font-mono text-emerald-400/80 border-t border-emerald-500/20">
                      Catraca destravada • Latência: 0.28s • Log #TUR-84219
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* Botão de Ação */}
            <button
              onClick={handleSimulateTurnstile}
              disabled={turnstileState !== 'idle'}
              className={`w-full py-3.5 px-4 rounded-xl font-bold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-md ${
                turnstileState !== 'idle'
                  ? 'bg-slate-200 text-slate-500 cursor-not-allowed'
                  : 'bg-[#1B3B54] hover:bg-[#152e42] text-white hover:shadow-lg'
              }`}
            >
              <Zap className="w-4 h-4 text-amber-400" />
              <span>
                {turnstileState === 'scanning'
                  ? 'Verificando...'
                  : turnstileState === 'granted'
                  ? 'Catraca Liberada!'
                  : '⚡ Simular Leitura na Catraca (Portaria)'}
              </span>
            </button>

            {/* Informações da Política */}
            <div className="space-y-2 pt-2 text-xs text-slate-500">
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span>Situação Cadastral:</span>
                <span className="font-semibold text-emerald-700">Ativo / Regular</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span>Limite de Reservas Ativas:</span>
                <span className="font-semibold text-slate-800">2 reservas simultâneas</span>
              </div>
              <div className="flex items-center justify-between py-1 border-b border-slate-100">
                <span>Exame Médico / Piscina:</span>
                <span className="font-semibold text-emerald-700">Válido até Dez/2026</span>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
