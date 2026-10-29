# syntax=docker/dockerfile:1

# ---------- Stage 1: build del frontend (Node solo existe en esta etapa) ----------
FROM node:22-bookworm-slim AS frontend

WORKDIR /build/frontend

COPY portafolio-react/package.json portafolio-react/package-lock.json ./
RUN npm ci

COPY portafolio-react/ ./
RUN npm run build

# ---------- Stage 2: runtime (Nginx público + FastAPI interno, gestionados por Supervisor) ----------
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=10000

RUN apt-get update \
    && apt-get install -y --no-install-recommends nginx supervisor \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY backend/requirements.txt /app/requirements.txt
RUN pip install -r /app/requirements.txt

COPY backend /app/backend
COPY --from=frontend /build/frontend/dist /app/frontend-dist
COPY deploy /app/deploy

RUN cp /app/deploy/start.sh /app/start.sh \
    && chmod +x /app/start.sh

EXPOSE 10000

CMD ["/app/start.sh"]
