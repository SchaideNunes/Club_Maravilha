# ==============================================================================
# CLUB MARAVILHA - FRONTEND DOCKERFILE (Multi-Stage Build)
# Suporta tanto ambiente de desenvolvimento (Vite) quanto produção (Nginx Alpine)
# ==============================================================================

# --- [Stage 1: Base e Desenvolvimento Local] ---
FROM node:20-alpine AS development

WORKDIR /app
COPY package*.json ./
RUN npm install
COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

# --- [Stage 2: Compilação de Produção] ---
FROM development AS builder
RUN npm run build

# --- [Stage 3: Servidor Web de Produção Ultraleve (Nginx Alpine)] ---
FROM nginx:1.25-alpine AS production

# Copia os artefatos compilados e a configuração otimizada do Nginx
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf /etc/nginx/conf.d/default.conf

EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]
