# Roadmap de Desenvolvimento - Club Maravilha

Este documento consolida a evolução do sistema de gestão do **Club Maravilha** (~300 associados). Todas as funcionalidades centrais de backend, regras de negócio, concorrência atômica, integrações e rotinas em segundo plano foram implementadas e validadas com rigoroso TDD.

---

## 🎯 Status dos Módulos Funcionais

| Módulo | Escopo Implementado | Status |
|---|---|---|
| **1. Gestão de Associados & Importador** | CRUD com paginação e busca textual flexível; Importador assíncrono de planilhas Excel (`.xlsx`) e `.csv` com Módulo 11 para validação de CPF, normalização E.164 de WhatsApp e script CLI direto | ✅ 100% Concluído |
| **2. Financeiro & Webhook Pix Dinâmico** | Geração de cobrança Pix EMVCo BR Code com cálculo polinomial de CRC-16-CCITT (`0x1021`); Baixa instantânea de pagamentos via webhook (< 2s), reativação automática de inadimplentes e idempotência | ✅ 100% Concluído |
| **3. WhatsApp & Régua Diária de Cobrança** | Fila assíncrona com rate limiting e jitter humanizado anti-ban (3s a 8s); Disparos prioritários (recibo pós-pagamento imediato); Régua matinal diária às 08:00 via APScheduler (D-3, D-0, D+3, D+7) | ✅ 100% Concluído |
| **4. Agendamento de Quadras & Concorrência** | Concorrência atômica row-level (`SELECT ... FOR UPDATE` + processo assíncrono) impedindo double-booking; Trava de inadimplência; Teto de 2 reservas ativas simultâneas; Cancelamento com antecedência mínima de 2h; Grade diária de disponibilidade por slots | ✅ 100% Concluído |
| **5. Franquia de Convidados & Faturamento** | Franquia mensal de 8 convites gratuitos por titular com reset no dia 1º; Emissão de excedentes a R$ 35,00 cada; Faturamento agregado automático de excedentes na próxima fatura Pix; QR Code temporário para o dia | ✅ 100% Concluído |
| **6. Catraca Facial Offline & Sincronização** | Whitelist offline periódica (`GET /api/v1/catraca/whitelist`) com checksum MD5 para detecção de alterações; Sincronização imediata pós-pagamento Pix; Auditoria de giro na catraca e check-in | ✅ 100% Concluído |
| **7. Design Visual & Frontend** | Identidade visual do portal web conduzida diretamente pelo amigo designer do projeto; API REST documentada no Swagger (`/docs`) para consumo no React/Vite | 🎨 Em andamento pelo Designer |

---

## 🧪 Qualidade & Testes Automatizados (TDD)
- **56 testes automatizados (unitários e integração)** executando via Docker com **100% de sucesso**.
- **86% de cobertura global de código**.
- Migrações versionadas com **Alembic** (`alembic upgrade head`).
- Commits atômicos no padrão Conventional Commits sincronizados em `origin main`.
