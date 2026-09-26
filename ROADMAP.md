# 🗺️ Roadmap de Desenvolvimento — Club Maravilha

Este documento consolida o estado atual do sistema de gestão do **Club Maravilha** (~480 associados) e o plano de implementação gradual para as novas funcionalidades solicitadas, seguindo os princípios de **Clean Architecture**, **Strict TDD (Red-Green-Refactor)** e **commits atômicos**.

---

## 🎯 1. Status dos Módulos Funcionais Entregues

| Módulo | Escopo Implementado | Status |
|---|---|---|
| **1. Gestão de Associados & Importador** | CRUD completo de sócios, busca textual, filtros de status; Importador assíncrono de planilhas Excel (`.xlsx`) e `.csv` com validação Módulo 11 de CPF e normalização E.164 de WhatsApp. | ✅ 100% Concluído |
| **2. Financeiro & Webhook Pix Dinâmico** | Geração de cobrança Pix EMVCo BR Code com cálculo polinomial de CRC-16-CCITT (`0x1021`); Baixa instantânea de pagamentos via webhook (< 2s), reativação automática de inadimplentes e idempotência. | ✅ 100% Concluído |
| **3. WhatsApp & Régua Diária de Cobrança** | Fila assíncrona com rate limiting e jitter humanizado anti-ban (3s a 8s); Disparos prioritários (recibo pós-pagamento imediato); Régua matinal diária às 08:00 via APScheduler (D-3, D-0, D+3, D+7). | ✅ 100% Concluído |
| **4. Agendamento de Quadras & Concorrência** | Concorrência atômica row-level (`SELECT ... FOR UPDATE` + processo assíncrono) impedindo double-booking; Trava de inadimplência; Teto de 2 reservas ativas simultâneas; Cancelamento com antecedência mínima de 2h; Grade diária de disponibilidade por slots. | ✅ 100% Concluído |
| **5. Franquia de Convidados & Faturamento** | Franquia mensal de 8 convites gratuitos por titular com reset no dia 1º; Emissão de excedentes a R$ 35,00 cada; Faturamento agregado automático de excedentes na próxima fatura Pix; QR Code temporário para o dia. | ✅ 100% Concluído |
| **6. Identificação Digital & Carteirinha** | Carteirinha digital do sócio com QR Code dinâmico, identificação rápida de dependentes, status regular e integração de acessos. | ✅ 100% Concluído |
| **7. Painel Administrativo da Diretoria** | Interface administrativa para gestão ágil de cadastros, alternância de status, simulação realista de mensagens de WhatsApp em mockup de smartphone e agenda de quadras. | ✅ 100% Concluído |

---

## 🚀 2. Novas Funcionalidades Planejadas (Implementação Gradual com TDD)

As novas demandas serão executadas de forma incremental, com testes automatizados antes de cada entrega:

### 👨‍👩‍👧‍👦 Fase 1: Membros da Família / Dependentes Gratuitos
* **Regra de Negócio:** Cada sócio titular pode cadastrar os membros da sua família (cônjuge, filhos, pais) que possuem entrada 100% gratuita no clube garantida, salvos permanentemente no cadastro daquele sócio, sem consumir a cota de 8 convites externos.
* **Tarefas Técnicas:**
  - [ ] **Modelagem & Banco:** Tabela `membros_familia` (`id`, `associado_id` [FK], `nome`, `parentesco`, `cpf`, `data_nascimento`, `ativo`, `created_at`) via migração Alembic.
  - [ ] **Backend (TDD):**
    - Schemas Pydantic (`MembroFamiliaCreate`, `MembroFamiliaUpdate`, `MembroFamiliaResponse`).
    - `MembroFamiliaRepository` e `MembroFamiliaService` com validações de unicidade e vínculo.
    - Endpoints REST: `GET/POST /api/v1/associados/{id}/familia` e `DELETE /api/v1/associados/{id}/familia/{membro_id}`.
    - Testes unitários e de integração com cobertura 100%.
  - [ ] **Frontend:**
    - Atualização da aba `UserFamiliaTab` para gerenciar dependentes permanentes separados dos convites de visitantes.
    - Visualização e cadastro de dependentes dentro do Painel Admin (modal de associado).

---

### 💳 Fase 2: Gateway de Pagamentos Mercado Pago (Pix & Webhook IPN)
* **Regra de Negócio:** A cobrança e conciliação bancária oficial será processada diretamente pela API do **Mercado Pago** (tarifa de ~1% por Pix liquidado). O sócio recebe o QR Code dinâmico gerado pelo Mercado Pago e a baixa da mensalidade é automática em até 2 segundos.
* **Tarefas Técnicas:**
  - [ ] **Configuração & Integração:**
    - Adição de credenciais no `.env` (`MERCADO_PAGO_ACCESS_TOKEN`, `MERCADO_PAGO_PUBLIC_KEY`, `MERCADO_PAGO_WEBHOOK_SECRET`).
    - Service provider `MercadoPagoPaymentProvider` para criar pagamentos Pix via API v1 com `external_reference = fatura.id`.
  - [ ] **Webhook do Mercado Pago (TDD):**
    - Endpoint `POST /api/v1/financeiro/webhook/mercadopago` com validação de assinatura HMAC (`x-signature`).
    - Processamento de notificação `payment.updated` com status `approved`: baixa imediata, reativação do sócio e disparo do recibo no WhatsApp.
    - Testes com mocks do gateway e testes de idempotência (re-envio de webhook idêntico).
  - [ ] **Frontend:**
    - Integração do modal de pagamento do sócio com o QR Code e chave Copia e Cola gerados diretamente pela API do Mercado Pago.

---

### 🎾 Fase 3: Agendamento com Prioridade de Sócios vs. Público Geral
* **Regra de Negócio:** As quadras esportivas e espaços de lazer (salão, quiosques) possuem dias em que apenas associados logados têm prioridade de agendamento. Em dias abertos ao público externo, visitantes podem agendar; nos dias prioritários, quem não estiver logado como sócio ativo é bloqueado.
* **Tarefas Técnicas:**
  - [ ] **Regras & Configuração:**
    - Parametrização no sistema dos dias com exclusividade para sócios (ex: fins de semana ou horários nobres) vs. dias livres para público externo.
  - [ ] **Backend (TDD):**
    - Verificação no `AgendamentoService`: se a data cair em dia exclusivo e o solicitante for visitante / não-sócio, retornar erro `403 Forbidden: "Agendamento reservado exclusivamente para associados ativos nesta data"`.
    - Testes unitários para sócios adimplentes, sócios inadimplentes e visitantes tentando reservar em dias permitidos e restritos.
  - [ ] **Frontend:**
    - Identificação visual no calendário de reservas ("Exclusivo para Sócios" vs "Livre").
    - Bloqueio amigável com convite para associar-se caso um visitante tente reservar em dia exclusivo.

---

### 📢 Fase 4: Gestão de Eventos no Painel Admin & Notificação no WhatsApp
* **Regra de Negócio:** A administradora do clube pode criar posts de novos eventos, shows e atividades que vão acontecer e apagar eventos passados. Ao publicar um evento, o sistema dispara aviso no WhatsApp para os sócios ativos da base.
* **Tarefas Técnicas:**
  - [ ] **Modelagem & Banco:** Tabela `eventos` (`id`, `titulo`, `descricao`, `data_evento`, `horario`, `categoria`, `banner_url`, `ativo`, `created_at`) via Alembic.
  - [ ] **Backend (TDD):**
    - Schemas Pydantic, Repositório e Serviço de Eventos.
    - Endpoints REST CRUD: `GET /api/v1/eventos`, `POST /api/v1/eventos`, `DELETE /api/v1/eventos/{id}`.
    - Endpoint de disparo: `POST /api/v1/eventos/{id}/notificar-whatsapp` que enfileira as mensagens na `WhatsAppQueueService` com controle de taxa anti-ban.
    - Testes automatizados do CRUD e do enfileiramento das mensagens de evento.
  - [ ] **Frontend:**
    - Nova seção no Painel Administrativo: "Eventos & Programação" (Criar post, upload/URL de banner, excluir post antigo, botão "Disparar para Sócios no WhatsApp").
    - Alimentação dinâmica dos carrosséis da Landing Page a partir dos eventos cadastrados no banco.

---

## 🧪 3. Qualidade & Testes Automatizados (TDD)
- **62 testes automatizados** passando com **100% de sucesso** via Docker.
- **86% de cobertura de testes** em regras de negócio, concorrência e integrações.
- Todas as novas fases seguirão estritamente o ciclo **Red -> Green -> Refactor**.
