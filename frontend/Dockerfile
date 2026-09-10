# ==============================================================================
# CLUB MARAVILHA - FRONTEND DOCKERFILE (Node 20 Alpine)
# ==============================================================================

FROM node:20-alpine

WORKDIR /app

# Instala dependências primeiro para cache eficiente de camadas Docker
COPY package*.json ./
RUN npm install

# Copia o código da aplicação
COPY . .

EXPOSE 5173

# Modo dev com host exposto para docker compose
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]
