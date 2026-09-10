# Club Maravilha - Sistema Integrado de Gestão Esportiva

Sistema de gestão full-stack concebido para administração completa de clube esportivo (~300 associados), integrando controle de sócios, cobrança automática com Pix dinâmico e webhooks, réguas de cobrança por WhatsApp, agendamento de quadras esportivas com travas de concorrência, franquia de convidados e integração com catraca facial (rede local).

---

## 🏗️ 1. Arquitetura do Monorepo

```
Club Maravilha/
├── .env.example              # Modelo de variáveis de ambiente
├── .gitignore                # Regras de exclusão do Git
├── docker-compose.yml        # Orquestração do ambiente de desenvolvimento
├── ROADMAP.md                # Planejamento do MVP e próximas fases
├── docker/
│   └── nginx/                # Proxy reverso para produção/staging
├── backend/                  # API FastAPI (Python 3.11)
│   ├── Dockerfile
│   ├── requirements.txt
│   ├── pytest.ini
│   ├── alembic.ini
│   ├── app/
│   │   ├── core/             # Configurações Pydantic v2 e Conexões de BD
│   │   ├── models/           # Modelos SQLAlchemy 2.0 Async
│   │   ├── schemas/          # Schemas / DTOs Pydantic v2
│   │   ├── repositories/     # Isolamento de persistência (Clean Arch)
│   │   ├── services/         # Regras de negócio e validações
│   │   └── api/v1/           # Rotas REST agrupadas
│   └── tests/                # Testes unitários e de integração (TDD)
└── frontend/                 # SPA React 18 + Vite + TypeScript
    ├── Dockerfile
    ├── package.json
    ├── tailwind.config.js
    └── src/                  # Componentes, types e serviços de API
```

---

## ⚡ 2. Como Inicializar o Projeto (Docker Compose)

### Pré-requisitos:
- Docker e Docker Compose instalados.

### Passo a passo:

1. **Configurar as Variáveis de Ambiente:**
   ```bash
   cp .env.example .env
   ```

2. **Subir os Serviços com Hot-Reload:**
   ```bash
   docker compose up -d --build
   ```

3. **Verificar os Serviços:**
   - **Frontend (React + Vite):** [http://localhost:5173](http://localhost:5173)
   - **Backend API (FastAPI):** [http://localhost:8000](http://localhost:8000)
   - **Documentação Swagger:** [http://localhost:8000/docs](http://localhost:8000/docs)
   - **Banco de Dados (PostgreSQL 16):** porta `5432`

4. **Acompanhar os Logs em Tempo Real:**
   ```bash
   docker compose logs -f
   ```

5. **Parar os Serviços:**
   ```bash
   docker compose down
   ```

---

## 🗄️ 3. Modelagem do Banco de Dados

- **`associados`**: Cadastro de sócios, status (`ATIVO`, `INADIMPLENTE`, `BLOQUEADO`), `facial_id` para catraca e regras de limite de reservas.
- **`faturas`**: Mensalidades com valor base, taxa de convidados excedentes agregada, `txid` único do Pix dinâmico, QR Code e auditoria de payload de Webhook.
- **`agendamentos_quadras`**: Reservas para Tênis, Beach Tennis e Futebol com índices compostos para busca rápida e travas contra inadimplência.
- **`convidados`**: Franquia de até 8 convites mensais gratuitos (reset no dia 1º), geração de token seguro para QR Code temporário e flag de cobrança excedente (R$ 35,00).

---

## 🧪 4. Execução de Testes Automatizados (Backend)

Os testes foram construídos seguindo estritamente a filosofia TDD, utilizando SQLite assíncrono em memória para execução ultrarrápida:

```bash
cd backend
pytest
```

---

## 📍 5. Próxima Etapa: Etapa 2 (Design do Site do Club)
Com a infraestrutura conteinerizada e a modelagem relacional consolidadas no MVP, a próxima etapa é a **criação do design do portal e site do clube**, incluindo:
- Identidade visual esportiva e elegante;
- Portal do Associado com consulta de status, botão Pix Copia e Cola e agendamento de quadras;
- Painel Administrativo de Controle e Catraca.
