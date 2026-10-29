#!/bin/sh
# Punto de entrada único del contenedor (Render y docker compose).
# Genera la config de Nginx con el puerto público y delega en Supervisor,
# que levanta FastAPI en 127.0.0.1:8000 y Nginx en $PORT.
set -eu

PORT="${PORT:-10000}"

# Quitar el default site de Nginx para que no compita con nuestro server
rm -f /etc/nginx/sites-enabled/default

sed "s/__PORT__/${PORT}/g" /app/deploy/nginx.conf.template > /etc/nginx/conf.d/default.conf

nginx -t

exec supervisord -c /app/deploy/supervisord.conf
