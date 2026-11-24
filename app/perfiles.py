import json, os
import pandas as pd

BASE = os.path.dirname(__file__)
MES = ["Enero","Febrero","Marzo","Abril","Mayo","Junio","Julio","Agosto","Septiembre","Octubre","Noviembre","Diciembre"]
DIAS = ["Lunes","Martes","Miércoles","Jueves","Viernes","Sábado","Domingo"]
GEDAD = ["0-14","15-29","30-44","45-59","60 o más"]
RANGO = ["Menos de 100 m²","100 a 299 m²","300 a 999 m²","1,000 m² o más"]
DEP = dict(enumerate(["Guatemala","El Progreso","Sacatepéquez","Chimaltenango","Escuintla","Santa Rosa","Sololá","Totonicapán","Quetzaltenango","Suchitepéquez","Retalhuleu","San Marcos","Huehuetenango","Quiché","Baja Verapaz","Alta Verapaz","Petén","Izabal","Zacapa","Chiquimula","Jalapa","Jutiapa"], 1))
MUN = dict(enumerate(["Guatemala","Santa Catarina Pinula","San José Pinula","San José del Golfo","Palencia","Chinautla","San Pedro Ayampuc","Mixco","San Pedro Sacatepéquez","San Juan Sacatepéquez","San Raymundo","Chuarrancho","Fraijanes","Amatitlán","Villa Nueva","Villa Canales","San Miguel Petapa"], 1))
SEXO = {1: "Hombre", 2: "Mujer", 9: "No identificado"}
COND = {1: "Fallecido", 2: "Lesionado", 9: "Ignorado"}
ORDER = {"mes": MES, "dia_semana": DIAS, "grupo_edad": GEDAD, "rango_area": RANGO}
NAT = {"hora", "anio", "trimestre"}

def dic(n):
    try: return json.load(open(os.path.join(BASE, "diccionarios.json"), encoding="utf-8")).get(n, {})
    except Exception: return {}

def lab(s, mapa):
    m = {int(k): v for k, v in mapa.items()}
    def f(v):
        if pd.isna(v): return None
        v = int(v); return m.get(v, "Ignorado" if v in (99, 999) else f"Código {v}")
    return s.map(f)

def pedir(df, cols):
    df = df.rename(columns={c: str(c).strip().lower() for c in df.columns})
    falta = [c for c in cols if c not in df.columns]
    if falta: raise ValueError("Faltan columnas: " + ", ".join(falta))
    return df

# ---------- Hechos de tránsito ----------
T_REQ = ["año_ocu","mes_ocu","dia_sem_ocu","hora_ocu","depto_ocu","sexo_per","edad_per","tipo_veh","tipo_eve","fall_les"]
def limpiar_transito(df):
    df = pedir(df, T_REQ)
    r = {"año_ocu":"anio","mes_ocu":"mes","dia_sem_ocu":"dia_sem","hora_ocu":"hora","depto_ocu":"depto","sexo_per":"sexo","edad_per":"edad","fall_les":"condicion"}
    o = df.rename(columns=r)[["anio","mes","dia_sem","hora","depto","sexo","edad","tipo_veh","tipo_eve","condicion"]]
    return o.apply(pd.to_numeric, errors="coerce").dropna(subset=["anio"])

def etiq_transito(df):
    o = pd.DataFrame(index=df.index); o["anio"] = df["anio"]
    o["mes"] = lab(df.mes, dict(enumerate(MES, 1))); o["dia_semana"] = lab(df.dia_sem, dict(enumerate(DIAS, 1)))
    o["hora"] = df.hora.map(lambda h: None if pd.isna(h) or h > 23 else f"{int(h):02d}:00")
    o["departamento"] = lab(df.depto, DEP); o["sexo"] = lab(df.sexo, SEXO)
    o["edad"] = df.edad.where(df.edad < 150)
    o["grupo_edad"] = pd.cut(o["edad"], [-1, 14, 29, 44, 59, 200], labels=GEDAD).astype(object)
    o["tipo_vehiculo"] = lab(df.tipo_veh, dic("tipo_veh")); o["tipo_evento"] = lab(df.tipo_eve, dic("tipo_eve"))
    o["condicion"] = lab(df.condicion, COND)
    return o

def kpis_transito(d):
    c = lambda col, v: int((d[col] == v).sum())
    return [{"t": "Total de víctimas", "v": len(d), "c": "#0A5CFF", "u": "n"}, {"t": "Fallecidos", "v": c("condicion", "Fallecido"), "c": "#0B1F4D", "u": "n"},
            {"t": "Lesionados", "v": c("condicion", "Lesionado"), "c": "#D4AF37", "u": "n"}, {"t": "Hombres", "v": c("sexo", "Hombre"), "c": "#2563EB", "u": "n"},
            {"t": "Mujeres", "v": c("sexo", "Mujer"), "c": "#EC4899", "u": "n"}, {"t": "No identificados", "v": c("sexo", "No identificado"), "c": "#9CA3AF", "u": "n"}]

# ---------- Construcciones particulares ----------
C_REQ = ["año","trimestre","departamento","municipio","num_construcciones","area_con_m2","costo_aprox_quetzales"]
def limpiar_constr(df):
    df = pedir(df, C_REQ)
    o = df.rename(columns={"año":"anio","departamento":"depto","num_construcciones":"num","area_con_m2":"area","costo_aprox_quetzales":"costo"})
    return o[["anio","trimestre","depto","municipio","num","area","costo"]].apply(pd.to_numeric, errors="coerce").dropna(subset=["anio"])

def etiq_constr(df):
    o = pd.DataFrame(index=df.index); o["anio"] = df["anio"]
    o["trimestre"] = df.trimestre.map(lambda t: None if pd.isna(t) else f"Trimestre {int(t)}")
    o["departamento"] = lab(df.depto, DEP)
    o["municipio"] = [MUN.get(int(m), f"Municipio {int(m)}") if d == 1 else f"Municipio {int(m)}" for d, m in zip(df.depto, df.municipio)]
    o["num"] = df.num; o["area"] = df.area; o["costo"] = df.costo
    o["rango_area"] = pd.cut(df.area, [0, 99, 299, 999, 1e12], labels=RANGO).astype(object)
    return o

def kpis_constr(d):
    n, a, q = float(d.num.sum()), float(d.area.sum()), float(d.costo.sum())
    return [{"t": "Construcciones", "v": n, "c": "#0A5CFF", "u": "n"}, {"t": "Área construida", "v": a, "c": "#0B1F4D", "u": "m2"},
            {"t": "Costo aproximado", "v": q, "c": "#D4AF37", "u": "q"}, {"t": "Costo promedio por m²", "v": q / a if a else 0, "c": "#9CA3AF", "u": "q"}]

PERFILES = {
 "transito": {"nombre": "Fallecidos y lesionados en hechos de tránsito 2025", "apartado": "Accidentes de Tránsito", "icono": "🚗",
  "desc": "Víctimas registradas por la PNC en hechos de tránsito, publicadas por el INE. Cada fila es una persona.",
  "tabla": "d_transito", "requeridas": T_REQ, "limpiar": limpiar_transito, "etiquetar": etiq_transito, "kpis": kpis_transito, "medidas": {},
  "filtros": [("mes","Mes"),("departamento","Departamento"),("sexo","Sexo"),("condicion","Condición"),("tipo_vehiculo","Tipo de vehículo")],
  "charts": [("sexo","Distribución por sexo","doughnut","sexo",None,None),("mes","Víctimas por mes","bar","mes","sexo",None),
             ("mapa","Mapa por departamento · clic para filtrar","mapa","departamento","sexo",None),("dep","Departamentos con más víctimas","hbar","departamento","sexo",10),
             ("edad","Por grupo de edad","bar","grupo_edad","sexo",None),("hora","Por hora del día","line","hora","sexo",None),
             ("dia","Por día de la semana","bar","dia_semana","sexo",None),("veh","Por tipo de vehículo","hbar","tipo_vehiculo","condicion",8),
             ("eve","Por tipo de evento","doughnut","tipo_evento",None,None)]},
 "construcciones": {"nombre": "Construcciones particulares, departamento de Guatemala", "apartado": "Transporte y Servicios", "icono": "🏗️",
  "desc": "Licencias de construcción particulares por trimestre y municipio con área y costo aproximado.",
  "tabla": "d_construcciones", "requeridas": C_REQ, "limpiar": limpiar_constr, "etiquetar": etiq_constr, "kpis": kpis_constr,
  "medidas": {"num": "Construcciones", "area": "Área construida (m²)", "costo": "Costo aproximado (Q)"},
  "filtros": [("trimestre","Trimestre"),("municipio","Municipio"),("rango_area","Tamaño")],
  "charts": [("tri","Por trimestre","bar","trimestre",None,None),("mun","Por municipio","hbar","municipio",None,17),("rango","Por tamaño de construcción","doughnut","rango_area",None,None)]},
}

CATEGORIAS = [("accidentes-de-transito","Accidentes de Tránsito","🚗"),("agropecuario","Agropecuario","🚜"),("canasta-basica","Canasta básica alimentaria y ampliada","🛒"),
 ("comercio-exterior","Comercio Exterior","💹"),("condiciones-de-vida","Condiciones de vida","🏠"),("educacion","Educación","🎓"),("empleo","Empleo","💼"),
 ("genero","Género","⚧️"),("gestion-municipal","Gestión Municipal","🏛️"),("ipc","IPC","🛍️"),("medio-ambiente","Medio Ambiente","🌎"),("migracion","Migración","✈️"),
 ("poblacion","Población","👥"),("precios","Precios","💲"),("pueblos","Pueblos","🧑‍🤝‍🧑"),("recurso-humano","Recurso Humano","👷"),("salud","Salud","🏥"),
 ("servicios-publicos-basicos","Servicios Públicos Básicos","🚰"),("transporte-y-servicios","Transporte y Servicios","🚌"),("violencia","Violencia","🚨"),("vitales","Vitales","👶")]

def orden(vals):
    vals = [str(v) for v in vals]
    try: return sorted(vals, key=float)
    except ValueError: return sorted(vals)

def serie_libre(d, dim, med, top):
    x = d.dropna(subset=[dim])
    if x.empty: return {"labels": [], "series": []}
    x = x.assign(**{dim: x[dim].astype(str)})
    g = x.groupby(dim)[med].sum() if med else x.groupby(dim).size()
    try:
        g = g.iloc[pd.to_numeric(pd.Series(g.index)).argsort().values]
    except (ValueError, TypeError):
        g = g.sort_values(ascending=False).head(top or len(g))
    return {"labels": [str(i) for i in g.index], "series": [{"name": "Total", "data": [float(v) for v in g.values]}]}

def construir_libre(nombre, categoria, desc, df, params, medida):
    num = [c for c in df.columns if pd.api.types.is_numeric_dtype(df[c]) and 40 < df[c].nunique() < len(df)]
    dims = [c for c in df.columns if c not in num and 2 <= df[c].nunique() <= 40]
    filtros = [{"col": c, "label": c.replace("_", " ").capitalize(), "opciones": orden(df[c].dropna().unique())} for c in dims[:5]]
    for f in filtros:
        if params.get(f["col"]): df = df[df[f["col"]].astype(str) == params[f["col"]]]
    medidas = {"registros": "Número de registros", **{c: "Suma de " + c.replace("_", " ") for c in num[:4]}}
    med = medida if medida in num else None
    pal = ["#0B1F4D", "#D4AF37", "#9CA3AF"]
    kpis = [{"t": "Total de registros", "v": len(df), "c": "#0A5CFF", "u": "n"}] + \
           [{"t": "Suma de " + c.replace("_", " "), "v": float(df[c].sum()), "c": pal[i], "u": "n"} for i, c in enumerate(num[:3])]
    charts = []
    for i, c in enumerate(dims[:8]):
        n = df[c].nunique()
        try: pd.to_numeric(df[c].dropna().astype(str)); natural = True
        except ValueError: natural = False
        tipo = "doughnut" if n <= 6 else "bar" if natural and n <= 31 else "hbar"
        charts.append({"id": f"c{i}", "t": "Por " + c.replace("_", " "), "tipo": tipo, **serie_libre(df, c, med, 12)})
    return {"nombre": nombre, "apartado": categoria, "descripcion": desc or "Conjunto de datos cargado por el INE.", "filtros": filtros,
            "medidas": medidas, "medida": med or "registros", "kpis": kpis, "charts": charts, "filas": len(df)}

def ordenar(col, vals):
    vals = list(vals)
    if col in ORDER: return [v for v in ORDER[col] if v in vals] + [v for v in vals if v not in ORDER[col]]
    return sorted(vals, key=str)

def serie(d, dim, stack, med, top):
    x = d.dropna(subset=[dim]); keys = [dim] + ([stack] if stack else [])
    if x.empty: return {"labels": [], "series": []}
    g = x.groupby(keys)[med].sum() if med else x.groupby(keys).size()
    p = g.unstack(fill_value=0) if stack else g.to_frame("Total")
    if dim in ORDER or dim in NAT: p = p.loc[ordenar(dim, p.index)]
    else: p = p.loc[p.sum(axis=1).sort_values(ascending=False).index]
    if top: p = p.head(top)
    return {"labels": [str(i) for i in p.index], "series": [{"name": str(c), "data": [float(v) for v in p[c]]} for c in p.columns]}

def construir(slug, df, params, medida):
    P = PERFILES[slug]; d = P["etiquetar"](df); filtros = []
    for col, tit in P["filtros"]:
        filtros.append({"col": col, "label": tit, "opciones": ordenar(col, d[col].dropna().unique())})
    for col, _ in P["filtros"]:
        if params.get(col): d = d[d[col].astype(str) == params[col]]
    med = (medida if medida in P["medidas"] else next(iter(P["medidas"]))) if P["medidas"] else None
    charts = []
    for cid, t, tipo, dim, stack, top in P["charts"]:
        charts.append({"id": cid, "t": t, "tipo": tipo, **serie(d, dim, stack, med, top)})
    return {"nombre": P["nombre"], "apartado": P["apartado"], "descripcion": P["desc"], "filtros": filtros, "medidas": P["medidas"],
            "medida": med, "kpis": P["kpis"](d), "charts": charts, "filas": len(d)}
