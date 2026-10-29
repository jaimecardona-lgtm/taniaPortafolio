# ⚡ Despliegue rápido en Render (Docker)

Un único Web Service Docker: Nginx público + React compilado + FastAPI interno.

## Requisitos previos

- Cuenta en Render
- API key de OpenRouter (https://openrouter.ai/keys)
- Repositorio conectado a Render

---

## 1️⃣ Crear el servicio desde el Blueprint (2 min)

1. En https://dashboard.render.com: **New → Blueprint**
2. Selecciona el repositorio. Render lee `render.yaml` y crea el servicio `tania-portafolio` (runtime Docker, plan Free).

> Antes de sincronizar, revisa la sección de migración en `docs/assistant-deploy.md`.

---

## 2️⃣ Configurar la API key (1 min)

En el servicio, **Environment**:

- **Key:** `OPENROUTER_API_KEY`
- **Value:** tu API key (no la subas al repositorio)

---

## 3️⃣ Desplegar (5–10 min la primera vez)

Render construye el `Dockerfile` de la raíz y espera a que `/api/health` responda.

---

## ✅ Verificar

```bash
curl https://<tu-servicio>.onrender.com/api/health
```

Debe responder: `{"status":"ok","service":"tania-portfolio-api"}`

Luego abre la URL del sitio, usa el botón flotante del asistente y haz una pregunta.

---

## ❌ Algo salió mal

| Problema | Solución |
|----------|----------|
| Deploy falla en health check | Revisa los logs del servicio en Render. Suele ser `OPENROUTER_API_KEY` ausente. |
| Asistente responde con error de servicio | Revisa logs; si es 429, el límite del proveedor se alcanzó: espera unos minutos. |
| Videos no cargan | Verifica en el navegador que la petición del video devuelva `206`. |

---

**Desarrollo local:** `docker compose up -d` y abre http://localhost:10000.
