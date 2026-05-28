"""Tests de endpoints HTTP reales con FastAPI TestClient."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient


@pytest.fixture
def client(tmp_path, monkeypatch):
    """Crea un cliente con DB temporal aislada por test."""
    db_tmp = tmp_path / "fastapi_test.db"
    import nutricosto.db as db
    import nutricosto.web as web
    monkeypatch.setattr(db, "DB_PATH", db_tmp)
    monkeypatch.setattr(web, "_ULTIMA_RESOLUCION", {})
    return TestClient(web.app)


class TestRutaIndex:
    def test_get_index_devuelve_html_con_formulario(self, client):
        r = client.get("/")
        assert r.status_code == 200
        assert "text/html" in r.headers["content-type"]
        # Debe contener referencias clave del formulario
        assert "Matriz de insumos" in r.text
        assert "precio_saco_Maiz" in r.text
        assert "ca_p_ratio_min" in r.text
        assert "Caliza" in r.text


class TestRutaOptimizar:
    def test_post_optimizar_con_defaults(self, client):
        r = client.post("/optimizar", data={})
        assert r.status_code == 200
        # El resultado debe traer Z* y composicion
        assert "Costo optimo" in r.text
        assert "Composicion del lote" in r.text
        assert "OPTIMO" in r.text

    def test_post_optimizar_respeta_overrides_de_form(self, client):
        # Forzando masa=100 espero ver "por lote de 100 kg" en el HTML
        r = client.post("/optimizar", data={"masa": "100"})
        assert r.status_code == 200
        assert "100 kg" in r.text

    def test_post_optimizar_es_idempotente(self, client):
        r1 = client.post("/optimizar", data={})
        r2 = client.post("/optimizar", data={})
        assert r1.status_code == 200
        assert r2.status_code == 200
        # Misma entrada, misma salida (texto del costo aparece igual).
        import re
        z1 = re.search(r"S/\.\s*(\d+\.\d+)", r1.text)
        z2 = re.search(r"S/\.\s*(\d+\.\d+)", r2.text)
        assert z1 and z2
        assert z1.group(1) == z2.group(1)

    def test_post_optimizar_con_basura_cae_a_defaults(self, client):
        """Valores no numericos en el form no rompen el endpoint."""
        r = client.post("/optimizar", data={"pc_min": "abc", "masa": "xyz"})
        assert r.status_code == 200
        assert "OPTIMO" in r.text


class TestPersistenciaTandas:
    def test_guardar_tanda_y_listarla(self, client):
        client.post("/optimizar", data={})  # ata _ULTIMA_RESOLUCION
        r_guardar = client.post(
            "/tandas",
            data={"codigo": "API-TEST-001", "notas": "via TestClient"},
        )
        assert r_guardar.status_code == 200

        r_listar = client.get("/tandas")
        assert r_listar.status_code == 200
        assert "API-TEST-001" in r_listar.text

    def test_guardar_sin_resolver_antes_no_explota(self, client):
        """Si no se ha llamado /optimizar, /tandas debe devolver error controlado."""
        r = client.post("/tandas", data={"codigo": "FAIL", "notas": ""})
        assert r.status_code in (400, 404, 409, 422)


class TestSensibilidadViaHTTP:
    def test_polvillo_carisimo_via_http_cambia_la_mezcla(self, client):
        """Endurecer un precio via HTTP debe cambiar el HTML del resultado."""
        r_base = client.post("/optimizar", data={})
        r_alt = client.post(
            "/optimizar",
            data={"precio_saco_Polvillo": "500", "kg_saco_Polvillo": "50"},
        )
        assert r_base.status_code == 200
        assert r_alt.status_code == 200
        import re
        z_base = float(re.search(r"S/\.\s*(\d+\.\d+)", r_base.text).group(1))
        z_alt = float(re.search(r"S/\.\s*(\d+\.\d+)", r_alt.text).group(1))
        # Encarecer Polvillo no puede abaratar Z*; debe encarecerlo notoriamente.
        assert z_alt > z_base + 1.0
