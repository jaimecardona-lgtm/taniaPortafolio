"""Tests del contexto dinámico de Tania (solo biblioteca estándar)"""

import unittest
from datetime import date

from app.context.tania_context import (
    build_tania_dynamic_context,
    get_tania_age,
)


class TestTaniaAge(unittest.TestCase):
    def test_edad_antes_del_cumpleanos(self):
        self.assertEqual(get_tania_age(date(2026, 2, 23)), 22)

    def test_edad_el_dia_del_cumpleanos(self):
        self.assertEqual(get_tania_age(date(2026, 2, 24)), 23)

    def test_edad_en_octubre(self):
        self.assertEqual(get_tania_age(date(2026, 10, 29)), 23)

    def test_edad_un_dia_antes_del_siguiente_cumpleanos(self):
        self.assertEqual(get_tania_age(date(2027, 2, 23)), 23)

    def test_edad_el_dia_del_siguiente_cumpleanos(self):
        self.assertEqual(get_tania_age(date(2027, 2, 24)), 24)

    def test_sin_fecha_usa_hoy_en_bogota(self):
        self.assertIsInstance(get_tania_age(), int)


class TestTaniaDynamicContext(unittest.TestCase):
    def test_contexto_incluye_fecha_de_nacimiento_y_edad(self):
        context = build_tania_dynamic_context(today=date(2026, 10, 29))
        self.assertIn("24 de febrero de 2003", context)
        self.assertIn("23 años", context)
        self.assertIn("29 de octubre de 2026", context)
        self.assertNotIn("Hoy es el cumpleaños", context)

    def test_contexto_el_dia_del_cumpleanos(self):
        context = build_tania_dynamic_context(today=date(2027, 2, 24))
        self.assertIn("24 años", context)
        self.assertIn("cumpleaños", context)
        self.assertIn("Hoy es el cumpleaños de Tania", context)

    def test_contexto_indica_proximo_cumpleanos_fuera_de_fecha(self):
        context = build_tania_dynamic_context(today=date(2026, 10, 29))
        self.assertIn("próximo cumpleaños es el 24 de febrero de 2027", context)


if __name__ == "__main__":
    unittest.main()
