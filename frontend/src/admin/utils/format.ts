/**
 * Utilitários de formatação pt-BR para o painel admin.
 */

export function formatBRL(valor: number | string): string {
  const num = typeof valor === 'string' ? parseFloat(valor) : valor;
  if (isNaN(num)) return 'R$ 0,00';
  return new Intl.NumberFormat('pt-BR', {
    style: 'currency',
    currency: 'BRL',
  }).format(num);
}

export function formatDate(iso: string): string {
  if (!iso) return '';
  if (/^\d{4}-\d{2}-\d{2}$/.test(iso)) {
    const [y, m, d] = iso.split('-');
    return `${d}/${m}/${y}`;
  }
  const date = new Date(iso);
  const formatter = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
  });
  return formatter.format(date);
}

export function formatDateTime(iso: string): string {
  if (!iso) return '';
  const date = new Date(iso);
  const formatter = new Intl.DateTimeFormat('pt-BR', {
    timeZone: 'America/Sao_Paulo',
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    hour: '2-digit',
    minute: '2-digit',
    hour12: false,
  });
  // O Intl pt-BR por padrão gera "dd/mm/aaaa, HH:mm" ou "dd/mm/aaaa HH:mm"
  return formatter.format(date).replace(',', '');
}

export function formatCPF(cpf: string): string {
  if (!cpf) return '';
  const limpo = cpf.replace(/\D/g, '');
  if (limpo.length !== 11) return cpf;
  return limpo.replace(/(\d{3})(\d{3})(\d{3})(\d{2})/, '$1.$2.$3-$4');
}

export function formatWhatsApp(numero: string): string {
  if (!numero) return '';
  const limpo = numero.replace(/\D/g, '');
  if (limpo.startsWith('55') && limpo.length === 13) {
    return limpo.replace(/^55(\d{2})(\d{5})(\d{4})$/, '($1) $2-$3');
  }
  if (limpo.startsWith('55') && limpo.length === 12) {
    return limpo.replace(/^55(\d{2})(\d{4})(\d{4})$/, '($1) $2-$3');
  }
  return numero;
}

export function labelSituacao(situacao: string): string {
  switch (situacao) {
    case 'EM_DIA':
      return 'Em dia';
    case 'PENDENTE':
      return 'Pendente';
    case 'ATRASADO':
      return 'Atrasado';
    default:
      return situacao;
  }
}

export function labelWhatsAppStatus(status: string): string {
  switch (status) {
    case 'CONECTADO':
      return 'Conectado';
    case 'DESCONECTADO':
      return 'Desconectado';
    case 'AGUARDANDO_QRCODE':
      return 'Aguardando QR Code';
    default:
      return 'Desconectado';
  }
}
