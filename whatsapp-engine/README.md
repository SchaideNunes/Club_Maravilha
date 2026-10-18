# whatsapp-engine

Motor de WhatsApp do Club Maravilha: microsserviço Node/TypeScript baseado em Baileys
(`@whiskeysockets/baileys`), consumido pelo backend via HTTP.

> **Status:** placeholder. O motor será implementado na **Feature 4** do MVP.
> Hoje existe apenas o `Dockerfile`, que mantém o serviço do `docker-compose` "buildável".

## Contrato de infraestrutura (já configurado nos `docker-compose*.yml`)

| Item | Valor |
|---|---|
| Porta interna | `3001` (`PORT`) |
| URL usada pelo backend | `WHATSAPP_ENGINE_URL=http://whatsapp-engine:3001` |
| Autenticação | header `x-api-key` com o valor de `WHATSAPP_API_KEY` (`API_KEY` no engine) |
| Sessão do WhatsApp | volume nomeado `whatsapp_auth`, montado em `/app/auth` (`AUTH_DIR`) |

A pasta `auth/` guarda as credenciais do número conectado e nunca deve ser versionada.
