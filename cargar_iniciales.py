"""Carga las bases de la carpeta datos/ en la base de datos. Uso: python cargar_iniciales.py
Cada base se enlaza con su conjunto del catálogo del INE. No crea conjuntos nuevos."""
import glob, hashlib, os
from sqlalchemy import text
from app.main import cargar_archivo, engine

REGLAS = (
    ("fallecidos-y-lesionados", "transito"),
    ("hechos-de-transito", "hechos"),
    ("vehiculos-involucrados", "vehiculos"),
    ("construcciones", "construcciones"),
    ("cbar", "costos-cba"),
    ("cba", "costos-cba"),
    ("ipc", "ipc-2024"),
)
NOMBRES_VIEJOS = ("Canasta Básica Alimentaria Rural", "IPC Base Anual 2024=100.00 ·")

with engine.begin() as c:
    for slug, nombre, tabla in list(c.execute(text("SELECT slug, nombre, tabla FROM conjunto"))):
        if nombre.startswith(NOMBRES_VIEJOS):
            c.execute(text(f"DROP TABLE IF EXISTS {tabla}"))
            c.execute(text("DELETE FROM conjunto WHERE slug = :s"), {"s": slug})
    for vieja in ("d_cbar_grupos", "d_cbar_productos", "d_ipc_producto", "d_ipc_division", "d_costos_cba", "d_ipc_2024"):
        c.execute(text(f"DROP TABLE IF EXISTS {vieja}"))

vistos = set()
for f in sorted(glob.glob("datos/*.xls*")):
    nombre = os.path.basename(f)
    raw = open(f, "rb").read()
    h = hashlib.md5(raw).hexdigest()
    if h in vistos: continue
    vistos.add(h)
    slug = next((s for k, s in REGLAS if k in nombre.lower()), None)
    if not slug: print("Se omite:", nombre); continue
    modo = "agregar" if slug in ("costos-cba", "ipc-2024") else "actualizar"
    n, anios = cargar_archivo(slug, raw, nombre, modo, "sistema")
    print(f"{slug:15} {nombre:62} {n:>7} filas · años {anios}")