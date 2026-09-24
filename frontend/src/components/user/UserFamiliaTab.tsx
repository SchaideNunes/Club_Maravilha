import React, { useState } from 'react';
import {
  Users,
  QrCode,
  Plus,
  CheckCircle2,
  Share2,
  ShieldCheck
} from 'lucide-react';

interface Guest {
  id: string;
  name: string;
  date: string;
  status: string;
  token: string;
}

export const UserFamiliaTab: React.FC = () => {
  const [guestName, setGuestName] = useState('');
  const [guestDate, setGuestDate] = useState('2026-09-24');
  const [successMessage, setSuccessMessage] = useState<string | null>(null);

  const [guests, setGuests] = useState<Guest[]>([
    {
      id: 'g-1',
      name: 'Mariana Duarte',
      date: '12/09/2026',
      status: 'UTILIZADO',
      token: 'CM-CONV-8192'
    },
    {
      id: 'g-2',
      name: 'Lucas Silveira',
      date: '22/09/2026',
      status: 'LIBERADO',
      token: 'CM-CONV-4412'
    },
    {
      id: 'g-3',
      name: 'Beatriz Lima',
      date: '26/09/2026',
      status: 'AGENDADO',
      token: 'CM-CONV-7719'
    }
  ]);

  const dependentes = [
    { nome: 'Maria Nunes', parentesco: 'Cônjuge', matricula: '#2026-0042-D1', biometria: 'Ativa' },
    { nome: 'Lucas Nunes', parentesco: 'Filho (14 anos)', matricula: '#2026-0042-D2', biometria: 'Ativa' },
    { nome: 'Sofia Nunes', parentesco: 'Filha (9 anos)', matricula: '#2026-0042-D3', biometria: 'Ativa' },
  ];

  const quotaTotal = 8;
  const quotaUsed = guests.length;
  const quotaRemaining = quotaTotal - quotaUsed;

  const handleCreateGuest = (e: React.FormEvent) => {
    e.preventDefault();
    if (!guestName.trim()) return;

    const newGuest = {
      id: `g-${Date.now()}`,
      name: guestName.trim(),
      date: guestDate.split('-').reverse().join('/'),
      status: 'LIBERADO',
      token: `CM-CONV-${Math.floor(1000 + Math.random() * 9000)}`
    };

    setGuests([newGuest, ...guests]);
    setSuccessMessage(`Convite emitido com sucesso para ${guestName}! Link com QR Code gerado.`);
    setGuestName('');
    setTimeout(() => setSuccessMessage(null), 5000);
  };

  const handleShareWhatsApp = (guest: { name: string; token: string; date: string }) => {
    const text = encodeURIComponent(
      `Olá ${guest.name}! Você recebeu um convite para o Club Maravilha em Teofilândia-BA para o dia ${guest.date}. Apresente seu QR Code na catraca: https://clubmaravilha.com.br/convite/${guest.token}`
    );
    window.open(`https://api.whatsapp.com/send?text=${text}`, '_blank');
  };

  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Plano Familiar</span>
          <span>•</span>
          <span>Cota de Convites Mensais</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Família & Convidados
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Gerencie seus dependentes cadastrados e emita convites com liberação automática de catraca via QR Code.
        </p>
      </div>

      {successMessage && (
        <div className="p-4 rounded-2xl bg-emerald-50 border border-emerald-300 text-emerald-900 flex items-center justify-between animate-in fade-in">
          <div className="flex items-center space-x-3">
            <CheckCircle2 className="w-5 h-5 text-emerald-600 shrink-0" />
            <span className="text-sm font-bold">{successMessage}</span>
          </div>
          <span className="text-xs bg-emerald-200 text-emerald-800 font-mono px-2 py-0.5 rounded-full">
            Pronto para WhatsApp
          </span>
        </div>
      )}

      {/* Franquia de Convites: Progress Bar */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-7 space-y-4">
        <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
          <div>
            <span className="text-xs uppercase font-bold tracking-wider text-slate-400">
              Franquia Mensal de Convidados
            </span>
            <h3 className="text-xl font-black text-[#1B3B54]">
              {quotaRemaining} de {quotaTotal} convites gratuitos disponíveis este mês
            </h3>
          </div>
          <span className="text-xs font-bold px-3 py-1 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300 self-start sm:self-auto">
            Plano Ouro: 8 Gratuitos / Mês
          </span>
        </div>

        {/* Barra de Progresso */}
        <div className="w-full h-3 bg-slate-100 rounded-full overflow-hidden">
          <div
            className="h-full bg-[#4E7A9C] rounded-full transition-all duration-500"
            style={{ width: `${(quotaUsed / quotaTotal) * 100}%` }}
          ></div>
        </div>

        <p className="text-xs text-slate-500">
          Convites além da cota mensal são tarifados automaticamente a R$ 25,00 na fatura do mês subsequente.
        </p>
      </div>

      {/* Grid: Formulário de Emissão à Esquerda e Lista de Convidados à Direita */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Formulário de Emissão (5 colunas) */}
        <div className="lg:col-span-5 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-5">
          <div className="flex items-center space-x-3">
            <div className="w-10 h-10 rounded-xl bg-[#4E7A9C] text-white flex items-center justify-center shadow-sm">
              <Plus className="w-5 h-5" />
            </div>
            <div>
              <h3 className="font-bold text-[#1B3B54] text-base">
                Emitir Novo Convite
              </h3>
              <p className="text-xs text-slate-500">
                Gera QR Code para liberação direta na portaria.
              </p>
            </div>
          </div>

          <form onSubmit={handleCreateGuest} className="space-y-4">
            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">
                Nome Completo do Convidado:
              </label>
              <input
                type="text"
                required
                placeholder="Ex: João Silva da Silva"
                value={guestName}
                onChange={(e) => setGuestName(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-[#1B3B54] focus:outline-none focus:ring-2 focus:ring-[#1B3B54]"
              />
            </div>

            <div>
              <label className="text-xs font-bold uppercase tracking-wider text-slate-600 block mb-1.5">
                Data Prevista da Visita:
              </label>
              <input
                type="date"
                required
                value={guestDate}
                onChange={(e) => setGuestDate(e.target.value)}
                className="w-full bg-slate-50 border border-slate-200 rounded-xl px-4 py-2.5 text-sm text-[#1B3B54] focus:outline-none focus:ring-2 focus:ring-[#1B3B54]"
              />
            </div>

            <button
              type="submit"
              className="w-full py-3 px-4 rounded-xl bg-[#1B3B54] hover:bg-[#152e42] text-white font-bold text-sm flex items-center justify-center space-x-2 transition-all cursor-pointer shadow-md"
            >
              <QrCode className="w-4 h-4 text-amber-300" />
              <span>Gerar Convite com QR Code</span>
            </button>
          </form>
        </div>

        {/* Convidados Emitidos (7 colunas) */}
        <div className="lg:col-span-7 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-4">
          <div className="flex items-center justify-between pb-3 border-b border-slate-100">
            <h3 className="font-bold text-[#1B3B54] text-base">
              Convites Emitidos Neste Mês
            </h3>
            <span className="text-xs text-slate-500 font-medium">
              {guests.length} convite(s)
            </span>
          </div>

          <div className="space-y-3">
            {guests.map((g) => (
              <div
                key={g.id}
                className="p-4 rounded-2xl bg-slate-50 border border-slate-200/80 flex flex-col sm:flex-row sm:items-center justify-between gap-3"
              >
                <div>
                  <div className="flex items-center space-x-2">
                    <span className="font-bold text-sm text-[#1B3B54]">{g.name}</span>
                    <span
                      className={`text-[10px] font-bold px-2 py-0.5 rounded-full ${
                        g.status === 'UTILIZADO'
                          ? 'bg-slate-200 text-slate-700'
                          : 'bg-emerald-100 text-emerald-800'
                      }`}
                    >
                      {g.status}
                    </span>
                  </div>
                  <div className="text-xs text-slate-500 mt-1">
                    Data: <span className="font-semibold text-slate-700">{g.date}</span> • Token: <span className="font-mono text-slate-600">{g.token}</span>
                  </div>
                </div>

                <div className="flex items-center space-x-2 self-end sm:self-center">
                  <button
                    onClick={() => handleShareWhatsApp(g)}
                    className="inline-flex items-center space-x-1.5 px-3 py-1.5 rounded-xl bg-emerald-600 hover:bg-emerald-500 text-white text-xs font-bold transition-colors cursor-pointer shadow-xs"
                  >
                    <Share2 className="w-3.5 h-3.5" />
                    <span>WhatsApp</span>
                  </button>
                </div>
              </div>
            ))}
          </div>
        </div>
      </div>

      {/* Dependentes Cadastrados */}
      <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-7 space-y-5">
        <div className="flex items-center justify-between pb-3 border-b border-slate-100">
          <div className="flex items-center space-x-3">
            <Users className="w-5 h-5 text-[#1B3B54]" />
            <h3 className="font-bold text-[#1B3B54] text-lg">
              Dependentes do Plano Familiar (4 Vidas)
            </h3>
          </div>
          <span className="text-xs text-emerald-700 font-bold bg-emerald-50 px-3 py-1 rounded-full border border-emerald-200">
            Todas as Biometrias Ativas
          </span>
        </div>

        <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
          {dependentes.map((dep, idx) => (
            <div key={idx} className="p-4 rounded-2xl bg-slate-50 border border-slate-200 space-y-2">
              <div className="flex items-center justify-between">
                <span className="font-bold text-sm text-[#1B3B54]">{dep.nome}</span>
                <ShieldCheck className="w-4 h-4 text-emerald-600" />
              </div>
              <div className="text-xs text-slate-500">{dep.parentesco}</div>
              <div className="pt-2 border-t border-slate-200 text-[10px] text-slate-400 font-mono">
                Matrícula: {dep.matricula}
              </div>
            </div>
          ))}
        </div>
      </div>
    </div>
  );
};
