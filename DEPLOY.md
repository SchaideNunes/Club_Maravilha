# 🚀 Guia de Deploy em VPS - Club Maravilha

Este guia contém o passo a passo completo para colocar o sistema do **Club Maravilha** em produção em qualquer provedor de VPS (Hetzner, Contabo, DigitalOcean, Linode, AWS Lightsail, etc.) com **Linux Ubuntu 22.04 ou 24.04 LTS**.

---

## 💻 Requisitos Recomendados da VPS
- **CPU:** 1 vCPU ou 2 vCPUs
- **Memória RAM:** 1 GB ou 2 GB (o sistema consome ~400 MB)
- **Disco:** 20 GB SSD
- **Sistema Operacional:** Ubuntu 22.04 / 24.04 LTS
- **Custo estimado:** Entre R$ 25,00 a R$ 45,00 / mês

---

## 🛠️ Passo 1: Instalação do Docker na VPS

Acesse a VPS via terminal SSH:
```bash
ssh root@SEU_IP_DA_VPS
```

Execute a atualização do sistema e a instalação do Docker:
```bash
apt update && apt upgrade -y
apt install -y curl git ufw

# Instalação do Docker oficial
curl -fsSL https://get.docker.com | sh

# Habilitar inicialização automática com o sistema
systemctl enable docker
systemctl start docker
```

Configure o Firewall básico (UFW) liberando SSH, HTTP e HTTPS:
```bash
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable
```

---

## 📥 Passo 2: Clonar o Projeto e Configurar o `.env`

Baixe o projeto do GitHub na pasta `/opt`:
```bash
cd /opt
git clone https://github.com/SchaideNunes/Club_Maravilha.git club-maravilha
cd /opt/club-maravilha
```

Crie o arquivo de configuração de produção a partir do modelo:
```bash
cp .env.example .env
nano .env
```

### 🔒 Variáveis Críticas para Alterar no `.env`:
1. `ENVIRONMENT=production`
2. `DEBUG=false`
3. `SECRET_KEY`: Gere uma chave aleatória forte rodando `openssl rand -hex 32` no terminal.
4. `POSTGRES_PASSWORD`: Defina uma senha forte para o banco.
5. `ALLOWED_ORIGINS`: Coloque o domínio do clube (ex: `https://clubmaravilha.com.br,https://www.clubmaravilha.com.br`).
6. `PIX_WEBHOOK_SECRET`: Chave secreta compartilhada com a Efí (Gerencianet).
7. `WHATSAPP_API_URL` e `WHATSAPP_API_KEY`: Dados da sua instância da Evolution API.

Salve o arquivo (`Ctrl + O`, depois `Enter`, depois `Ctrl + X`).

---

## 🚀 Passo 3: Iniciar o Sistema em Produção

Execute o Docker Compose de produção:
```bash
docker compose -f docker-compose.prod.yml up -d --build
```

O comando irá:
1. Subir o PostgreSQL 16 Alpine com volume persistente.
2. Executar as migrações automáticas do banco (`alembic upgrade head`).
3. Iniciar a API FastAPI com 2 workers assíncronos.
4. Compilar o Frontend React SPA em build estático otimizado.
5. Iniciar o Nginx servindo o Frontend e redirecionando a API `/api/` e os Webhooks.

Para verificar se todos os containers estão saudáveis:
```bash
docker compose -f docker-compose.prod.yml ps
```

Para acompanhar os logs em tempo real:
```bash
docker compose -f docker-compose.prod.yml logs -f
```

---

## 🔒 Passo 4: Ativar Certificado SSL Gratuito (HTTPS / Let's Encrypt)

Para que o gateway do Pix envie os Webhooks com segurança, é obrigatório ter HTTPS ativo.

Aponte seu domínio (ex: `clubmaravilha.com.br`) para o IP da sua VPS no seu registrador de domínio (ex: Registro.br / Cloudflare).

Na VPS, instale o Certbot:
```bash
apt install -y certbot
```

Gere o certificado para o seu domínio:
```bash
certbot certonly --webroot -w /opt/club-maravilha/docker/nginx -d clubmaravilha.com.br -d www.clubmaravilha.com.br
```

---

## 🔄 Como Atualizar o Sistema (Novas Funcionalidades)

Sempre que novas funcionalidades forem commitadas no GitHub, basta rodar na VPS:
```bash
cd /opt/club-maravilha
git pull origin main
docker compose -f docker-compose.prod.yml up -d --build
```
A atualização é aplicada sem perder dados do banco e com tempo de inatividade mínimo.

---

## 💾 Backup do Banco de Dados

Para realizar um backup manual do banco PostgreSQL a qualquer momento:
```bash
docker compose -f docker-compose.prod.yml exec -T db pg_dump -U club_admin club_maravilha > backup_$(date +%Y%m%d_%H%M%S).sql
```
