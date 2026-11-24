"""Carga datos de DEMOSTRACIÓN (no oficiales) para ver el tablero funcionando. Uso: python seed.py"""
import numpy as np, pandas as pd
from app.main import engine, T
from sqlalchemy import delete
DEP = ["Guatemala","Sacatepéquez","Chimaltenango","Escuintla","Santa Rosa","Sololá","Totonicapán","Quetzaltenango","Suchitepéquez","Retalhuleu","San Marcos","Huehuetenango","Quiché","Baja Verapaz","Alta Verapaz","Petén","Izabal","Zacapa","Chiquimula","Jalapa","Jutiapa","El Progreso"]
r = np.random.default_rng(7); filas = []
for ind, esc in (("Casos registrados", 1.0), ("Personas atendidas", 0.7)):
    for d in DEP:
        peso = r.uniform(0.4, 2.2) * (3 if d == "Guatemala" else 1)
        for a in (2023, 2024, 2025):
            for m in range(1, 13):
                for sx, f in (("Mujer", 1.05), ("Hombre", 0.95), ("No identificado", 0.03)):
                    for ed, fe in (("0-14", .2), ("15-29", .3), ("30-59", .35), ("60+", .15)):
                        filas.append(["Demostración", ind, a, m, d, sx, ed, round(float(r.poisson(30 * peso * f * fe * esc)), 0), "DATOS DE DEMOSTRACIÓN, no oficiales"])
df = pd.DataFrame(filas, columns=["tema","indicador","anio","mes","departamento","sexo","grupo_edad","valor","fuente"])
with engine.begin() as c: c.execute(delete(T))
df.to_sql("indicador", engine, if_exists="append", index=False, chunksize=2000)
print("Filas de demostración cargadas:", len(df))
