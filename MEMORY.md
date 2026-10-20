# MEMORY.md — Memória de Contexto & Estado Operacional do Club Maravilha

**Projeto:** Club Maravilha — Sistema Integrado de Gestão Esportiva, Automação de WhatsApp e Painel Administrativo  
**Repositório:** `D:\Trabalho\Club Maravilha`  
**Última Atualização:** 19 de Outubro de 2026  
**Status Atual:** MVP Concluído, Containers Ativos e Conexão de WhatsApp Validada em Produção Local  

---

## 1. 📌 Resumo do Estado Atual

O sistema encontra-se 100% operacional no ambiente de desenvolvimento local via Docker Compose.
- **Suíte de Testes Automatizados:** 1.159 testes passando sem falhas (870 backend, 176 frontend, 113 motor WhatsApp).
- **Conectividade WhatsApp (Baileys):** QR Code escaneado e pareado com sucesso pelo usuário. Disparo e recebimento de mensagem real via WhatsApp testados e homologados com sucesso.
- **Banco de Dados Relacional:** PostgreSQL 16 com schema completo e migrações Alembic sincronizadas na versão `head` (`e5a1b2c3d4e5`).
- **Autenticação:** Painel administrativo com JWT, seed automático de usuário administrador e mitigação de timing attacks.

---

## 2. 🌐 Arquitetura de Portas & Acessos Locais

| Serviço | URL / Host | Porta Host | Porta Container | Descrição & Credenciais |
| :--- | :--- | :--- | :--- | :--- |
| **Frontend SPA** | `http://localhost:5173` | `5173` | `5173` | React 18 + Vite + Tailwind CSS |
| **Backend API** | `http://localhost:8000` | `8000` | `8000` | FastAPI (Docs: `/docs`, OpenAPI: `/openapi.json`) |
| **Motor WhatsApp** | `http://localhost:3001` | `3001` | `3001` | Node.js/TypeScript com Baileys (`x-api-key: club_maravilha_secret_key_123`) |
| **Banco de Dados** | `localhost:5433` | `5433` | `5432` | PostgreSQL 16 (User: `club_admin`, DB: `club_maravilha`) |

> **Nota Crítica sobre a Porta do PostgreSQL:**  
> O host Windows possui um serviço nativo de PostgreSQL rodando na porta `5432`. Para evitar conflitos de bind (`listen tcp4 127.0.0.1:5432: bind`), a porta mapeada no host para o container Docker foi configurada para **`5433`** no arquivo `.env` (`POSTGRES_PORT=5433`). Na rede interna do Docker (`club_network`), os containers comunicam-se na porta padrão `5432`.

### Credenciais de Acesso Inicial ao Painel Admin:
- **URL:** [http://localhost:5173](http://localhost:5173)
- **E-mail:** `admin@clubmaravilha.com.br`
- **Senha:** `admin_secret_password_change_in_prod` (ou conforme alterada no [`.env`](file:///D:/Trabalho/Club%20Maravilha/.env))

---

## 3. 🛠️ Correções e Ajustes Técnicos Aplicados

Durante a homologação da subida dos containers em 19/10/2026, os seguintes ajustes foram realizados e devem ser preservados:

1. **Dependência `greenlet` no Backend ([`backend/requirements.txt`](file:///D:/Trabalho/Club%20Maravilha/backend/requirements.txt)):**
   - Adicionadas as entradas `sqlalchemy[asyncio]>=2.0.28` e `greenlet>=3.0.3`. O SQLAlchemy 2.0 Async exige o pacote C/Python `greenlet` para executar I/O assíncrono no Linux Alpine do container Docker.
2. **Correção de Tipagem Dinâmica ([`backend/app/services/convidado_service.py`](file:///D:/Trabalho/Club%20Maravilha/backend/app/services/convidado_service.py)):**
   - Inserido `from __future__ import annotations` e importada explicitamente a classe `Associado` de `app.models.associado`, evitando `NameError: name 'Associado' is not defined` durante o carregamento de módulos no Python 3.11.
3. **Idempotência na Migração de Administradores ([`backend/alembic/versions/e5a1b2c3d4e5_create_usuarios_admin.py`](file:///D:/Trabalho/Club%20Maravilha/backend/alembic/versions/e5a1b2c3d4e5_create_usuarios_admin.py)):**
   - Adicionada verificação via `sa.inspect(op.get_bind()).get_table_names()` para garantir que a migração não tente recriar a tabela `usuarios_admin` caso ela já tenha sido criada pelo `Base.metadata.create_all` no startup da API.
4. **Limpeza de Registro Duplicado em `faturas`:**
   - Excluído registro redundante de teste de setembro/2026 (`b94f6248-cc04-49e8-81a2-86f1bfa8312a`), permitindo a aplicação sem erro da restrição única `uq_faturas_associado_referencia_mes` da migração `d485e921b712`.
5. **Atualização do Volume Anônimo de `node_modules` do Frontend:**
   - Executado `npm install` no container para sincronizar pacotes novos (como `react-router-dom`) com o volume anônimo persistido no Docker.
6. **Variáveis de Ambiente ([`.env`](file:///D:/Trabalho/Club%20Maravilha/.env)):**
   - Configurado `WHATSAPP_PROVIDER=BAILEYS`, `WHATSAPP_ENGINE_URL=http://localhost:3001`, `ADMIN_EMAIL`, `ADMIN_PASSWORD` e `POSTGRES_PORT=5433`.

---

## 4. 🚀 Comandos Rápidos de Operação

### Executar Testes Automatizados (Sem Docker):
```powershell
# Backend (870 testes com SQLite em memória assíncrono):
cd backend
.\.venv\Scripts\pytest.exe

# Frontend (176 testes Vitest):
cd frontend
npm test

# WhatsApp Engine (113 testes Vitest):
cd whatsapp-engine
npm test
```

### Gerenciamento dos Containers Docker:
```powershell
# Subir ambiente completo com build:
docker compose up -d --build

# Ver status dos serviços:
docker compose ps

# Visualizar logs em tempo real:
docker compose logs -f

# Aplicar migrações do Alembic (se houver novas):
docker compose exec backend python -m scripts.migrate

# Parar serviços:
docker compose down
```

---

## 5. 📋 Próximas Fases (Roadmap)

Conforme planejado no [`ROADMAP.md`](file:///D:/Trabalho/Club%20Maravilha/ROADMAP.md):
- **Etapa 2 — Portal do Associado e Landing Page:**
  - Desenvolvimento da interface pública do clube (apresentação, planos, estrutura esportiva).
  - Portal logado do Associado (consulta de débitos, botão de Pix Copia-e-Cola em tempo real, geração de convites e agendamento de quadras).
- **Etapa 3 — Agendamento de Quadras & Integração Catraca Facial:**
  - Travas de concorrência e limite simultâneo de reservas.
  - Sincronização em rede local com a controladora da catraca para liberação física por reconhecimento facial e QR Code.
