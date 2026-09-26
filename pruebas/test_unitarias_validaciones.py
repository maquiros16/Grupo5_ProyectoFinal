import unittest
from solucion.validaciones import ErrorValidacion, validar_carne, validar_nombre, validar_correo, validar_estado


class ValidacionesTest(unittest.TestCase):
    # Comprueba carné, límites y espacios.
    def test_rf02_carne_limites_y_espacios(self):
        for valor in ("", "A12345678", "A1234567890", "A123 56789", "A12345678!", None, 1234567890):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                validar_carne(valor)
        self.assertEqual(validar_carne(" A123456789 "), "A123456789")
        self.assertEqual(validar_carne("0000000001"), "0000000001")

    # Comprueba nombre mínimo.
    def test_rf02_nombre_minimo(self):
        for valor in ("", "   ", "a b", "\ta\nb", None):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                validar_nombre(valor)
        self.assertEqual(validar_nombre("  A b c  "), "A b c")
        self.assertEqual(validar_nombre("  María Ñúñez "), "María Ñúñez")

    # Comprueba correo segun enunciado.
    def test_rf02_correo_segun_enunciado(self):
        for valor in ("", "abc", "a@b", "a@@b.c", "a.b@c", None):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                validar_correo(valor)
        self.assertEqual(validar_correo(" a@b.c "), "a@b.c")
        # El documento solo exige un @ y un punto posterior: no imponer otra política.
        self.assertEqual(validar_correo("@."), "@.")

    # Comprueba estado.
    def test_rf11_estado(self):
        self.assertEqual(validar_estado(" inactivo "), "inactivo")
        for valor in ("Activo", "cancelado", "", None):
            with self.subTest(valor=valor), self.assertRaises(ErrorValidacion):
                validar_estado(valor)
