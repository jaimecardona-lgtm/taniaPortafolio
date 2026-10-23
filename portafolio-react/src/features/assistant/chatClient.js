/**
 * Cliente centralizado para comunicación con /api/chat
 */

// Margen para cold start de Render (el backend puede tardar en despertar)
const CHAT_REQUEST_TIMEOUT = 75000;

// Timeout separado para el warmup: no bloquea nada, solo despierta el backend
const WARMUP_TIMEOUT = 60000;

// Reintentos con backoff para 502/503/504 (cold start / gateway)
const RETRY_DELAYS = [2000, 4000, 8000];
const RETRYABLE_STATUSES = [502, 503, 504];

/**
 * Obtiene la URL base del API
 */
function getChatApiUrl() {
  const baseUrl = import.meta.env.VITE_CHAT_API_URL;
  if (!baseUrl) {
    throw new Error('VITE_CHAT_API_URL no está configurado');
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
        throw httpError(429, 'Demasiadas solicitudes. Intenta más tarde.');
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
 * ¿Vale la pena reintentar este error?
 * Solo 502/503/504 y fallos de red (fetch lanza TypeError). Nunca 400/401/403.
 */
function isRetryable(error) {
  if (error.status !== undefined) {
    return RETRYABLE_STATUSES.includes(error.status);
  }
  return error instanceof TypeError;
}

/**
 * Espera el backoff, cancelable con el signal del usuario
 */
function wait(ms, signal) {
  return new Promise((resolve, reject) => {
    if (signal?.aborted) {
      reject(cancelledError());
      return;
    }

    const onAbort = () => {
      clearTimeout(timer);
      reject(cancelledError());
    };

    const timer = setTimeout(() => {
      signal?.removeEventListener('abort', onAbort);
      resolve();
    }, ms);

    signal?.addEventListener('abort', onAbort);
  });
}

/**
 * Realiza una solicitud de chat al servidor, con reintentos automáticos.
 * El mensaje del usuario se envía una sola vez; los reintentos ocurren aquí dentro.
 * @param {Array} messages - Historial de mensajes
 * @param {AbortSignal} signal - Signal para cancelar la solicitud
 * @param {{onRetry?: (attempt: number) => void}} options - Callback al iniciar un reintento
 * @returns {Promise<{role: string, content: string}>}
 */
export async function sendChatMessage(messages, signal, { onRetry } = {}) {
  const endpoint = `${getChatApiUrl()}/api/chat`;

  for (let attempt = 0; ; attempt++) {
    try {
      return await attemptChat(endpoint, messages, signal);
    } catch (error) {
      const canRetry =
        attempt < RETRY_DELAYS.length && isRetryable(error) && !signal?.aborted;

      if (!canRetry) {
        throw error;
      }

      onRetry?.(attempt + 1);
      await wait(RETRY_DELAYS[attempt], signal);
    }
  }
}
