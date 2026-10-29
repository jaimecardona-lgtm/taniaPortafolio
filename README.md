# taniaPortafolio

Portafolio profesional de Tania Peláez Valverde con asistente conversacional integrado.

## Estructura

- `portafolio-react/` — sitio principal (Vite + React + React Router) con asistente integrado.
  - `src/features/assistant/` — componentes y lógica del asistente conversacional.
- `backend/` — API FastAPI del asistente (`/api/health`, `/api/chat`) que llama a OpenRouter.
- `deploy/` — configuración de Nginx, Supervisor y script de inicio del contenedor.
- `Dockerfile` — imagen única de producción (frontend compilado + backend + Nginx + Supervisor).
- `docker-compose.yml` — ejecución local de la misma imagen que se despliega en Render.
- `docs/` — guía de despliegue (`docs/assistant-deploy.md`).

## Arquitectura

Se despliega como **un único Web Service Docker** en Render. Dentro del contenedor, React y FastAPI siguen separados:

```
Internet
  ↓
Nginx (único proceso público, escucha en $PORT)
  ├── /*      → React compilado (index.html + assets, videos, PDF e imágenes)
  └── /api/*  → FastAPI / Uvicorn (interno, 127.0.0.1:8000)
                  ↓
                OpenRouter API
```

- Supervisor administra Nginx y FastAPI dentro del contenedor.
- El frontend usa rutas relativas (`/api/chat`, `/api/health`): en producción es mismo origen, sin CORS.
- La API key de OpenRouter solo existe en runtime (variable de entorno). Nunca entra al repositorio ni a la imagen.

## Desarrollo local

### Opción A: contenedor (igual que producción)

Requiere Docker Desktop y un archivo `backend/.env` (copia de `backend/.env.example` con tu API key).

```bash
docker compose build
docker compose up -d
docker compose ps        # el servicio debe quedar "healthy"
```

- Sitio: http://localhost:10000
- Health: http://localhost:10000/api/health

Para detenerlo: `docker compose down`.

### Opción B: frontend y backend separados (desarrollo con recarga)

Backend:

```bash
cd backend
pip install -r requirements.txt
uvicorn app.main:app --host 127.0.0.1 --port 8000
```

Frontend (en otra terminal), con `portafolio-react/.env`:

```
VITE_CHAT_API_URL=http://localhost:8000
```

```bash
cd portafolio-react
npm install
npm run dev
```

Abre http://localhost:5173. Sin `VITE_CHAT_API_URL` el frontend usa mismo origen (`/api/*`), que en `npm run dev` no existe; por eso esta variable es necesaria en este modo.

## Variables de entorno

### Backend (`backend/.env` en local, Environment en Render)

Copia `backend/.env.example` como `backend/.env`. Nunca subas `backend/.env` al repositorio.

| Variable | Descripción |
|---|---|
| `OPENROUTER_API_KEY` | API key de OpenRouter. **Secreta**: solo en `.env` local o en el dashboard de Render. |
| `OPENROUTER_BASE_URL` | `https://openrouter.ai/api/v1` |
| `OPENROUTER_SITE_URL` | Opcional. Referer de OpenRouter. Si está vacío: `RENDER_EXTERNAL_URL` (en Render) o `http://localhost:10000` (local). |
| `OPENROUTER_SITE_NAME` | Nombre del sitio para OpenRouter. |
| `CHAT_PRIMARY_LLM` / `CHAT_FALLBACK_LLM` / `CHAT_USE_FALLBACK` | Modelo principal, fallback y si se usa fallback. |
| `CHAT_TEMPERATURE`, `CHAT_TOP_P`, `CHAT_MAX_TOKENS`, `CHAT_TIMEOUT_MS` | Parámetros de generación. |
| `ALLOWED_ORIGINS` | Orígenes CORS. Solo importa en desarrollo con frontend separado. |

### Frontend (`portafolio-react/.env`)

```
# Opcional. Vacío = mismo origen (/api/*). Solo necesario con frontend y backend separados.
VITE_CHAT_API_URL=
```

Esta variable no contiene secretos.

## Despliegue en Render

Producción usa el `Dockerfile` de la raíz. Render construye la imagen y levanta un único servicio.

1. En Render Dashboard: **New → Blueprint** y conecta el repositorio (usa `render.yaml`).
2. En el servicio, **Environment**, define `OPENROUTER_API_KEY` (el Blueprint la marca con `sync: false`, así que Render te la pedirá).
3. Render comprueba `GET /api/health` antes de dar por buena cada versión.

Notas:
- El Blueprint declara `runtime: docker`, `dockerfilePath: ./Dockerfile`, `dockerContext: .` y `healthCheckPath: /api/health`.
- No se configura `VITE_CHAT_API_URL` en Render: el frontend es mismo origen.
- Antes de sincronizar un Blueprint sobre un servicio que ya existe, revisa `docs/assistant-deploy.md` (sección de migración).

## Build y validación

```bash
# Frontend
cd portafolio-react
npm ci
npm run build

# Imagen completa
cd ..
docker compose config --quiet   # valida docker-compose.yml sin imprimir variables
docker compose build
```

## Componentes del asistente

### Frontend

- `AssistantWidget.jsx` — Widget principal (botón flotante + panel de chat)
- `useAssistantChat.js` — Hook que maneja estado de conversación
- `chatClient.js` — Cliente centralizado para `/api/chat` y `/api/health`
- `AssistantWidget.module.css` — Estilos (usa paleta de colores del portafolio)

### Backend

- `app/main.py` — Endpoints `/api/health` y `/api/chat`, CORS y mapeo de errores
- `app/services/openrouter.py` — Cliente de OpenRouter con modelo principal y fallback controlado
- `app/services/response_guard.py` — Limpieza local de la respuesta (sin llamadas extra al modelo)
- `app/prompts/tania.py` — System prompt del asistente

## Características

✅ Botón flotante elegante en esquina inferior derecha
✅ Panel conversacional integrado con identidad visual del portafolio
✅ Colores: rose (#e974a3), brown (#4a3d33), sand (#f5ece1), gold (#D8B36A)
✅ Tipografía: Playfair Display (títulos), Outfit (cuerpo)
✅ Responsive (desktop, tablet, mobile)
✅ Mensaje inicial con sugerencias contextuales
✅ Indicadores de carga y errores
✅ Botón para limpiar conversación
✅ Botón para reintentar si hay error
✅ Auto-scroll al último mensaje
✅ Accesibilidad: aria-labels, teclado, roles semánticos
✅ Protección contra prompt injection
✅ Límites de tasa y validación en servidor

## Conocimiento del asistente

El asistente "conoce" todo sobre Tania a partir de:
- Información en Home.jsx, Empresa.jsx, Experiencia.jsx, Portafolio.jsx
- Datos en publicaciones.js
- Nada se inventa; todo es verificable en el portafolio

Responde sobre:
- Perfil y formación de Tania
- Experiencia en Comité de Cafeteros
- Funciones, responsabilidades y logros
- Proyectos: "Tu voto, tu gremio", #ESDELC, "Más allá del lente"
- Habilidades profesionales
- Cómo contactar a Tania

## Seguridad

🔒 **Lo que está protegido:**
- La API key de OpenRouter nunca llega al navegador ni a la imagen Docker (solo existe en runtime)
- Validación de requests en servidor (no solo frontend)
- Errores 429 y de cliente (400/401/402/403) no hacen fallback; solo fallos reales del proveedor
- Límites de mensajes, longitud, tokens y timeouts

⚠️ **Monitorear:**
- Logs del contenedor en Render para actividad anómala
- Uso de tokens en OpenRouter (cambios bruscos = abuso)

## Troubleshooting

**`docker compose ps` muestra "unhealthy" o "starting" por mucho tiempo:**
- Revisa `docker compose logs tania-app`
- Si falta `OPENROUTER_API_KEY` en `backend/.env`, el backend no arranca (Supervisor lo reintenta; Nginx sigue sirviendo el sitio).

**El asistente no responde en local con `npm run dev`:**
- Verifica que `portafolio-react/.env` tenga `VITE_CHAT_API_URL=http://localhost:8000` y que uvicorn esté corriendo en el puerto 8000.

**"Tania está recibiendo muchas consultas":**
- Es el límite del proveedor (429). Espera unos minutos; el servidor no reintenta automáticamente.

Ver `docs/assistant-deploy.md` para el despliegue completo en Render.
