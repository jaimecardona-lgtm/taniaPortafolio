# Despliegue del Portafolio y Asistente en Render

Este documento describe el despliegue actual: **un único Web Service Docker** en Render.

## Arquitectura

```
Internet
  ↓
Nginx (único proceso público, escucha en $PORT)
  ├── /*      → React compilado (estático)
  └── /api/*  → FastAPI / Uvicorn (127.0.0.1:8000, interno)
                  ↓
                OpenRouter API
```

- `Dockerfile` (raíz): build multi-stage. Stage 1 compila el frontend con Node 22; stage 2 es Python 3.11 con Nginx y Supervisor, y copia el `dist` compilado.
- `deploy/start.sh`: genera la config de Nginx con `$PORT` y arranca Supervisor.
- `deploy/supervisord.conf`: administra uvicorn (FastAPI) y Nginx.
- `deploy/nginx.conf.template`: rutas SPA, `/api/*` hacia FastAPI, videos servidos por Nginx con soporte de Range.
- El frontend usa rutas relativas (`/api/chat`, `/api/health`), así que en producción es mismo origen y no requiere CORS.

---

## Requisitos previos

- Cuenta en [Render](https://render.com)
- Cuenta en [OpenRouter](https://openrouter.ai) con API key generada
- Para pruebas locales: Docker Desktop

---

## Paso 1: Variables de entorno en Render

Definidas en `render.yaml` (Blueprint):

| Variable | Valor |
|---|---|
| `OPENROUTER_API_KEY` | **Secreta**. Se configura en el dashboard (`sync: false`). Nunca en el repositorio. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_SITE_NAME` | `Tania Pelaez Valverde Portfolio` |
| `CHAT_PRIMARY_LLM` | `nvidia/nemotron-3.5-lightning:free` |
| `CHAT_FALLBACK_LLM` | `openrouter/free` |
| `CHAT_USE_FALLBACK` | `true` |
| `CHAT_TEMPERATURE` | `0.2` |
| `CHAT_TOP_P` | `0.8` |
| `CHAT_MAX_TOKENS` | `450` |
| `CHAT_TIMEOUT_MS` | `45000` |

`OPENROUTER_SITE_URL` no se declara: el backend usa `RENDER_EXTERNAL_URL` (inyectada por Render) como referer. `VITE_CHAT_API_URL` no se declara: el frontend es mismo origen.

---

## Paso 2: Crear o sincronizar el servicio

1. En Render Dashboard: **New → Blueprint** y selecciona el repositorio.
2. Render lee `render.yaml` y crea un servicio Web (`tania-portafolio`) con:
   - `runtime: docker`
   - `dockerfilePath: ./Dockerfile`
   - `dockerContext: .`
   - `healthCheckPath: /api/health`
3. Define `OPENROUTER_API_KEY` en **Environment**.
4. Espera al primer deploy.

### Migración desde la arquitectura anterior (dos servicios)

Antes de sincronizar el Blueprint, revisa en el Dashboard:

- Si existe el **Static Site** `tania-portafolio` y el **Web Service** `tania-portafolio-api` de la arquitectura anterior, un Blueprint no cambia el runtime de un servicio existente de forma fiable. Verifica el resultado antes de confirmar.
- El dominio `taniaportafolio.onrender.com` pertenece hoy al Static Site. Decide si el nuevo servicio usará ese dominio (eliminando o renombrando antes el Static Site) o una URL nueva.
- Elimina `tania-portafolio-api` solo cuando el nuevo servicio esté verificado.

---

## Paso 3: Verificar el despliegue

```bash
BASE=https://<tu-servicio>.onrender.com

curl -i $BASE/api/health                       # 200, {"status":"ok",...}
curl -I $BASE/empresa                          # 200 (SPA)
curl -I $BASE/experiencia                      # 200 (SPA)
curl -I $BASE/portafolio                       # 200 (SPA)
curl -i -H "Range: bytes=0-1023" $BASE/elecciones/video4.mp4   # 206 Partial Content
```

---

## Desarrollo local

### Con Docker (igual que producción)

Crea `backend/.env` a partir de `backend/.env.example` y añade tu API key localmente.

```bash
docker compose build
docker compose up -d
docker compose ps                                 # "healthy"
curl http://localhost:10000/api/health
```

Abre http://localhost:10000. Para detener: `docker compose down`.

`docker-compose.yml` solo sirve para desarrollo y verificación local. Render no lo utiliza.

### Frontend y backend separados

```bash
# Backend
cd backend
uvicorn app.main:app --host 127.0.0.1 --port 8000

# Frontend, con VITE_CHAT_API_URL=http://localhost:8000 en portafolio-react/.env
cd portafolio-react
npm run dev
```

---

## Solución de problemas

### El deploy falla en el health check
- Revisa los logs del servicio en Render.
- Causa habitual: `OPENROUTER_API_KEY` no definida. El backend no arranca y `/api/health` no responde.

### `/api/chat` responde 429
- Límite del proveedor OpenRouter. El backend no reintenta; el usuario puede volver a intentar más tarde.

### Videos no reproducen
- Verifica que la respuesta incluya `206 Partial Content` con `Range`.

### La página en una ruta profunda devuelve 404
- Las rutas SPA caen en `index.html` desde Nginx. Si ocurre, revisa `deploy/nginx.conf.template`.

---

## Seguridad

- La API key de OpenRouter vive solo en variables de entorno de runtime. No está en el repositorio, en el `Dockerfile`, ni en la imagen.
- `backend/.env` está ignorado por Git y excluido de la imagen (`.dockerignore`).
- `.claude/`, `.git/` y `node_modules/` están excluidos del contexto Docker.
- Revisa logs en Render y el uso de tokens en OpenRouter para detectar abuso.
