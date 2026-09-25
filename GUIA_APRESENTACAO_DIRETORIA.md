# 📋 Roteiro & Guia Oficial de Apresentação — Club Maravilha

Este documento foi preparado para você conduzir a apresentação do sistema no computador da empresa. Ele contém o passo a passo da demonstração, argumentos de valor para a diretoria, o que já está funcionando, como o sistema vai evoluir e os próximos passos pós-fechamento.

---

## ⚡ 1. Preparação Rápida no Computador da Empresa

Ao abrir o computador da empresa, execute no terminal:

```bash
# 1. Puxe as atualizações mais recentes do GitHub
git pull origin main

# 2. Suba o ambiente com o Docker Compose
docker compose up -d

# 3. Acesse no navegador:
# Landing Page:  http://localhost:5173
# Área do Sócio: http://localhost:5173/#/usuario
# Painel Admin:  http://localhost:5173/#/admin
```

> **Dica de Navegação:** Você não precisa digitar os links na frente da diretoria. No cabeçalho da área do associado há um botão dourado **"Painel da Diretoria"**, e no menu hambúrguer de qualquer página há acesso direto a todas as seções.

---

## 🎙️ 2. Roteiro de Apresentação (Minuto a Minuto)
*Duração sugerida: 15 a 20 minutos.*

### ⏱️ Parte 1: Introdução & Diagnóstico (2 minutos)
* **Objetivo:** Alinhar o problema atual do clube antes de mostrar as telas.
* **O que falar:**
  > *"Hoje, o clube cresceu e gerenciar mais de 300 a 500 sócios por anotações, cadernos ou planilhas soltas gera três grandes problemas: sobrecarga na secretaria, atrasos nas mensalidades por falta de lembrete prático, e atrito dos sócios para agendar quadras esportivas.*
  > *Desenvolvemos uma solução sob medida, moderna e direta ao ponto: um portal para o associado ter autonomia total e um painel administrativo para a diretoria ter controle total em tempo real."*

---

### ⏱️ Parte 2: A Experiência do Associado (6 minutos)
* **Onde clicar:** [http://localhost:5173/#/usuario](http://localhost:5173/#/usuario)

1. **Carteirinha Digital do Sócio (`Aba: Carteirinha`)**:
   * **O que mostrar:** A credencial digital com nome, foto/iniciais, CPF, matrícula oficial, validade e QR Code.
   * **O que falar:**
     > *"O sócio não precisa mais de carteirinha de plástico que quebra ou se perde. Ele tem a credencial oficial no celular, com situação cadastral em dia, dependentes vinculados e liberação rápida na portaria."*

2. **Financeiro & Pagamento em 1 Clique (`Aba: Financeiro`)**:
   * **O que mostrar:** A fatura do mês com valor e botão de pagamento.
   * **Ação ao vivo:** Clique em **"Pagar Mensalidade com Pix"** para abrir o modal com o Pix Copia e Cola.
   * **O que falar:**
     > *"O maior motivo de atraso de mensalidade é a burocracia do boleto ou a fila na secretaria. Aqui o sócio clica em 'Pagar', copia o Pix e a confirmação é imediata no sistema. Sem atrito."*

3. **Reserva de Quadras Esportivas (`Aba: Reservas`)**:
   * **O que mostrar:** Visualização das quadras (Beach Tennis, Tênis de Saibro, Campo Society).
   * **O que falar:**
     > *"Acabou o grupo de WhatsApp da secretaria com disputa de horário. O sócio visualiza os horários disponíveis e garante a reserva dele com regras claras (limite por matrícula e antecedência)."*

---

### ⏱️ Parte 3: O Painel Administrativo da Diretoria (8 minutos) — *O Ponto Alto*
* **Onde clicar:** [http://localhost:5173/#/admin](http://localhost:5173/#/admin) (ou clique em **"Painel da Diretoria"** no topo).

1. **Administração de Cadastros (`Aba: Administração de Cadastros`)**:
   * **O que mostrar:**
     * Indicadores superiores: Total de Cadastros, Ativos / Em Dia, Pagamentos Pendentes e Inativos.
     * Tabela limpa com matrícula, nome, CPF, WhatsApp, plano e dia de vencimento.
     * Filtros rápidos por status e barra de busca instantânea.
   * **Ação ao vivo (Efeito Prático):**
     * Clique em **"+ Novo Associado"**.
     * Preencha um cadastro fictício rápido (ex: *Carlos Eduardo*, *Plano Familiar Ouro*, *Dia 10*).
     * Clique em **"Salvar Cadastro"** e veja o sócio entrar imediatamente na tabela com matrícula gerada e toast de sucesso.
     * Clique no ícone de lápis de qualquer associado para mostrar que é possível alterar telefone, e-mail ou observações em segundos sem quebrar nada.
   * **O que falar:**
     > *"A secretaria não precisa de treinamentos complexos. Cadastrar um associado leva 15 segundos. Se alguém mudou de número ou plano, basta editar na hora."*

2. **Estilo da Mensagem que Chega no WhatsApp (`Aba: Estilo da Mensagem no WhatsApp`)**:
   * **O que mostrar:** O mockup em formato de smartphone com a interface oficial do WhatsApp (cabeçalho verde escuro `#075E54`, selo de verificado, status de conta comercial e balão com tique duplo azul).
   * **Ação ao vivo (Interatividade Máxima):**
     * Alterne entre os 4 botões de modelo:
       1. 💳 **Lembrete de Mensalidade & Pix**: mostra o texto com chave Pix Copia e Cola.
       2. 👋 **Boas-Vindas & Acesso**: mensagem de boas-vindas com matrícula para novos cadastros.
       3. 🎾 **Reserva de Quadra**: confirmação de agendamento esportivo.
       4. 📢 **Comunicado de Evento**: aviso sobre shows e programações do clube.
     * Selecione o associado que você acabou de cadastrar no menu suspenso: veja o nome e plano dele entrarem automaticamente no texto do balão do WhatsApp!
     * Altere uma palavra no campo de texto e mostre que o balão do WhatsApp se atualiza na hora na tela.
     * Clique em **"Simular Envio ao Sócio"**.
   * **O que falar:**
     > *"O grande diferencial: o sócio não é obrigado a baixar nenhum aplicativo pesado se não quiser. Ele recebe avisos amigáveis, lembretes de mensalidade com Pix e confirmações de quadra diretamente no WhatsApp oficial do clube, com comunicação padronizada e sem desgaste da secretária."*

3. **Agenda das Quadras (`Aba: Reservas das Quadras`)**:
   * **O que mostrar:** Grade do dia informando horário, quadra e nome do sócio titular.
   * **O que falar:**
     > *"A diretoria e a equipe da quadra têm a visão clara de quem está jogando em cada horário, evitando conflitos ou uso indevido."*

---

## 🔮 3. Como o Sistema vai Evoluir Mais para Frente (Roadmap Futuro)

Apresente essa visão para demonstrar planejamento e escalabilidade:

1. **Gateway de Pagamento Bancário Integrado (Asaas / Mercado Pago / Banco Inter)**:
   * Emissão automática de Pix e boletos bancários registrados diretamente na conta corrente jurídica do clube.
   * Conciliação bancária 100% automatizada (caiu o Pix na conta, o sistema já marca como pago e dispara recibo no WhatsApp).
2. **Totem ou Tablet de Autoatendimento na Portaria**:
   * Um tablet simples na recepção/portaria para leitura rápida do QR Code da carteirinha do sócio ou check-in de convidados.
3. **PWA (Aplicativo Instalável)**:
   * O associado poderá adicionar o ícone do Clube Maravilha diretamente na tela inicial do iPhone ou Android sem passar pela burocracia da App Store.
4. **Relatórios Financeiros & DRE para o Conselho Fiscal**:
   * Relatório mensal de inadimplência, novos associados e faturamento consolidado exportável em PDF e Excel para as assembleias.

---

## 🚀 4. Como Seguir a Partir do Fechamento do Projeto (Plano de Implantação)

Ao final da reunião, mostre o cronograma prático de implantação para transmitir total segurança:

| Etapa | Duração | Atividades Principais |
|---|---|---|
| **Fase 1: Migração de Dados** | Semana 1 | Coleta da planilha atual do clube, higienização dos dados e importação oficial de todos os sócios no banco de dados. |
| **Fase 2: Conexão Oficial do WhatsApp** | Semana 2 | Configuração do número de WhatsApp Business da secretaria e validação do fluxo de envio com as mensagens padronizadas. |
| **Fase 3: Treinamento da Equipe** | Semana 3 | Treinamento rápido (1 a 2 horas) com a secretária e recepcionista para uso do painel de cadastros e reservas. |
| **Fase 4: Lançamento aos Sócios** | Semana 4 | Disparo inaugural de WhatsApp para toda a base de associados apresentando o novo portal e liberando as carteirinhas digitais. |
| **Fase 5: Suporte & Evolução** | Contínuo | Acompanhamento do primeiro mês de cobrança, ajustes operacionais e suporte técnico. |

---

## 💡 Dicas de Ouro para a Apresentação
* **Foque na Simplicidade:** Não use termos técnicos complexos como "PostgreSQL", "Docker" ou "APIs". Use termos do negócio: *"gestão de associados"*, *"baixa automática sem filas"*, *"notificação no celular"* e *"controle de quadras"*.
* **Deixe a Diretoria Interagir:** Peça para alguém da mesa falar um nome e cadastre ao vivo no painel de associados. Isso quebra qualquer dúvida sobre a funcionalidade do sistema.
* **Segurança de Execução:** Todas as funções da tela possuem retorno imediato e visual limpo na paleta de cores aprovada (`#1B3B54` e `#6899BA`).
