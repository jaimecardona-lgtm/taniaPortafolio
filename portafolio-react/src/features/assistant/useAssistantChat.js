import { useState, useCallback, useRef } from 'react';
import { sendChatMessage } from './chatClient';

// Si la respuesta tarda más que esto, se asume cold start y se muestra "Conectando"
const CONNECTING_HINT_DELAY = 4000;

/**
 * Hook para gestionar el estado de la conversación del asistente
 */
export function useAssistantChat() {
  const [messages, setMessages] = useState([]);
  const [isLoading, setIsLoading] = useState(false);
  const [isConnecting, setIsConnecting] = useState(false);
  const [error, setError] = useState(null);
  const abortControllerRef = useRef(null);

  /**
   * Pide respuesta al backend y actualiza el estado de conexión
   */
  const requestReply = useCallback((history, signal) => {
    const hintTimer = setTimeout(() => setIsConnecting(true), CONNECTING_HINT_DELAY);

    return sendChatMessage(history, signal, {
      onRetry: () => setIsConnecting(true),
    }).finally(() => {
      clearTimeout(hintTimer);
      setIsConnecting(false);
    });
  }, []);

  /**
   * Envía un mensaje y obtiene respuesta del asistente
   */
  const sendMessage = useCallback(
    async (userMessage) => {
      if (!userMessage || userMessage.trim().length === 0) {
        return;
      }

      // Limpiar errores previos
      setError(null);

      // Agregar mensaje del usuario
      const newUserMessage = {
        role: 'user',
        content: userMessage.trim(),
      };

      setMessages((prev) => [...prev, newUserMessage]);
      setIsLoading(true);

      // Preparar historial para enviar (mantener últimos 12 mensajes para control de costo)
      const MAX_HISTORY = 12;
      const historyToSend = [...messages, newUserMessage].slice(-MAX_HISTORY);

      try {
        // Crear nuevo AbortController para esta solicitud
        abortControllerRef.current = new AbortController();

        const response = await requestReply(
          historyToSend,
          abortControllerRef.current.signal
        );

        setMessages((prev) => [...prev, response]);
        setError(null);
      } catch (err) {
        const errorMessage = err.message || 'Ocurrió un error al procesar tu solicitud.';
        setError(errorMessage);
        console.error('Chat error:', err);
      } finally {
        setIsLoading(false);
        abortControllerRef.current = null;
      }
    },
    [messages, requestReply]
  );

  /**
   * Cancela la solicitud actual
   */
  const cancelMessage = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsLoading(false);
    }
  }, []);

  /**
   * Limpia la conversación
   */
  const clearChat = useCallback(() => {
    setMessages([]);
    setError(null);
    cancelMessage();
  }, [cancelMessage]);

  /**
   * Reintenta enviar el último mensaje
   */
  const retryLastMessage = useCallback(() => {
    if (messages.length === 0) return;

    // Encontrar el último mensaje del usuario
    let lastUserMessageIndex = -1;
    for (let i = messages.length - 1; i >= 0; i--) {
      if (messages[i].role === 'user') {
        lastUserMessageIndex = i;
        break;
      }
    }

    if (lastUserMessageIndex === -1) return;

    // Remover cualquier mensaje de error o respuesta incompleta después del último usuario
    setMessages((prev) => prev.slice(0, lastUserMessageIndex + 1));
    setError(null);
    setIsLoading(true);

    // Reenviar sin duplicar (usar el historial actual sin volver a agregar)
    const historyToSend = messages.slice(0, lastUserMessageIndex + 1).slice(-12);

    try {
      abortControllerRef.current = new AbortController();

      requestReply(historyToSend, abortControllerRef.current.signal)
        .then((response) => {
          setMessages((prev) => [...prev, response]);
          setError(null);
          setIsLoading(false);
        })
        .catch((err) => {
          const errorMessage = err.message || 'Ocurrió un error al procesar tu solicitud.';
          setError(errorMessage);
          setIsLoading(false);
        });
    } catch (err) {
      setError(err.message || 'Error desconocido');
      setIsLoading(false);
    }
  }, [messages, requestReply]);

  return {
    messages,
    isLoading,
    isConnecting,
    error,
    sendMessage,
    clearChat,
    retryLastMessage,
    cancelMessage,
  };
}
