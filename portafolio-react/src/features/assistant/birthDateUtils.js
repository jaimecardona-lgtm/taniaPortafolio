/**
 * Utilidades para calcular edad y detectar cumpleaños de Tania
 */

// Febrero 24, 2003. Misma fecha biográfica que backend/app/context/tania_context.py
// (el backend la usa para que el modelo conozca la edad sin depender de este código).
const TANIA_BIRTH_DATE = new Date(2003, 1, 24);

/**
 * Calcula la edad actual de Tania basada en la fecha actual
 * @returns {number} La edad en años
 */
export function getTaniaAge() {
  const today = new Date();
  let age = today.getFullYear() - TANIA_BIRTH_DATE.getFullYear();
  const monthDiff = today.getMonth() - TANIA_BIRTH_DATE.getMonth();

  if (
    monthDiff < 0 ||
    (monthDiff === 0 && today.getDate() < TANIA_BIRTH_DATE.getDate())
  ) {
    age--;
  }

  return age;
}

/**
 * Verifica si hoy es el cumpleaños de Tania
 * @returns {boolean} true si hoy es cumpleaños, false en caso contrario
 */
export function isTaniaBirthday() {
  const today = new Date();
  return (
    today.getMonth() === TANIA_BIRTH_DATE.getMonth() &&
    today.getDate() === TANIA_BIRTH_DATE.getDate()
  );
}

/**
 * Obtiene el siguiente cumpleaños de Tania
 * @returns {Date} La fecha del próximo cumpleaños
 */
export function getNextBirthday() {
  const today = new Date();
  let nextBirthday = new Date(today.getFullYear(), 1, 24); // 24 de febrero

  if (nextBirthday < today) {
    nextBirthday = new Date(today.getFullYear() + 1, 1, 24);
  }

  return nextBirthday;
}

/**
 * Obtiene información de contexto sobre Tania incluyendo edad y cumpleaños
 * @returns {string} Información formateada para incluir en el contexto del agente
 */
export function getTaniaContextInfo() {
  const age = getTaniaAge();
  const isBirthday = isTaniaBirthday();

  if (isBirthday) {
    return `Tania nació el 24 de febrero de 2003 y HOY ES SU CUMPLEAÑOS. Cumple ${age} años hoy. Deberías mencionar de manera cálida y genuina que es su cumpleaños si es relevante en la conversación.`;
  }

  const nextBirthday = getNextBirthday();
  const daysUntilBirthday = Math.ceil(
    (nextBirthday - new Date()) / (1000 * 60 * 60 * 24)
  );

  return `Tania nació el 24 de febrero de 2003 y actualmente tiene ${age} años. Su próximo cumpleaños es en ${daysUntilBirthday} días (24 de febrero).`;
}

/**
 * Obtiene información de nacimiento para incluir en mensajes
 * @returns {object} Objeto con información de edad y cumpleaños
 */
export function getTaniaBirthInfo() {
  return {
    birthDate: '24 de febrero de 2003',
    currentAge: getTaniaAge(),
    isBirthdayToday: isTaniaBirthday(),
    nextBirthdayAge: isTaniaBirthday() ? getTaniaAge() : getTaniaAge() + 1,
  };
}
