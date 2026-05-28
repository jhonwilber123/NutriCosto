# NutriCosto

Motor de **Programacion Lineal** para la formulacion automatica de alimento balanceado destinado a toros de engorde en el Altiplano peruano (Puno, > 3,800 m.s.n.m.).

Implementa el **plan maestro** del curso de Investigacion de Operaciones 2026-I: minimiza el costo de adquisicion de insumos sujeto a restricciones biologicas (proteina, energia), tecnicas (masa fija, prescripciones veterinarias) y geograficas (techo de carbohidratos no estructurales por riesgo de Sindrome Ascitico Bovino).

## Modelo

```
Minimizar  Z = 1.35 x1 + 1.06 x2 + 1.38 x3 + 1.92 x4 + 1.90 x5 + 8.00 x6 + 0.56 x7

sujeto a:
    x1 + x2 + x3 + x4 + x5 + x6 + x7 = 100         (masa fija del lote)
    x6 = 1.25                                       (Fosvimin, prescripcion)
    x7 = 0.50                                       (sal, homeostasis)
    0.08 x1 + 0.13 x2 + 0.15 x3 + 0.46 x4 + 0.36 x5 >= 14.0   (PC)
    3.10 x1 + 2.80 x2 + 2.50 x3 + 2.90 x4 + 2.60 x5 >= 285.0  (EM)
    x1 <= 70                                        (techo NSC 70%)
    x_i >= 0
```

| Var | Insumo   | Costo S/. /kg |
|----:|----------|---------------|
| x1  | Maiz     | 1.35          |
| x2  | Polvillo | 1.06          |
| x3  | Afrecho  | 1.38          |
| x4  | Soya     | 1.92          |
| x5  | Pasta    | 1.90          |
| x6  | Fosvimin | 8.00          |
| x7  | Sal      | 0.56          |

## Arquitectura

```
NutriCosto/
├── main.py                  # CLI con argparse
├── app.py                   # UI interactiva (Streamlit)
├── requirements.txt
├── data/
│   └── nutricosto.db        # SQLite (autogenerado al guardar la primera tanda)
└── nutricosto/
    ├── insumos.py           # catalogo y restricciones parametrizadas
    ├── modelo.py            # LP con PuLP (Simplex CBC)
    ├── solver.py            # verificacion con SciPy HiGHS (Interior Point)
    ├── reporte.py           # tablas, sensibilidad, verificacion cruzada
    └── db.py                # persistencia SQLite de tandas
```

El motor resuelve el LP con dos metodos independientes:

1. **Simplex (CBC)** via PuLP — solucion primaria, expone holguras y precios sombra.
2. **Interior Point (HiGHS)** via SciPy — verificacion cruzada de robustez numerica.

## Instalacion

```powershell
pip install -r requirements.txt
```

## Despliegue en Render

La aplicacion incluye los archivos necesarios para ser desplegada como **Web Service** en Render usando el entorno `Python 3`.
- **Build Command:** `pip install -r requirements.txt`
- **Start Command:** `streamlit run app.py --server.port $PORT --server.address 0.0.0.0`

> **Nota sobre base de datos:** El despliegue gratuito de Render utiliza almacenamiento efimero. Para mantener el historial de tandas, es recomendable usar un "Persistent Disk" o configurar una conexion a PostgreSQL en `nutricosto/db.py`.

## Uso

### Aplicacion interactiva (recomendada)

```powershell
streamlit run app.py
```

La app abre en `http://localhost:8501` y ofrece tres pestanias:

- **Optimizar**: editores numericos para los 7 precios y las restricciones nutricionales; boton "Optimizar" y "Guardar tanda" para persistir en SQLite.
- **Historico**: listado y detalle de tandas registradas (precios usados, composicion resultante, costo).
- **Analisis**: serie temporal del costo optimo Z* por tanda.

### CLI (uso scriptable)

```powershell
python main.py
python main.py --pc-min 15.0 --em-min 300.0 --techo-nsc 0.65
python main.py --verbose
```

## Base de datos

Las tandas se almacenan en `data/nutricosto.db` (SQLite, autogenerado) con tres tablas:

- `tandas` — cabecera (fecha, codigo, parametros nutricionales, costo optimo, estado).
- `tanda_precios` — precios de los 7 insumos usados en cada tanda.
- `tanda_composicion` — kg y costo parcial por insumo resultante.

Para migrar a PostgreSQL basta sustituir `sqlite3.connect` en `nutricosto/db.py` por `psycopg2.connect`: el esquema SQL es portable.

## Salida

El programa genera un reporte de 7 secciones:

1. Funcion objetivo simbolica.
2. Restricciones del modelo con justificacion.
3. Estado del solver y valor optimo `Z*`.
4. Composicion del lote: kg, %, costo parcial por insumo.
5. Cumplimiento nutricional y tecnico (chequeo OK/FALLA).
6. Analisis de sensibilidad: holguras y precios sombra (variables duales).
7. Verificacion cruzada Simplex vs Interior Point.
