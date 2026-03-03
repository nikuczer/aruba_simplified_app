FROM python:3.11-slim

ARG MAIN_SCRIPT=aruba_empty.py
ENV MAIN_SCRIPT=${MAIN_SCRIPT}

WORKDIR /app

# Installe les dépendances d'abord (meilleur cache Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copie le reste du code
COPY . .

CMD ["sh", "-c", "python -u ${MAIN_SCRIPT}"]