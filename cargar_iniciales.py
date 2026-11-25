"""Carga las bases de la carpeta datos/ en la base de datos. Uso: python cargar_iniciales.py
Lee cada archivo, detecta a qué apartado pertenece por su nombre y actualiza solo los años que trae."""
import glob, hashlib, os
from app.main import cargar_archivo
REGLAS = (("fallecidos-y-lesionados", "transito"), ("hechos-de-transito", "hechos"), ("vehiculos-involucrados", "vehiculos"), ("construcciones", "construcciones"))
vistos = set()
for f in sorted(glob.glob("datos/*.xlsx")):
    nombre = os.path.basename(f); raw = open(f, "rb").read(); h = hashlib.md5(raw).hexdigest()
    slug = next((s for k, s in REGLAS if k in nombre), None)
    if not slug: print("Se omite (no se reconoce):", nombre); continue
    if h in vistos: print("Se omite (archivo repetido):", nombre); continue
    vistos.add(h)
    n, anios = cargar_archivo(slug, raw, nombre, "actualizar", "sistema")
    print(f"{slug:15} {nombre:62} {n:>7} filas · años {anios}")
