FROM python:3.12-slim

# Instala dependências de sistema essenciais (FFmpeg e libsndfile)
RUN apt-get update && apt-get install -y --no-install-recommends \
    ffmpeg \
    libsndfile1 \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Garante compatibilidade com virtualenvs montados do host (/usr/bin/python3)
RUN ln -sf /usr/local/bin/python3 /usr/bin/python3

WORKDIR /app

# Instala pacotes Python
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia código da aplicação
COPY . .

# Garante permissões nos diretórios de trabalho
RUN mkdir -p uploads output static/assets

EXPOSE 8000

ENV PORT=8000
ENV PYTHONUNBUFFERED=1

CMD ["uvicorn", "app:app", "--host", "0.0.0.0", "--port", "8000"]
