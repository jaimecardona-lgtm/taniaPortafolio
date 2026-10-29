/**
 * Cliente centralizado para comunicación con /api/chat
 */

// Margen para cold start de Render (el backend puede tardar en despertar)
const CHAT_REQUEST_TIMEOUT = 75000;

// Timeout separado para el warmup: no bloquea nada, solo despierta el backend
const WARMUP_TIMEOUT = 60000;

// Sin reintentos automáticos: el backend ya hace fallback y cada request consume
// el free tier. Si falla, el usuario reintenta manualmente con el botón.
const RATE_LIMIT_MESSAGE =
  'Tania está recibiendo muchas consultas en este momento. Intenta nuevamente en unos minutos.';

/**
 * Obtiene la URL base del API.
 * Vacía = mismo origen (/api/*), que es lo que usa el contenedor en producción.
 */
function getChatApiUrl() {
  const baseUrl = import.meta.env.VITE_CHAT_API_URL?.trim();
  if (!baseUrl) {
    return '';
  }
  return baseUrl.replace(/\/$/, ''); // Remover trailing slash si existe
}

/**
 * Despierta el backend (Render) antes del primer mensaje.
 * Nunca lanza: si falla, el primer envío reintentará automáticamente.
 */
export async function warmUpChatApi() {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), WARMUP_TIMEOUT);

  try {
    const baseUrl = getChatApiUrl();
    await fetch(`${baseUrl}/api/health`, {
      method: 'GET',
      signal: controller.signal,
    });
  } catch {
    // Silencioso a propósito
  } finally {
    clearTimeout(timeoutId);
  }
}

function httpError(status, message) {
  const error = new Error(message);
  error.status = status;
  return error;
}

function cancelledError() {
  const error = new Error('La solicitud fue cancelada');
  error.name = 'AbortError';
  return error;
}

/**
 * Una sola solicitud a /api/chat (sin reintentos)
 */
async function attemptChat(endpoint, messages, signal) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), CHAT_REQUEST_TIMEOUT);
  let abortListener = null;

  try {
    if (signal) {
      if (signal.aborted) {
        controller.abort();
      } else {
        abortListener = () => controller.abort();
        signal.addEventListener('abort', abortListener);
      }
    }

    const response = await fetch(endpoint, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({ messages }),
      signal: controller.signal,
    });

    if (!response.ok) {
      if (response.status === 429) {
        throw httpError(429, RATE_LIMIT_MESSAGE);
      }

      if (response.status >= 500) {
        throw httpError(
          response.status,
          'El servidor está experimentando problemas. Intenta más tarde.'
        );
      }

      const errorData = await response.json().catch(() => ({}));
      throw httpError(
        response.status,
        errorData.detail ||
          errorData.error ||
          `Error ${response.status}: No se pudo procesar tu solicitud.`
      );
    }

    const data = await response.json();

    if (!data.role || !data.content) {
      throw new Error('Respuesta inválida del servidor');
    }

    return data;
  } catch (error) {
    if (error.name === 'AbortError') {
      // Cancelación del usuario vs. timeout propio
      if (signal?.aborted) {
        throw cancelledError();
      }
      throw new Error('El servidor tardó demasiado. Intenta de nuevo.');
    }

    throw error;
  } finally {
    clearTimeout(timeoutId);
    if (signal && abortListener) {
      signal.removeEventListener('abort', abortListener);
    }
  }
}

/**
 * Realiza una única solicitud de chat al servidor (sin reintentos).
 * @param {Array} messages - Historial de mensajes
 * @param {AbortSignal} signal - Signal para cancelar la solicitud
 * @returns {Promise<{role: string, content: string}>}
 */
export async function sendChatMessage(messages, signal) {
  const endpoint = `${getChatApiUrl()}/api/chat`;
  return attemptChat(endpoint, messages, signal);
}
