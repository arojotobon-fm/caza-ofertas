"""Pruebas de identidades corporativas, validación por evidencia del canal y distribuidor autorizado (decisión 22 nov).
Garantizan que ningún vendedor externo, pendiente o no identificado llegue al Radar.
Ejecutar:  python3 -m unittest discover -s tests -v
"""
import copy
import json
import os
import subprocess
import sys
import tempfile
import unittest

ROOT = os.path.join(os.path.dirname(__file__), "..")
sys.path.insert(0, os.path.join(ROOT, "scripts"))
from validacion import (TIPOS_PERMITIDOS, cargar_identidades, clasificar_vendedor, elegibilidad_publica,  # noqa: E402
                        estado_publicacion, identidad_por_nombre, validar_por_canal)
from comparador import comparar_precios, comercios_independientes  # noqa: E402

HOY = "2026-11-22"
IDENT = cargar_identidades()
LIMPIA = {"fecha": HOY, "status": 200, "has_main": True, "banner_txt": "", "banner_img": "", "seller_text": None, "special": False}
CHEQUEO = os.path.join(ROOT, "data", "v2", "chequeos", "alkosto-2026-11-22.json")


def ficha(**cambios):
    f = dict(LIMPIA)
    f.update(cambios)
    return f


class IdentidadesExactas(unittest.TestCase):
    def test_razon_social_y_alias_documentados(self):
        for n in ["Colombiana de Comercio S.A.", "COLOMBIANA DE COMERCIO S.A.", "Alkosto", "ktronix", "Alkomprar",
                  "Corbeta S.A.", "Alkosto S.A."]:
            ident, _ = identidad_por_nombre(n, IDENT)
            self.assertIsNotNone(ident, n)
            self.assertEqual(ident["nit"], "890.900.943-1")

    def test_nunca_coincidencia_aproximada(self):
        for n in ["Alkosto Store", "Alkost", "Distribuidora Alkosto", "Ktronix Oficial", "Corbeta", "Comercio S.A.",
                  "Tienda Alkomprar Bogotá", "", None]:
            self.assertIsNone(identidad_por_nombre(n, IDENT)[0], n)


class ValidacionPorCanal(unittest.TestCase):
    def test_ficha_limpia_valida_con_nivel_fecha_fuente_y_revalidacion(self):
        v = validar_por_canal("alkosto", ficha(), IDENT, HOY)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("retailer", "validado"))
        self.assertEqual(v["nivel_evidencia"], "canal_corporativo")
        self.assertEqual(v["validado_en"], HOY)
        self.assertEqual(v["vendedor_real"]["nit"], "890.900.943-1")
        self.assertIn("contrato-compraventa", v["evidencia"]["canal"]["fuente"])
        self.assertNotIn("revalidar_antes_de", v)  # los 90 días pertenecen al contrato del canal, no a la ficha

    def test_ficha_de_otro_dia_no_se_reutiliza(self):
        vieja = ficha(fecha="2026-11-21")
        v = validar_por_canal("alkosto", vieja, IDENT, HOY)
        self.assertEqual(v["estado_validacion"], "pendiente")
        self.assertIn("fecha de actualización", v["motivo"])

    def test_otro_vendedor_queda_pendiente(self):
        for t in ["Vendido por TecnoShop SAS", "Vendedor: Importadora XYZ", "Proveedor: Samsung Colombia",
                  "Producto de aliado comercial", "Vendido y despachado por Alkosto Store"]:
            v = validar_por_canal("alkosto", ficha(seller_text=t), IDENT, HOY)
            self.assertEqual(v["estado_validacion"], "pendiente", t)

    def test_vendido_por_alias_de_la_misma_identidad_se_acepta(self):
        v = validar_por_canal("alkosto", ficha(seller_text="Vendido por Alkosto"), IDENT, HOY)
        self.assertEqual(v["estado_validacion"], "validado")

    def test_banner_principal_con_contenido_queda_pendiente(self):
        self.assertEqual(validar_por_canal("alkosto", ficha(banner_txt="Producto de un aliado"), IDENT, HOY)["estado_validacion"], "pendiente")
        self.assertEqual(validar_por_canal("alkosto", ficha(banner_img="/medias/aliado.png"), IDENT, HOY)["estado_validacion"], "pendiente")

    def test_reacondicionado_exhibicion_o_especial_va_a_revision_individual(self):
        casos = [ficha(special=True), ficha(h1="Celular X reacondicionado"), ficha(crumbs=["Inicio", "Exhibición"])]
        for f in casos:
            v = validar_por_canal("alkosto", f, IDENT, HOY)
            self.assertEqual(v["estado_validacion"], "pendiente")
            self.assertTrue(v.get("revision_individual"))
        v = validar_por_canal("alkosto", ficha(), IDENT, HOY, condicion_producto="no_nuevo")
        self.assertEqual(estado_publicacion(v, "no_nuevo")[0], "pendiente")

    def test_no_se_puede_determinar_queda_pendiente(self):
        for f in [None, {}, ficha(status=404), ficha(has_main=False), ficha(error="timeout")]:
            self.assertEqual(validar_por_canal("alkosto", f, IDENT, HOY)["estado_validacion"], "pendiente")

    def test_evidencia_vencida_obliga_a_revalidar(self):
        v = validar_por_canal("alkosto", ficha(fecha="2027-03-01"), IDENT, "2027-03-01")   # ficha del día, contrato vencido
        self.assertEqual(v["estado_validacion"], "pendiente")
        self.assertIn("canal", v["motivo"])

    def test_canal_sin_clausula_verificada_no_valida(self):
        # Ktronix y Alkomprar: cláusula verificada el 22 nov 2026. Homecenter tiene marketplace: sigue pendiente.
        for c in ["homecenter", "falabella", "exito"]:
            self.assertEqual(validar_por_canal(c, ficha(), IDENT, HOY)["estado_validacion"], "pendiente", c)
        for c in ["ktronix", "alkomprar"]:
            self.assertEqual(validar_por_canal(c, ficha(), IDENT, HOY)["estado_validacion"], "validado", c)


class DistribuidorAutorizado(unittest.TestCase):
    def test_nunca_automatico(self):
        v = clasificar_vendedor("falabella", "Distribuidor Oficial Colombia", "NINJA", HOY, "prueba", IDENT)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("distribuidor_autorizado", "pendiente"))

    def test_empresa_del_grupo_en_marketplace_ajeno_es_distribuidor_pendiente(self):
        v = clasificar_vendedor("falabella", "Alkosto", "SAMSUNG", HOY, "prueba", IDENT)
        self.assertEqual((v["tipo"], v["estado_validacion"]), ("distribuidor_autorizado", "pendiente"))
        self.assertFalse(elegibilidad_publica({"estado_validacion": "pendiente"}, v)[0])

    def test_sin_validacion_humana_no_es_elegible_aunque_se_marque_validado(self):
        v = {"tipo": "distribuidor_autorizado", "estado_validacion": "validado", "metodo": "x"}
        self.assertFalse(elegibilidad_publica({"estado_validacion": "validado"}, v)[0])
        v["validacion_humana"] = {"por": "Ana Marcela", "fecha": HOY}
        self.assertTrue(elegibilidad_publica({"estado_validacion": "validado"}, v)[0])


class GrupoUnico(unittest.TestCase):
    COM = {"alkosto": {"grupo_empresarial": "colcomercio"}, "ktronix": {"grupo_empresarial": "colcomercio"},
           "alkomprar": {"grupo_empresarial": "colcomercio"}, "falabella": {"grupo_empresarial": "falabella"}}

    def test_alkosto_ktronix_alkomprar_cuentan_como_un_comercio(self):
        self.assertEqual(comercios_independientes({"alkosto", "ktronix", "alkomprar"}, self.COM), 1)
        filas = comparar_precios([
            {"publicacion_id": "a", "comercio_id": "alkosto", "condicion": "contado", "monto": 100},
            {"publicacion_id": "k", "comercio_id": "ktronix", "condicion": "contado", "monto": 90},
            {"publicacion_id": "m", "comercio_id": "alkomprar", "condicion": "contado", "monto": 95}], self.COM)
        self.assertTrue(all(f["estado_comparacion"] == "sin_comparacion" for f in filas))


class MigracionDeEnsayo(unittest.TestCase):
    """Corre la migración completa en una carpeta temporal y revisa cada fila que podría llegar al Radar."""

    def correr(self, chequeo_path, fecha=HOY):
        out = tempfile.mkdtemp()
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "migrar_v1_a_v2.py"), "--salida", out,
                        "--chequeo", chequeo_path, "--fecha-verificacion", fecha], check=True, capture_output=True)
        L = lambda n: json.load(open(os.path.join(out, n), encoding="utf-8"))  # noqa: E731
        return L("publicaciones.json"), L("comparaciones.json"), L("productos.json")

    def filas_publicas(self, comps):
        return [f for c in comps for f in c["publica"]["filas"]]

    def test_ninguna_fila_publica_viene_de_vendedor_no_validado_o_externo(self):
        pubs, comps, _ = self.correr(CHEQUEO)
        idx = {p["id"]: p for p in pubs}
        filas = self.filas_publicas(comps)
        self.assertTrue(filas)
        for f in filas:
            p = idx[f["publicacion_id"]]
            v = p["validacion_vendedor"]
            self.assertEqual(p["estado_validacion"], "validado")
            self.assertEqual(v["estado_validacion"], "validado")
            self.assertIn(v["tipo"], TIPOS_PERMITIDOS - {"distribuidor_autorizado"})
            self.assertNotEqual(v["tipo"], "tercero_marketplace")
            self.assertTrue(p["elegibilidad_publica"]["elegible"])
            self.assertIn(v.get("nivel_evidencia"), {"publicacion", "canal_corporativo"})

    def test_referencias_en_revision_no_se_comparan_en_publico(self):
        _, comps, prods = self.correr(CHEQUEO)
        enrev = {p["id"] for p in prods if p["estado_referencia"] == "en_revision"}
        self.assertTrue(enrev)
        for c in comps:
            if c["producto_id"] in enrev:
                self.assertEqual(c["publica"]["filas"], [])

    def test_una_ficha_con_otro_vendedor_sale_del_radar(self):
        c = json.load(open(CHEQUEO, encoding="utf-8"))
        pubs0, comps0, _ = self.correr(CHEQUEO)
        idx0 = {p["id"]: p for p in pubs0}
        objetivo = next(idx0[f["publicacion_id"]] for f in self.filas_publicas(comps0)
                        if idx0[f["publicacion_id"]]["comercio_id"] == "alkosto")
        path = objetivo["url"].replace("https://www.alkosto.com", "")
        for cambio in [{"seller_text": "Vendido por Importadora Andina"}, {"banner_txt": "Producto de aliado"}, {"special": True}, {"status": 500}]:
            c2 = copy.deepcopy(c)
            c2["fichas"][path].update(cambio)
            tmp = tempfile.NamedTemporaryFile("w", suffix=".json", delete=False, encoding="utf-8")
            json.dump(c2, tmp, ensure_ascii=False)
            tmp.close()
            pubs, comps, _ = self.correr(tmp.name)
            p = next(x for x in pubs if x["id"] == objetivo["id"])
            self.assertEqual(p["estado_validacion"], "pendiente", cambio)
            self.assertNotIn(objetivo["id"], {f["publicacion_id"] for f in self.filas_publicas(comps)}, cambio)

    def test_chequeo_de_otro_dia_no_llega_al_radar(self):
        for fecha in ["2026-11-23", "2026-12-15"]:
            pubs, comps, _ = self.correr(CHEQUEO, fecha)
            idx = {p["id"]: p for p in pubs}
            self.assertEqual([f for f in self.filas_publicas(comps) if idx[f["publicacion_id"]]["comercio_id"] == "alkosto"], [], fecha)
            self.assertTrue(all(p["estado_validacion"] == "pendiente" for p in pubs if p["comercio_id"] == "alkosto"))

    def test_sin_chequeo_alkosto_sigue_pendiente(self):
        out = tempfile.mkdtemp()
        subprocess.run([sys.executable, os.path.join(ROOT, "scripts", "migrar_v1_a_v2.py"), "--salida", out], check=True, capture_output=True)
        pubs = json.load(open(os.path.join(out, "publicaciones.json"), encoding="utf-8"))
        self.assertTrue(all(p["estado_validacion"] == "pendiente" for p in pubs if p["comercio_id"] == "alkosto"))


if __name__ == "__main__":
    unittest.main()
