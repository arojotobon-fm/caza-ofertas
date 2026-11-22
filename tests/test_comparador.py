"""Pruebas del comparador v1. Ejecutar:  python3 -m unittest discover -s tests -v"""
import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "scripts"))
from normalizar import canonical_brand, model_codes, specs  # noqa: E402
from comparador import agrupar, comparar_precios, comercios_independientes, evaluar_par  # noqa: E402

COMERCIOS = {
    "alkosto": {"grupo_empresarial": "colcomercio"},
    "ktronix": {"grupo_empresarial": "colcomercio"},
    "alkomprar": {"grupo_empresarial": "colcomercio"},
    "falabella": {"grupo_empresarial": "falabella"},
    "exito": {"grupo_empresarial": "grupo-exito"},
    "olimpica": {"grupo_empresarial": "olimpica"},
}


def pub(id, nombre, marca="", categoria="Tecnología"):
    return {"id": id, "marca": canonical_brand(marca, nombre), "codigos": model_codes(nombre),
            "specs": specs(nombre), "categoria": categoria}


class Normalizacion(unittest.TestCase):
    def test_marca_alias(self):
        self.assertEqual(canonical_brand("BLACK & DECKER", "Freidora"), "BLACK+DECKER")
        self.assertEqual(canonical_brand("", "Freidora de Aire BLACK+DECKER 4.2 Litros"), "BLACK+DECKER")

    def test_codigos_sin_unidades_ni_cpu(self):
        c = model_codes("Portátil Lenovo IdeaPad 3 15ABA7 Ryzen 5 5625U 8GB 512GB 15.6 pulgadas")
        self.assertIn("15ABA7", c)
        self.assertNotIn("5625U", c)      # procesador, no referencia
        self.assertNotIn("512GB", c)      # unidad

    def test_procesador_intel_core_serie_100(self):
        self.assertNotIn("100U", model_codes("Portátil HP Intel Core 3 100U 8GB RAM 512GB"))

    def test_specs(self):
        s = specs("Portátil HP 15 Intel Core i5 16GB RAM 512GB SSD 15.6\"")
        self.assertEqual(s["ram_gb"], 16)
        self.assertEqual(s["almacenamiento_gb"], 512)


class Coincidencias(unittest.TestCase):
    def test_mismo_codigo_exacto(self):
        a = pub("a", "Licuadora NINJA Profesional BL610 Negro", "NINJA", "Electrodomésticos")
        b = pub("b", "Licuadora Ninja Professional BL610", "NINJA", "Electrodomésticos")
        self.assertEqual(evaluar_par(a, b)[0], "exacta")

    def test_misma_marca_y_procesador_no_es_el_mismo_portatil(self):
        a = pub("a", "Portátil Lenovo IdeaPad Slim 3 Ryzen 5 7520U 8GB RAM 512GB", "LENOVO")
        b = pub("b", "Portátil Lenovo LOQ Ryzen 5 7520U 16GB RAM 512GB", "LENOVO")
        self.assertEqual(evaluar_par(a, b)[0], "descartada")

    def test_mismo_modelo_distinta_ram_se_descarta(self):
        a = pub("a", "Portátil ASUS Vivobook X1504VA 8GB RAM 512GB", "ASUS")
        b = pub("b", "Portátil ASUS Vivobook X1504VA 16GB RAM 512GB", "ASUS")
        estado, motivo = evaluar_par(a, b)
        self.assertEqual(estado, "descartada")
        self.assertIn("ram_gb", motivo)

    def test_televisor_distinto_tamano(self):
        a = pub("a", "Televisor SAMSUNG 50 pulgadas Crystal UHD UN50DU7000", "SAMSUNG")
        b = pub("b", "Televisor SAMSUNG 55 pulgadas Crystal UHD UN55DU7000", "SAMSUNG")
        self.assertEqual(evaluar_par(a, b)[0], "descartada")

    def test_combo_no_es_igual_al_producto_solo(self):
        a = pub("a", "Televisor LG 58\" 58NU850 UHD", "LG")
        b = pub("b", "Televisor LG 58\" 58NU850 UHD + Barra de sonido", "LG")
        self.assertEqual(evaluar_par(a, b)[0], "descartada")

    def test_sufijo_regional_queda_candidato(self):
        a = pub("a", "Freidora de Aire NINJA Pro 4.7 Litros AF141LAA Negro", "NINJA", "Electrodomésticos")
        b = pub("b", "Freidora de aire Pro 4.7 Litros AF141", "NINJA", "Electrodomésticos")
        self.assertEqual(evaluar_par(a, b)[0], "candidata")

    def test_marca_distinta(self):
        a = pub("a", "Audífonos XYZ123 Bluetooth", "SONY")
        b = pub("b", "Audífonos XYZ123 Bluetooth", "JBL")
        self.assertEqual(evaluar_par(a, b)[0], "descartada")

    def test_agrupar_no_mezcla_tamanos(self):
        ps = [pub("1", "Televisor TCL 50\" QLED 50C655", "TCL"), pub("2", "TV TCL 50 pulgadas 50C655 QLED", "TCL"),
              pub("3", "Televisor TCL 55\" QLED 55C655", "TCL")]
        grupos, _ = agrupar(ps)
        self.assertIn(sorted(["1", "2"]), [sorted(g) for g in grupos])
        self.assertIn(["3"], grupos)


class ComerciosYPrecios(unittest.TestCase):
    def test_mismo_grupo_cuenta_una_vez(self):
        self.assertEqual(comercios_independientes(["alkosto", "ktronix", "alkomprar"], COMERCIOS), 1)
        self.assertEqual(comercios_independientes(["alkosto", "ktronix", "falabella", "exito"], COMERCIOS), 3)

    def test_tarjeta_no_se_compara_con_contado(self):
        ofertas = [
            {"publicacion_id": "p1", "comercio_id": "alkosto", "condicion": "tarjeta", "monto": 329910},
            {"publicacion_id": "p1", "comercio_id": "alkosto", "condicion": "contado", "monto": 399900},
            {"publicacion_id": "p2", "comercio_id": "exito", "condicion": "contado", "monto": 399500},
        ]
        r = comparar_precios(ofertas, COMERCIOS, "contado")
        self.assertEqual({x["monto"] for x in r}, {399900, 399500})   # el precio con tarjeta no entra
        self.assertTrue(all(x["estado_comparacion"] == "limitada" for x in r))

    def test_comparacion_completa_con_tres_grupos(self):
        ofertas = [
            {"publicacion_id": "a", "comercio_id": "alkosto", "condicion": "contado", "monto": 100},
            {"publicacion_id": "k", "comercio_id": "ktronix", "condicion": "contado", "monto": 90},
            {"publicacion_id": "f", "comercio_id": "falabella", "condicion": "contado", "monto": 120},
            {"publicacion_id": "e", "comercio_id": "exito", "condicion": "contado", "monto": 130},
        ]
        r = {x["publicacion_id"]: x for x in comparar_precios(ofertas, COMERCIOS)}
        self.assertEqual(r["k"]["comercios_independientes"], 3)
        self.assertEqual(r["k"]["estado_comparacion"], "completa")
        self.assertEqual(r["k"]["referencia"], 125)       # mediana de Falabella y Éxito, sin contar Alkosto (mismo grupo)

    def test_dos_comercios_del_mismo_grupo_no_son_comparacion(self):
        ofertas = [
            {"publicacion_id": "a", "comercio_id": "alkosto", "condicion": "contado", "monto": 100},
            {"publicacion_id": "k", "comercio_id": "ktronix", "condicion": "contado", "monto": 95},
        ]
        r = comparar_precios(ofertas, COMERCIOS)
        self.assertTrue(all(x["estado_comparacion"] == "sin_comparacion" and x["referencia"] is None for x in r))


if __name__ == "__main__":
    unittest.main()
