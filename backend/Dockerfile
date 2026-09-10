# ==============================================================================
# CLUB MARAVILHA - BACKEND DOCKERFILE (Python 3.11 Slim)
# ==============================================================================

FROM python:3.11-slim

# Evita criação de arquivos .pyc e força buffer stdout/stderr imediato
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências de sistema essenciais (libpq para postgres, curl para healthchecks)
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Instala dependências do Python primeiro para otimização de cache de camadas Docker
COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Copia código-fonte da aplicação
COPY . /app

EXPOSE 8000

# Inicialização padrão para desenvolvimento (sobrescrita no docker-compose com hot-reload)
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
