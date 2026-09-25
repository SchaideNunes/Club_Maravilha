import React, { useState, useEffect } from 'react';
import {
  ShieldCheck,
  CheckCircle2,
  QrCode,
  Users
} from 'lucide-react';

export const UserCarteirinhaTab: React.FC = () => {
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
          <div className="w-full max-w-md mx-auto rounded-3xl p-6 sm:p-7 bg-[#1B3B54] text-white shadow-lg border border-[#2B5475] relative">
            {/* Topbar da Carteirinha */}
            <div className="flex items-center justify-between pb-6 border-b border-white/15">
              <div className="flex items-center space-x-2.5">
                <div className="w-9 h-9 rounded-xl bg-amber-400 text-[#1B3B54] flex items-center justify-center font-black text-sm shadow-xs">
                  CM
                </div>
                <div>
                  <h3 className="tracking-wider font-bold text-sm uppercase text-white">
                    Clube Maravilha
                  </h3>
                  <span className="text-[10px] text-slate-300 uppercase tracking-wider block -mt-0.5">
                    Teofilândia • Bahia
                  </span>
                </div>
              </div>

              <div className="flex items-center space-x-1.5 px-3 py-1 rounded-full bg-emerald-500/20 border border-emerald-400/30 text-emerald-300 text-[11px] font-bold">
                <span className="w-2 h-2 rounded-full bg-emerald-400 animate-pulse"></span>
                <span>ADIMPLENTE</span>
              </div>
            </div>

            {/* Dados Centrais do Sócio */}
            <div className="py-6 flex items-center space-x-5">
              <div className="w-18 h-18 rounded-2xl bg-amber-400 text-[#1B3B54] flex flex-col items-center justify-center font-black shadow-sm shrink-0">
                <span className="text-2xl">SN</span>
                <span className="text-[9px] uppercase tracking-tighter text-[#1B3B54]/80">TITULAR</span>
              </div>

              <div className="min-w-0">
                <span className="text-[10px] font-extrabold uppercase tracking-widest text-amber-300 block mb-0.5">
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

            {/* Selo de Acesso */}
            <div className="mt-4 pt-3 border-t border-white/10 flex items-center justify-between text-[11px] text-slate-300">
              <span className="flex items-center space-x-1.5 text-emerald-300 font-medium">
                <ShieldCheck className="w-4 h-4 text-emerald-400" />
                <span>Credencial Válida • Portaria Principal</span>
              </span>
              <span className="text-slate-400 text-[10px]">
                Clube Maravilha • 2026
              </span>
            </div>
          </div>
        </div>

        {/* Coluna Direita: Informações de Acesso & Benefícios */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white p-6 rounded-3xl border border-slate-200 shadow-sm space-y-5">
            <div className="flex items-center space-x-3">
              <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
                <CheckCircle2 className="w-5 h-5 text-emerald-300" />
              </div>
              <div>
                <h3 className="font-bold text-[#1B3B54] text-base">
                  Acesso & Benefícios do Sócio
                </h3>
                <p className="text-xs text-slate-500">
                  Consulte os benefícios ativos da sua matrícula.
                </p>
              </div>
            </div>

            {/* Lista de Benefícios e Permissões */}
            <div className="space-y-3 pt-2 text-xs">
              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Situação Cadastral:</span>
                <span className="inline-flex items-center space-x-1 px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 font-bold">
                  <span className="w-1.5 h-1.5 rounded-full bg-emerald-500"></span>
                  <span>Ativo / Regular</span>
                </span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Dependentes Inclusos:</span>
                <span className="font-bold text-slate-800">3 familiares ativos</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Exame Médico / Piscina:</span>
                <span className="font-bold text-emerald-700">Válido até Dez/2026</span>
              </div>

              <div className="flex items-center justify-between p-3 rounded-xl bg-slate-50 border border-slate-100">
                <span className="text-slate-600 font-medium">Reservas de Quadras:</span>
                <span className="font-bold text-slate-800">Liberado (Beach Tennis e Tênis)</span>
              </div>
            </div>

            {/* Ações Práticas */}
            <div className="space-y-2 pt-2">
              <button
                onClick={() => alert('Carteirinha digital salva! Apresente o QR Code na portaria ou secretária do clube.')}
                className="w-full py-3 px-4 rounded-xl bg-[#1B3B54] hover:bg-[#152e42] text-white font-bold text-xs flex items-center justify-center space-x-2 transition-colors cursor-pointer shadow-xs"
              >
                <span>Baixar Carteirinha para o Celular</span>
              </button>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
