import json, os, sys, unittest
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from historial_diario import precio_vtex, precio_falabella, limpio


class TestHistorialDiario(unittest.TestCase):
    def test_vtex_solo_vendedor_de_la_tienda(self):
        data = [{"items": [{"sellers": [
            {"sellerId": "17306", "commertialOffer": {"Price": 1689000, "ListPrice": 2799000, "AvailableQuantity": 5}},
            {"sellerId": "1", "commertialOffer": {"Price": 579900, "ListPrice": 799900, "AvailableQuantity": 3}}]}]}]
        self.assertEqual(precio_vtex(json.dumps(data)), (579900, 799900, None))

    def test_vtex_sin_stock_de_la_tienda(self):
        data = [{"items": [{"sellers": [{"sellerId": "1", "commertialOffer": {"Price": 0, "ListPrice": 0, "AvailableQuantity": 0}}]}]}]
        self.assertIsNone(precio_vtex(json.dumps(data)))

    def test_falabella(self):
        pd = {"variants": [{"prices": [{"type": "cmrPrice", "price": ["369.900"]}, {"type": "internetPrice", "price": ["399.900"]},
                                       {"type": "normalPrice", "price": ["599.900"], "crossed": True}]}]}
        html = '<script id="__NEXT_DATA__" type="application/json">' + json.dumps({"props": {"pageProps": {"productData": pd}}}) + "</script>"
        self.assertEqual(precio_falabella(html), (399900, 599900, 369900))

    def test_clave_del_enlace(self):
        self.assertEqual(limpio("https://www.Jumbo.com/x/p/?a=1"), "https://www.jumbo.com/x/p")


if __name__ == "__main__":
    unittest.main()
