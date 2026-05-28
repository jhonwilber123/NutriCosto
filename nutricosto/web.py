"""Servidor FastAPI de NutriCosto.

Rutas:
    GET  /                  Pagina de optimizacion (form + zona de resultado)
    POST /optimizar         Resuelve LP y devuelve fragmento HTML con resultado
    POST /tandas            Guarda la ultima tanda y devuelve toast HTML
    GET  /tandas            Listado completo
    GET  /tandas/{id}       Detalle de tanda
    POST /tandas/{id}/delete  Elimina y redirige
    GET  /analisis          Serie temporal de costos optimos
    GET  /api/tandas.json   Datos crudos para Chart.js
"""

from __future__ import annotations

from pathlib import Path

from fastapi import FastAPI, Form, HTTPException, Request
from fastapi.responses import HTMLResponse, JSONResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .db import borrar_tanda, detalle_tanda, guardar_tanda, listar_tandas
from .insumos import CATALOGO_INSUMOS, Insumo, ParametrosLote
from .modelo import resolver_simplex
from .sacos import plan_de_compra
from .solver import resolver_interior_point

BASE_DIR = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = BASE_DIR / "templates"
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(title="NutriCosto", version="1.0.0")
templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")


_ULTIMA_RESOLUCION: dict = {}


def _build_parametros(form: dict) -> ParametrosLote:
    """Reconstruye ParametrosLote desde un dict de form."""

    def f(name: str, default: float) -> float:
        try:
            return float(form.get(name, default))
        except (TypeError, ValueError):
            return default

    insumos = []
    for base in CATALOGO_INSUMOS:
        if base.limite_max_pct is None:
            limite = None
        else:
            limite_pct = form.get(f"limite_{base.nombre}")
            try:
                limite = float(limite_pct) / 100.0 if limite_pct is not None else base.limite_max_pct
            except (TypeError, ValueError):
                limite = base.limite_max_pct
        precio_saco = f(f"precio_saco_{base.nombre}", base.precio_saco)
        kg_saco = f(f"kg_saco_{base.nombre}", base.kg_por_saco)
        costo_kg = precio_saco / kg_saco if kg_saco > 0 else base.costo_kg
        pc = f(f"pc_{base.nombre}", base.proteina_cruda * 100.0) / 100.0
        em = f(f"em_{base.nombre}", base.energia_metabolizable)
        fc = f(f"fc_{base.nombre}", base.fibra_cruda * 100.0) / 100.0
        ca = f(f"ca_{base.nombre}", base.calcio * 100.0) / 100.0
        p = f(f"p_{base.nombre}", base.fosforo * 100.0) / 100.0
        insumos.append(
            Insumo(
                indice=base.indice,
                nombre=base.nombre,
                costo_kg=costo_kg,
                proteina_cruda=pc,
                energia_metabolizable=em,
                fibra_cruda=fc,
                calcio=ca,
                fosforo=p,
                limite_max_pct=limite,
                precio_saco=precio_saco,
                kg_por_saco=kg_saco,
            )
        )
    return ParametrosLote(
        masa_total_kg=f("masa", 50.0),
        fosvimin_kg=f("fosvimin", 0.625),
        sal_kg=f("sal", 0.25),
        pc_minima_kg=f("pc_min", 7.0),
        em_minima_mcal=f("em_min", 142.5),
        fc_minima_kg=f("fc_min", 2.5),
        ca_minima_kg=f("ca_min", 0.10),
        p_minima_kg=f("p_min", 0.08),
        ca_p_ratio_min=f("ca_p_ratio_min", 1.3),
        insumos=insumos,
    )


@app.get("/", response_class=HTMLResponse)
async def index(request: Request) -> HTMLResponse:
    return templates.TemplateResponse(
        "index.html",
        {
            "request": request,
            "insumos": CATALOGO_INSUMOS,
            "nav": "optimizar",
        },
    )


@app.post("/optimizar", response_class=HTMLResponse)
async def optimizar(request: Request) -> HTMLResponse:
    form = dict(await request.form())
    parametros = _build_parametros(form)
    solucion = resolver_simplex(parametros)
    verificacion = resolver_interior_point(parametros)

    _ULTIMA_RESOLUCION["parametros"] = parametros
    _ULTIMA_RESOLUCION["solucion"] = solucion

    composicion = []
    for ins in parametros.insumos:
        kg = solucion.asignaciones[ins.nombre]
        composicion.append(
            {
                "indice": ins.indice,
                "nombre": ins.nombre,
                "costo_kg": ins.costo_kg,
                "kg": kg,
                "pct": 100.0 * kg / solucion.masa_total_kg if solucion.masa_total_kg else 0,
                "parcial": kg * ins.costo_kg,
            }
        )

    sensibilidad = []
    for nombre in solucion.holguras:
        holgura = solucion.holguras.get(nombre) or 0.0
        dual = solucion.duales.get(nombre) or 0.0
        sensibilidad.append(
            {
                "nombre": nombre.replace("_", " "),
                "holgura": holgura,
                "dual": dual,
                "activa": abs(holgura) < 1e-4,
            }
        )

    delta_ip = abs(solucion.costo_total - verificacion.costo_total)

    try:
        lotes = max(int(float(form.get("lotes", 1))), 1)
    except (TypeError, ValueError):
        lotes = 1
    plan = plan_de_compra(parametros, solucion, lotes)

    return templates.TemplateResponse(
        "partials/resultado.html",
        {
            "request": request,
            "solucion": solucion,
            "composicion": composicion,
            "sensibilidad": sensibilidad,
            "delta_ip": delta_ip,
            "max_kg": max((c["kg"] for c in composicion), default=1) or 1,
            "plan": plan,
        },
    )


@app.post("/tandas", response_class=HTMLResponse)
async def crear_tanda(
    request: Request,
    codigo: str = Form(default=""),
    notas: str = Form(default=""),
) -> HTMLResponse:
    if "parametros" not in _ULTIMA_RESOLUCION:
        return HTMLResponse(
            '<div class="text-red-600 text-sm">Optimiza primero antes de guardar.</div>',
            status_code=400,
        )
    tanda_id = guardar_tanda(
        _ULTIMA_RESOLUCION["parametros"],
        _ULTIMA_RESOLUCION["solucion"],
        codigo=codigo or None,
        notas=notas or None,
    )
    return templates.TemplateResponse(
        "partials/toast.html",
        {"request": request, "tanda_id": tanda_id},
    )


@app.get("/tandas", response_class=HTMLResponse)
async def vista_tandas(request: Request) -> HTMLResponse:
    tandas = listar_tandas()
    return templates.TemplateResponse(
        "historico.html",
        {"request": request, "tandas": tandas, "nav": "historico"},
    )


@app.get("/tandas/{tanda_id}", response_class=HTMLResponse)
async def vista_detalle(request: Request, tanda_id: int) -> HTMLResponse:
    try:
        detalle = detalle_tanda(tanda_id)
    except ValueError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return templates.TemplateResponse(
        "detalle.html",
        {"request": request, "detalle": detalle, "nav": "historico"},
    )


@app.post("/tandas/{tanda_id}/delete")
async def eliminar_tanda(tanda_id: int) -> RedirectResponse:
    borrar_tanda(tanda_id)
    return RedirectResponse(url="/tandas", status_code=303)


@app.get("/analisis", response_class=HTMLResponse)
async def vista_analisis(request: Request) -> HTMLResponse:
    tandas = listar_tandas()
    return templates.TemplateResponse(
        "analisis.html",
        {"request": request, "tandas": tandas, "nav": "analisis"},
    )


@app.get("/api/tandas.json")
async def api_tandas() -> JSONResponse:
    tandas = listar_tandas()
    serie = [
        {
            "id": t["id"],
            "fecha": t["fecha"],
            "codigo": t["codigo"],
            "costo": t["costo_optimo"],
        }
        for t in reversed(tandas)
    ]
    return JSONResponse(serie)
