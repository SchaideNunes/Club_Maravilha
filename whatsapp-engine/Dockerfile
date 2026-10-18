# ==============================================================================
# CLUB MARAVILHA - WHATSAPP ENGINE (PLACEHOLDER)
# O motor Baileys (Node/TypeScript) será implementado na Feature 4 do MVP.
# Este Dockerfile apenas mantém o serviço `whatsapp-engine` do docker-compose
# "buildável" e o container vivo até lá.
# ==============================================================================

FROM node:20-alpine

WORKDIR /app

# Diretório da sessão autenticada (volume nomeado `whatsapp_auth` no docker-compose)
RUN mkdir -p /app/auth

EXPOSE 3001

CMD ["node", "-e", "console.log('[whatsapp-engine] placeholder: o motor Baileys sera implementado na Feature 4'); setInterval(() => {}, 60000);"]
