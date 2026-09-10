# Roadmap de Desenvolvimento - Club Maravilha

Este documento consolida a evolução do sistema de gestão do **Club Maravilha** (~300 associados), delimitando o escopo do **MVP (Produto Mínimo Viável)** e as fases incrementais para guiar o avanço contínuo do projeto.

---

## 🎯 Escopo do MVP (Fase Atual)

O objetivo do MVP é fornecer uma fundação arquitetural sólida, segura e conteinerizada, permitindo cadastrar e listar associados, visualizar faturas e reservar quadras com validação básica, preparando o terreno para o design e integrações externas.

| Módulo | Escopo do MVP | Status |
|---|---|---|
| **Infra & Scaffolding** | Monorepo, Docker Compose (FastAPI, React+Vite, PostgreSQL 16), `.env`, CI/CD base | ✅ Concluído (Etapa 1) |
| **Modelagem de Dados** | Tabelas `associados`, `faturas`, `agendamentos_quadras`, `convidados` com SQLAlchemy 2.0 | ✅ Concluído (Etapa 1) |
| **Design & Portal Web** | Identidade visual premium do clube, navegação, portal do associado e painel admin | ⏳ Próxima (Etapa 2) |
| **Gestão de Associados** | CRUD básico de sócios, controle de status (ATIVO/INADIMPLENTE/BLOQUEADO) | ⏳ Planejado |
| **Financeiro Básico** | Emissão de fatura manual/simulada, exibição de status PAGO/PENDENTE | ⏳ Planejado |
| **Quadras** | Consulta de disponibilidade e criação de agendamento com trava de horário | ⏳ Planejado |

---

## 🚀 Fases Subsequentes (Pós-MVP)

### Fase 1: Design do Portal & Experiência do Usuário (Etapa 2)
- [ ] Criação da identidade visual moderna do Club Maravilha (paleta refinada, sem estilo genérico).
- [ ] Portal do Associado: visão geral da situação financeira, reservas ativas e atalhos rápidos.
- [ ] Painel Administrativo: métricas de ocupação, inadimplência e atalhos de gestão.
- [ ] Responsividade mobile-first para associados acessarem pelo smartphone.

### Fase 2: Importação de Sócios & Catraca Facial
- [ ] Endpoint de upload e script de parsing de arquivos `.xlsx` / `.csv` com validação de duplicidade por CPF.
- [ ] API local REST para sincronização da lista branca (IDs liberados/bloqueados) com a memória da catraca.
- [ ] Endpoint de upload e compressão de foto para biometria facial.

### Fase 3: Gateway Pix Dinâmico & Webhooks de Alta Performance
- [ ] Integração com Efí (Gerencianet) / Asaas para geração de Pix com `txid` exclusivo e QR Code.
- [ ] Endpoint assíncrono `/api/v1/webhooks/pix` validando assinatura criptográfica e garantindo resposta em < 2s.
- [ ] Baixa instantânea de fatura e reativação automática do status do sócio para liberação da catraca.

### Fase 4: Automação WhatsApp (Régua de Cobrança Diária)
- [ ] Worker diário (APScheduler / Celery) varrendo faturas:
  - **D-3**: Lembrete amigável de vencimento.
  - **D-0**: Envio matinal do Pix Copia e Cola.
  - **Pós-pagamento**: Confirmação instantânea de quitação e boas-vindas ao clube.
  - **D+3 / D+7**: Notificação de pendência e aviso de bloqueio na catraca.
- [ ] Adapter flexível para Evolution API e Meta Cloud API.

### Fase 5: Agendamento Avançado de Quadras & Controle de Concorrência
- [ ] Grade visual interativa por quadra (Tênis 1, Tênis 2, Beach Tennis 1, Beach Tennis 2, Futebol Society).
- [ ] Concorrência atômica com `SELECT ... FOR UPDATE` para impedir double-booking milissegundo a milissegundo.
- [ ] Trava rígida impedindo reservas de sócios inadimplentes ou que atingiram o limite simultâneo (2 reservas).

### Fase 6: Franquia de Convidados & Cobrança Agregada
- [ ] Emissão de convites com QR Code temporário (válido apenas na data agendada).
- [ ] Controle automático de franquia de 8 convites gratuitos por mês (reset no dia 1º).
- [ ] Agregação de convites excedentes (R$ 35,00 cada) na fatura Pix do mês seguinte do titular.

---

## 📌 Marcadores de Código & Continuidade
Todos os pontos de extensão futura no código estão sinalizados com tags de busca padronizadas:
- `TODO(FASE-2-CATRACA)`
- `TODO(FASE-3-PIX)`
- `TODO(FASE-4-WHATSAPP)`
- `TODO(FASE-5-QUADRAS)`
- `TODO(FASE-6-CONVIDADOS)`
