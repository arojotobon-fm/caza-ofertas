"""Pruebas de la ampliación del 22 nov 2026: Ktronix, Olímpica y Jumbo; Homecenter agrupado con Falabella."""
import json
import os
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
GRUPO = {"Alkosto": "colcomercio", "Ktronix": "colcomercio", "Alkomprar": "colcomercio",
         "Falabella": "falabella", "Homecenter": "falabella"}


def cargar(*ruta):
    with open(os.path.join(ROOT, *ruta), encoding="utf-8") as f:
        return json.load(f)


class ComerciosNuevos(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.v1 = cargar("data", "ofertas.json")["productos"]
        cls.pubs = cargar("data", "v2", "publicaciones.json")
        cls.comercios = {c["id"]: c for c in cargar("data", "v2", "comercios.json")["comercios"]}

    def test_nunca_se_compara_dentro_del_mismo_grupo(self):
        for r in self.v1:
            grupos = [GRUPO.get(c["tienda"], c["tienda"]) for c in r.get("comparativo", [])]
            self.assertEqual(len(grupos), len(set(grupos)), r["nombre"])

    def test_homecenter_en_el_grupo_de_falabella_y_no_admitido(self):
        h = self.comercios["homecenter"]
        self.assertEqual(h["grupo_empresarial"], "falabella")
        self.assertNotEqual(h["estado_admision"], "admitido")
        self.assertFalse(any(r["tienda"] == "Homecenter" for r in self.v1))

    def test_olimpica_y_jumbo_solo_validan_al_vendedor_propio(self):
        propio = {"olimpica": "OLIMPICA", "jumbo": "CENCOSUD - COLOMBIA"}
        for p in self.pubs:
            if p["comercio_id"] in propio and p["estado_validacion"] == "validado":
                vendedor = (p["validacion_vendedor"]["evidencia"].get("texto_listado") or "").upper()
                self.assertEqual(vendedor, propio[p["comercio_id"]], p["titulo"])

    def test_ficha_de_ktronix_con_excepcion_no_se_valida(self):
        ch = cargar("data", "v2", "chequeos", "ktronix-2026-11-22.json")
        malas = {p for p, f in ch["fichas"].items() if f.get("status") != 200 or not f.get("has_main") or f.get("banner_txt")
                 or f.get("banner_img") or f.get("seller_text") or f.get("special") or f.get("error")}
        self.assertTrue(malas)
        for r in self.v1:
            if r["tienda"] == "Ktronix" and r["link"].replace("https://www.ktronix.com", "") in malas:
                self.assertFalse(r.get("vendedor_validado_en"), r["nombre"])

    def test_cada_tienda_con_su_hora_real_del_mismo_dia(self):
        for r in self.v1:
            self.assertTrue(r["verificado"].startswith("2026-11-22T"), r["tienda"])


if __name__ == "__main__":
    unittest.main()
