import unittest
from scripts.captura_selectiva import validar_url, buscar_producto, extraer_codigo


class CapturaSelectivaTests(unittest.TestCase):
    def test_acepta_producto_alkosto(self):
        self.assertEqual(validar_url("https://www.alkosto.com/p/producto"), "https://www.alkosto.com/p/producto")

    def test_rechaza_otro_dominio(self):
        with self.assertRaises(ValueError):
            validar_url("https://ejemplo.com/p/producto")

    def test_rechaza_home(self):
        with self.assertRaises(ValueError):
            validar_url("https://www.alkosto.com/")

    def test_reconoce_producto_schema(self):
        producto = buscar_producto([{"@type": "Product", "name": "Estufa"}])
        self.assertEqual(producto["name"], "Estufa")

    def test_extrae_codigo_visible(self):
        self.assertEqual(extraer_codigo(["Código", "ABBA-1234"]), "ABBA-1234")


if __name__ == "__main__":
    unittest.main()
