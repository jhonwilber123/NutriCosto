"""Capa de persistencia SQLite para tandas de produccion.

Esquema:
  tandas              ── cabecera (fecha, parametros, costo optimo)
  tanda_precios       ── precios por insumo usados en la tanda
  tanda_composicion   ── composicion optima resultante (kg + costo parcial)

SQLite se eligio por cero configuracion. Para escalar a PostgreSQL basta
sustituir el `connect` por psycopg2/asyncpg manteniendo el mismo esquema.
"""

from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Iterator

from .insumos import ParametrosLote
from .modelo import SolucionLP

DB_PATH = Path(__file__).resolve().parent.parent / "data" / "nutricosto.db"


SCHEMA = """
CREATE TABLE IF NOT EXISTS tandas (
    id              INTEGER PRIMARY KEY AUTOINCREMENT,
    fecha           TEXT    NOT NULL,
    codigo          TEXT,
    notas           TEXT,
    masa_kg         REAL    NOT NULL,
    fosvimin_kg     REAL    NOT NULL,
    sal_kg          REAL    NOT NULL,
    pc_min_kg       REAL    NOT NULL,
    em_min_mcal     REAL    NOT NULL,
    techo_nsc       REAL    NOT NULL DEFAULT 0.70,
    estado_solver   TEXT    NOT NULL,
    costo_optimo    REAL    NOT NULL,
    solver          TEXT    NOT NULL
);

CREATE TABLE IF NOT EXISTS tanda_precios (
    tanda_id         INTEGER NOT NULL,
    insumo           TEXT    NOT NULL,
    costo_kg         REAL    NOT NULL,
    limite_max_pct   REAL,
    PRIMARY KEY (tanda_id, insumo),
    FOREIGN KEY (tanda_id) REFERENCES tandas(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS tanda_composicion (
    tanda_id        INTEGER NOT NULL,
    insumo          TEXT    NOT NULL,
    kg              REAL    NOT NULL,
    costo_parcial   REAL    NOT NULL,
    PRIMARY KEY (tanda_id, insumo),
    FOREIGN KEY (tanda_id) REFERENCES tandas(id) ON DELETE CASCADE
);

CREATE INDEX IF NOT EXISTS idx_tandas_fecha ON tandas(fecha);
"""


def _migrate(conn: sqlite3.Connection) -> None:
    """Migraciones idempotentes para bases creadas con esquemas previos."""
    cols = {row[1] for row in conn.execute("PRAGMA table_info(tanda_precios);")}
    if "limite_max_pct" not in cols:
        conn.execute("ALTER TABLE tanda_precios ADD COLUMN limite_max_pct REAL;")


@dataclass
class TandaRegistrada:
    id: int
    fecha: str
    codigo: str | None
    costo_optimo: float


@contextmanager
def conexion(db_path: Path | str = DB_PATH) -> Iterator[sqlite3.Connection]:
    """Context manager que abre/cierra la conexion y aplica el esquema."""
    path = Path(db_path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(str(path))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON;")
    conn.executescript(SCHEMA)
    _migrate(conn)
    try:
        yield conn
        conn.commit()
    except Exception:
        conn.rollback()
        raise
    finally:
        conn.close()


def guardar_tanda(
    parametros: ParametrosLote,
    solucion: SolucionLP,
    codigo: str | None = None,
    notas: str | None = None,
    db_path: Path | str = DB_PATH,
) -> int:
    """Inserta cabecera, precios y composicion. Devuelve el id de la tanda."""

    fecha = datetime.now().isoformat(timespec="seconds")

    maiz = next((i for i in parametros.insumos if i.nombre == "Maiz"), None)
    techo_nsc_legado = maiz.limite_max_pct if maiz and maiz.limite_max_pct else 0.70

    with conexion(db_path) as conn:
        cur = conn.execute(
            """
            INSERT INTO tandas (
                fecha, codigo, notas,
                masa_kg, fosvimin_kg, sal_kg,
                pc_min_kg, em_min_mcal, techo_nsc,
                estado_solver, costo_optimo, solver
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
            """,
            (
                fecha,
                codigo,
                notas,
                parametros.masa_total_kg,
                parametros.fosvimin_kg,
                parametros.sal_kg,
                parametros.pc_minima_kg,
                parametros.em_minima_mcal,
                techo_nsc_legado,
                solucion.estado,
                float(solucion.costo_total),
                solucion.solver,
            ),
        )
        tanda_id = cur.lastrowid

        conn.executemany(
            "INSERT INTO tanda_precios (tanda_id, insumo, costo_kg, limite_max_pct) VALUES (?, ?, ?, ?);",
            [(tanda_id, ins.nombre, ins.costo_kg, ins.limite_max_pct) for ins in parametros.insumos],
        )
        conn.executemany(
            "INSERT INTO tanda_composicion (tanda_id, insumo, kg, costo_parcial) VALUES (?, ?, ?, ?);",
            [
                (
                    tanda_id,
                    ins.nombre,
                    float(solucion.asignaciones[ins.nombre]),
                    float(solucion.asignaciones[ins.nombre]) * ins.costo_kg,
                )
                for ins in parametros.insumos
            ],
        )
    return tanda_id


def listar_tandas(db_path: Path | str = DB_PATH) -> list[dict]:
    with conexion(db_path) as conn:
        filas = conn.execute(
            "SELECT id, fecha, codigo, notas, masa_kg, pc_min_kg, em_min_mcal, "
            "techo_nsc, estado_solver, costo_optimo "
            "FROM tandas ORDER BY id DESC;"
        ).fetchall()
    return [dict(f) for f in filas]


def detalle_tanda(tanda_id: int, db_path: Path | str = DB_PATH) -> dict:
    with conexion(db_path) as conn:
        cabecera = conn.execute(
            "SELECT * FROM tandas WHERE id = ?;", (tanda_id,)
        ).fetchone()
        if cabecera is None:
            raise ValueError(f"Tanda {tanda_id} no existe")
        precios = conn.execute(
            "SELECT insumo, costo_kg FROM tanda_precios WHERE tanda_id = ?;",
            (tanda_id,),
        ).fetchall()
        composicion = conn.execute(
            "SELECT insumo, kg, costo_parcial FROM tanda_composicion WHERE tanda_id = ?;",
            (tanda_id,),
        ).fetchall()
    return {
        "cabecera": dict(cabecera),
        "precios": [dict(p) for p in precios],
        "composicion": [dict(c) for c in composicion],
    }


def borrar_tanda(tanda_id: int, db_path: Path | str = DB_PATH) -> None:
    with conexion(db_path) as conn:
        conn.execute("DELETE FROM tandas WHERE id = ?;", (tanda_id,))
