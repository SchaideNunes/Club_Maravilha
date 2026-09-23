import {
  User,
  Phone,
  Mail,
  MapPin,
  ShieldCheck,
  CheckCircle2
} from 'lucide-react';

export const UserContaTab: React.FC = () => {
  return (
    <div className="space-y-8">
      {/* Cabeçalho */}
      <div>
        <div className="flex items-center space-x-2 text-xs font-bold uppercase tracking-wider text-[#4E7A9C]">
          <span>Dados do Associado</span>
          <span>•</span>
          <span>Gestão Cadastral</span>
        </div>
        <h1 className="text-2xl sm:text-3xl font-black text-[#1B3B54] tracking-tight mt-1">
          Minha Conta & Perfil
        </h1>
        <p className="text-slate-500 text-sm mt-1">
          Consulte suas informações pessoais, status da biometria facial e preferências de notificação via WhatsApp.
        </p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
        {/* Dados Pessoais (7 colunas) */}
        <div className="lg:col-span-7 bg-white rounded-3xl border border-slate-200 shadow-sm p-6 sm:p-7 space-y-6">
          <div className="flex items-center space-x-4 pb-6 border-b border-slate-100">
            <div className="w-16 h-16 rounded-2xl bg-gradient-to-br from-[#1B3B54] to-[#4E7A9C] text-amber-300 font-black text-2xl flex items-center justify-center shadow-md">
              SN
            </div>
            <div>
              <div className="flex items-center space-x-2">
                <h3 className="text-xl font-black text-[#1B3B54]">Schaide Nunes</h3>
                <span className="text-[10px] font-bold px-2.5 py-0.5 rounded-full bg-emerald-100 text-emerald-800 border border-emerald-300">
                  ATIVO
                </span>
              </div>
              <p className="text-xs text-slate-500 mt-0.5">
                Matrícula Oficial: <span className="font-mono font-bold text-slate-700">#2026-0042</span> • Sócio desde Jan/2024
              </p>
            </div>
          </div>

          <div className="space-y-4 text-sm">
            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 text-xs flex items-center space-x-2">
                <User className="w-4 h-4 text-slate-400" />
                <span>CPF do Titular:</span>
              </span>
              <span className="font-mono font-bold text-[#1B3B54]">123.456.789-00</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 text-xs flex items-center space-x-2">
                <Phone className="w-4 h-4 text-slate-400" />
                <span>WhatsApp Oficial:</span>
              </span>
              <div className="flex items-center space-x-1.5">
                <span className="font-mono font-bold text-[#1B3B54]">(75) 98328-5614</span>
                <span className="text-[10px] font-bold px-1.5 py-0.5 rounded-sm bg-emerald-100 text-emerald-800">
                  Verificado
                </span>
              </div>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 text-xs flex items-center space-x-2">
                <Mail className="w-4 h-4 text-slate-400" />
                <span>E-mail:</span>
              </span>
              <span className="font-medium text-[#1B3B54]">schaide@clubmaravilha.com.br</span>
            </div>

            <div className="flex items-center justify-between py-2 border-b border-slate-100">
              <span className="text-slate-500 text-xs flex items-center space-x-2">
                <MapPin className="w-4 h-4 text-slate-400" />
                <span>Cidade:</span>
              </span>
              <span className="font-medium text-[#1B3B54]">Teofilândia - BA</span>
            </div>
          </div>
        </div>

        {/* Status Tecnológico & Notificações (5 colunas) */}
        <div className="lg:col-span-5 space-y-6">
          <div className="bg-white rounded-3xl border border-slate-200 shadow-sm p-6 space-y-4">
            <div className="flex items-center space-x-3 pb-3 border-b border-slate-100">
              <ShieldCheck className="w-5 h-5 text-emerald-600" />
              <h3 className="font-bold text-[#1B3B54] text-base">
                Segurança & Portaria Inteligente
              </h3>
            </div>

            <div className="space-y-3 text-xs">
              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#1B3B54]">Reconhecimento Facial:</span>
                  <span className="text-emerald-700 font-bold flex items-center space-x-1">
                    <CheckCircle2 className="w-3.5 h-3.5" />
                    <span>Sincronizado</span>
                  </span>
                </div>
                <p className="text-slate-500 text-[11px]">
                  ID Facial cadastrado nos terminais biométricos da portaria principal e piscina.
                </p>
              </div>

              <div className="p-3.5 rounded-2xl bg-slate-50 border border-slate-200/80 space-y-1">
                <div className="flex items-center justify-between">
                  <span className="font-bold text-[#1B3B54]">Notificações WhatsApp:</span>
                  <span className="text-emerald-700 font-bold">Ativas</span>
                </div>
                <p className="text-slate-500 text-[11px]">
                  Régua de lembrete matinal (D-3, D-0) e recibo automático após pagamento via Pix.
                </p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  );
};
