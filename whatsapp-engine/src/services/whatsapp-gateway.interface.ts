/**
 * Contrato de integração com o gateway de WhatsApp.
 */

export type WhatsAppConnectionState = 'open' | 'connecting' | 'close';

export interface ConnectionStatus {
  state: WhatsAppConnectionState;
  qrcode?: string | null;
}

export interface QrCodeResult {
  state: WhatsAppConnectionState;
  qrcode?: string | null;
}

export interface SendTextResult {
  id: string | null;
  jid: string;
}

export class NumeroSemWhatsAppError extends Error {
  constructor(whatsapp: string) {
    super(`O número ${whatsapp} não possui WhatsApp`);
    this.name = 'NumeroSemWhatsAppError';
  }
}

export class WhatsAppDesconectadoError extends Error {
  constructor(message: string = 'WhatsApp desconectado') {
    super(message);
    this.name = 'WhatsAppDesconectadoError';
  }
}

export interface IWhatsAppGateway {
  checkInstanceStatus(): Promise<ConnectionStatus>;
  getQrCode(): Promise<QrCodeResult>;
  sendText(whatsapp: string, text: string): Promise<SendTextResult>;
  numberExists(whatsapp: string): Promise<boolean>;
  logout(): Promise<void>;
  restart(): Promise<void>;
}
