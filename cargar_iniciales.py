"""Carga las dos bases de la carpeta datos/ en la base de datos. Uso: python cargar_iniciales.py"""
from app.main import cargar_archivo
for slug, f in (("transito", "datos/base-de-datos-fallecidos-y-lesionados-pnc-2025.xlsx"),
                ("construcciones", "datos/bd-construcciones-particulares-departamento-de-guatemala.xlsx")):
    print(slug, cargar_archivo(slug, open(f, "rb").read(), f.split("/")[-1], "reemplazar", "sistema"), "filas")
