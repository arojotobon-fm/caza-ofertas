import os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from taxonomia import clasificar


class TestTaxonomia(unittest.TestCase):
    def test_ajenos_se_ocultan(self):
        for n in ["IBUPROFENO MK 800MG CAJAX30TABLETAS", "Galletas gullon choco tablet", "Bebedero Portátil 500ml",
                  "Casa De Muñecas Villa Armable 275 Piezas", "Oferta destacada 🔥"]:
            self.assertIsNone(clasificar(n, "Tecnología")[0], n)

    def test_categorias_aprobadas(self):
        casos = {"Celular | Galaxy S25 FE | 5G | 128 GB": "Celulares y accesorios",
                 "Portátil IdeaPad Slim 3 Ryzen 7": "Computación",
                 "Televisor 55 pulgadas 4K UHD QNED": "TV y video",
                 "Consola de videojuegos PlayStation 5 Slim": "Consolas",
                 "Audífonos bluetooth WH-CH520": "Audio",
                 "Reloj Forerunner 255 Graphite": "Smartwatch y anillos",
                 "Freidora de Aire 6 L": "Electrodomésticos de cocina",
                 "Secador de cabello D31A-110F": "Tecnobelleza",
                 "Aspiradora Sin Bolsa 2200W 2L Boquilla Para Mascotas": "Aspirado y limpieza",
                 "Robot Aspirador D30 Ultra": "Smart home"}
        for n, sub in casos.items():
            self.assertEqual(clasificar(n)[1], sub, n)


if __name__ == "__main__":
    unittest.main()
