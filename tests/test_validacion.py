"""Pruebas de validación de vendedores, publicaciones pendientes y condiciones de pago.
Ejecutar:  python3 -m unittest discover -s tests -v
"""
import json
import os
import sys
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validacion import clasificar_vendedor, elegibilidad_publica, estado_publicacion  # noqa: E402
from comparador import comparar_precios  # noqa: E402

F = "2026-11-21T22:40:00-05:00"
SRC = "prueba"
COMERCIOS = {"alkosto": {"grupo_empresarial": "colcomercio"}, "falabella": {"grupo_empresarial": "falabella"},
             "exito": {"grupo_empresarial": "grupo-exito"}, "ktronix": {"grupo_empresarial": "colcomercio"}}


class ValidacionVendedores(unittest.TestCase):
    def test_coincidencia_exacta_valida_con_evidencia_y_fecha(self):
        v = clasificar_vendedor("falabella", "Falabella", "SONY", F, SRC)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("retailer", "validado"))
        self.assertEqual(v["validado_en"], F)
        self.assertEqual(v["evidencia"], {"texto_listado": "Falabella", "fuente": SRC, "fecha": F})

    def test_normaliza_tildes_y_mayusculas(self):
        self.assertEqual(clasificar_vendedor("exito", " ÉXITO ", "", F, SRC)["estado_validacion"], "validado")

    def test_coincidencia_aproximada_no_basta(self):
        for nombre in ("Falabella Colombia SAS", "falabella.com", "Tienda Falabella Bogotá"):
            v = clasificar_vendedor("falabella", nombre, "", F, SRC)
            self.assertEqual(v["estado_validacion"], "pendiente", nombre)
            self.assertIsNone(v["validado_en"])

    def test_nombre_de_otro_comercio_no_valida(self):
        # 'Exito' vendiendo dentro de Falabella no es el comercio donde está publicado
        self.assertNotEqual(clasificar_vendedor("falabella", "Exito", "", F, SRC)["estado_validacion"], "validado")

    def test_alkosto_sin_vendedor_queda_pendiente(self):
        v = clasificar_vendedor("alkosto", None, "NINJA", F, SRC)
        self.assertEqual(v["estado_validacion"], "pendiente")
        self.assertIsNone(v["tipo"])

    def test_tienda_oficial_requiere_validacion_humana(self):
        for nombre, marca in (("Sony Colombia", "SONY"), ("Tienda Oficial Dreame", "DREAME")):
            v = clasificar_vendedor("falabella", nombre, marca, F, SRC)
            self.assertEqual((v["tipo"], v["estado_validacion"]), ("tienda_oficial_fabricante", "pendiente"))

    def test_marca_ajena_en_el_nombre_no_es_tienda_oficial(self):
        v = clasificar_vendedor("exito", "Tecno optima", "SAMSUNG", F, SRC)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("tercero_marketplace", "rechazado"))

    def test_tercero_marketplace_rechazado(self):
        v = clasificar_vendedor("exito", "Ocnatech", "SILVER CREST", F, SRC)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("tercero_marketplace", "rechazado"))


class PublicacionesYElegibilidad(unittest.TestCase):
    def test_pendiente_no_es_elegible(self):
        v = clasificar_vendedor("alkosto", None, "", F, SRC)
        estado, _ = estado_publicacion(v)
        ok, motivos = elegibilidad_publica({"estado_validacion": estado}, v)
        self.assertEqual(estado, "pendiente")
        self.assertFalse(ok)
        self.assertIn("vendedor pendiente", motivos)

    def test_validado_es_elegible(self):
        v = clasificar_vendedor("falabella", "Falabella", "", F, SRC)
        estado, _ = estado_publicacion(v)
        self.assertEqual(elegibilidad_publica({"estado_validacion": estado}, v), (True, []))

    def test_producto_no_nuevo_se_rechaza_aunque_el_vendedor_sea_valido(self):
        v = clasificar_vendedor("falabella", "Falabella", "", F, SRC)
        self.assertEqual(estado_publicacion(v, "no_nuevo")[0], "rechazado")

    def test_tienda_oficial_pendiente_no_es_elegible(self):
        v = clasificar_vendedor("falabella", "Sony Colombia", "SONY", F, SRC)
        estado, _ = estado_publicacion(v)
        self.assertFalse(elegibilidad_publica({"estado_validacion": estado}, v)[0])


class CondicionesDePago(unittest.TestCase):
    def test_cada_condicion_se_compara_aparte(self):
        ofertas = [
            {"publicacion_id": "a", "comercio_id": "alkosto", "condicion": "tarjeta", "monto": 300},
            {"publicacion_id": "a", "comercio_id": "alkosto", "condicion": "contado", "monto": 400},
            {"publicacion_id": "f", "comercio_id": "falabella", "condicion": "contado", "monto": 410},
            {"publicacion_id": "e", "comercio_id": "exito", "condicion": "financiado", "monto": 350},
        ]
        contado = comparar_precios(ofertas, COMERCIOS, "contado")
        self.assertEqual(sorted(x["monto"] for x in contado), [400, 410])
        self.assertEqual({x["referencia"] for x in contado}, {400, 410})
        self.assertTrue(all(x["condicion"] == "contado" for x in contado))
        # una sola tienda con tarjeta: no hay comparación posible en esa condición
        self.assertTrue(all(x["referencia"] is None for x in comparar_precios(ofertas, COMERCIOS, "tarjeta")))


class DatosMigrados(unittest.TestCase):
    """Controles sobre data/v2 generado por scripts/migrar_v1_a_v2.py."""

    @classmethod
    def setUpClass(cls):
        d = lambda n: json.load(open(os.path.join(ROOT, "data", "v2", n), encoding="utf-8"))  # noqa: E731
        cls.pubs = {p["id"]: p for p in d("publicaciones.json")}
        cls.comps = d("comparaciones.json")
        cls.prods = d("productos.json")
        cls.vend = d("vendedores.json")
        cls.inf = d("informe_migracion.json")

    def test_sin_errores_de_migracion_y_sin_perdida(self):
        self.assertEqual(self.inf["errores_verificacion"], [])
        self.assertEqual(self.inf["ids_v1_mapeados"], self.inf["registros_v1"])

    def test_ninguna_publicacion_pendiente_o_rechazada_en_comparaciones_publicas(self):
        for c in self.comps:
            for f in c["publica"]["filas"]:
                self.assertTrue(self.pubs[f["publicacion_id"]]["elegibilidad_publica"]["elegible"], f["publicacion_id"])
                self.assertEqual(self.pubs[f["publicacion_id"]]["estado_validacion"], "validado")

    def test_comparaciones_tecnicas_pueden_incluir_pendientes_pero_marcadas(self):
        for c in self.comps:
            self.assertEqual(c["tecnica"]["estado"], "candidata")
            for pid in c["tecnica"]["pendientes"]:
                self.assertFalse(self.pubs[pid]["elegibilidad_publica"]["elegible"])

    def test_comparaciones_publicas_solo_contado_y_sin_etiquetas(self):
        for c in self.comps:
            self.assertEqual(c["condicion"], "contado")
            for f in c["publica"]["filas"]:
                self.assertEqual(f["condicion"], "contado")
                self.assertIsNone(f["etiqueta"])

    def test_dos_comercios_es_limitada(self):
        for c in self.comps:
            n = c["publica"]["comercios_independientes"]
            if c["publica"]["filas"]:
                self.assertEqual(c["publica"]["estado_comparacion"], {1: "sin_comparacion", 2: "limitada"}.get(n, "completa"))

    def test_vendedores_validados_tienen_evidencia_metodo_y_fecha(self):
        for v in self.vend:
            if v["estado_validacion"] == "validado":
                self.assertEqual(v["metodo_validacion"], "automatica_coincidencia_exacta")
                self.assertTrue(v["validado_en"])
                self.assertTrue(v["evidencias"])
            if v["tipo"] == "tienda_oficial_fabricante":
                self.assertEqual(v["estado_validacion"], "pendiente")
            if v["tipo"] == "tercero_marketplace":
                self.assertEqual(v["estado_validacion"], "rechazado")

    def test_alkosto_sin_vendedor_pendiente(self):
        for p in self.pubs.values():
            if p["comercio_id"] == "alkosto":
                self.assertEqual(p["estado_validacion"], "pendiente")

    def test_ninguna_referencia_verificada_sin_persona(self):
        for p in self.prods:
            self.assertIn(p["estado_referencia"], ("sin_verificar", "agrupada_automatica"))
            self.assertIsNone(p["verificacion_humana"])


if __name__ == "__main__":
    unittest.main()
