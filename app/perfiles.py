import json, os, unicodedata
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
EDAD_MM = {1: "Mayor de edad", 2: "Menor de edad", 9: "Ignorado"}
ORDER = {"mes": MES, "dia_semana": DIAS, "grupo_edad": GEDAD, "rango_area": RANGO}
NAT = {"hora", "anio", "trimestre"}
OVER = {}  # nombres de códigos guardados desde el panel, los llena main.py en cada consulta
CAMPOS_DIC = {"tipo_veh": "Tipo de vehículo", "tipo_eve": "Tipo de evento", "marca_veh": "Marca del vehículo", "color_veh": "Color del vehículo",
              "estado_con": "Estado del conductor", "int_o_noint": "Campo int_o_noint", "mupio": "Municipio"}

def norm(c): return unicodedata.normalize("NFKD", str(c).strip().lower()).encode("ascii", "ignore").decode().replace(" ", "_")

def dic(n):
    try: j = json.load(open(os.path.join(BASE, "diccionarios.json"), encoding="utf-8")).get(n, {})
    except Exception: j = {}
    return {**j, **OVER.get(n, {})}

def dic_completo(campo):
    m = {int(k): v for k, v in dic(campo).items()}
    return {**{100 + k: v for k, v in MUN.items()}, **m} if campo == "mupio" else m

def lab(s, mapa, pref="Código"):
    m = {int(k): v for k, v in mapa.items()}
    def f(v):
        if pd.isna(v): return None
        v = int(v); return m.get(v, "Ignorado" if v in (99, 999, 9999) else f"{pref} {v}")
    return s.map(f)

def pedir(df, cols):
    df = df.rename(columns={c: norm(c) for c in df.columns})
    falta = [c for c in cols if c not in df.columns]
    if falta: raise ValueError("Faltan columnas: " + ", ".join(falta))
    return df

# ---------- Accidentes de tránsito: tres bases con el mismo formato base ----------
COMUN = ["ano_ocu", "mes_ocu", "dia_sem_ocu", "hora_ocu", "depto_ocu", "tipo_eve"]
RENAME = {"ano_ocu": "anio", "mes_ocu": "mes", "dia_sem_ocu": "dia_sem", "hora_ocu": "hora", "depto_ocu": "depto", "mupio_ocu": "mupio",
          "zona_ocu": "zona", "sexo_per": "sexo", "edad_per": "edad", "fall_les": "condicion"}

def limpiar_t(req):
    def f(df):
        df = pedir(df, req)
        df = df.drop(columns=[c for c in ("num_corre",) if c in df.columns]).rename(columns=RENAME)
        return df.apply(pd.to_numeric, errors="coerce").dropna(subset=["anio"])
    return f

def etiq_transito(df):
    t = lambda c: c in df.columns
    o = pd.DataFrame(index=df.index); o["anio"] = df["anio"].astype(int)
    o["mes"] = lab(df.mes, dict(enumerate(MES, 1))); o["dia_semana"] = lab(df.dia_sem, dict(enumerate(DIAS, 1)))
    o["hora"] = df.hora.map(lambda h: None if pd.isna(h) or h > 23 else f"{int(h):02d}:00")
    o["departamento"] = lab(df.depto, DEP)
    if t("mupio"): o["municipio"] = lab(df.mupio, dic_completo("mupio"), "Municipio")
    if t("zona"): o["zona"] = df.zona.map(lambda v: None if pd.isna(v) else ("Sin zona" if int(v) == 99 else f"Zona {int(v)}"))
    if t("sexo"): o["sexo"] = lab(df.sexo, SEXO)
    if t("edad"):
        o["edad"] = df.edad.where(df.edad < 150)
        o["grupo_edad"] = pd.cut(o["edad"], [-1, 14, 29, 44, 59, 200], labels=GEDAD).astype(object)
    if t("mayor_menor"): o["mayor_o_menor"] = lab(df.mayor_menor, EDAD_MM)
    if t("tipo_veh"): o["tipo_vehiculo"] = lab(df.tipo_veh, dic_completo("tipo_veh"))
    o["tipo_evento"] = lab(df.tipo_eve, dic_completo("tipo_eve"))
    if t("marca_veh"): o["marca"] = lab(df.marca_veh, dic_completo("marca_veh"))
    if t("color_veh"): o["color"] = lab(df.color_veh, dic_completo("color_veh"))
    if t("estado_con"): o["estado_conductor"] = lab(df.estado_con, dic_completo("estado_con"))
    if t("int_o_noint"): o["int_o_noint"] = lab(df.int_o_noint, dic_completo("int_o_noint"))
    if t("condicion"): o["condicion"] = lab(df.condicion, COND)
    return o

def moda(d, col):
    s = d[col].dropna() if col in d.columns else []
    return str(s.value_counts().idxmax()) if len(s) else "sin dato"

def kpis_transito(d):
    c = lambda col, v: int((d[col] == v).sum())
    return [{"t": "Total de víctimas", "v": len(d), "c": "#0A5CFF", "u": "n"}, {"t": "Fallecidos", "v": c("condicion", "Fallecido"), "c": "#0B1F4D", "u": "n"},
            {"t": "Lesionados", "v": c("condicion", "Lesionado"), "c": "#D4AF37", "u": "n"}, {"t": "Hombres", "v": c("sexo", "Hombre"), "c": "#2563EB", "u": "n"},
            {"t": "Mujeres", "v": c("sexo", "Mujer"), "c": "#EC4899", "u": "n"}, {"t": "No identificados", "v": c("sexo", "No identificado"), "c": "#9CA3AF", "u": "n"}]

def kpis_hechos(d):
    return [{"t": "Total de hechos de tránsito", "v": len(d), "c": "#0A5CFF", "u": "n"}, {"t": "Día con más hechos", "v": moda(d, "dia_semana"), "c": "#D4AF37", "u": "txt"},
            {"t": "Hora con más hechos", "v": moda(d, "hora"), "c": "#0B1F4D", "u": "txt"}, {"t": "Departamento con más hechos", "v": moda(d, "departamento"), "c": "#9CA3AF", "u": "txt"},
            {"t": "Mes con más hechos", "v": moda(d, "mes"), "c": "#2563EB", "u": "txt"}]

def kpis_vehiculos(d):
    c = lambda v: int((d["sexo"] == v).sum()) if "sexo" in d.columns else 0
    return [{"t": "Vehículos involucrados", "v": len(d), "c": "#0A5CFF", "u": "n"}, {"t": "Conductores hombres", "v": c("Hombre"), "c": "#2563EB", "u": "n"},
            {"t": "Conductoras mujeres", "v": c("Mujer"), "c": "#EC4899", "u": "n"}, {"t": "No identificados", "v": c("No identificado"), "c": "#9CA3AF", "u": "n"},
            {"t": "Hora con más casos", "v": moda(d, "hora"), "c": "#0B1F4D", "u": "txt"}, {"t": "Departamento con más casos", "v": moda(d, "departamento"), "c": "#D4AF37", "u": "txt"}]

F_BASE = [("anio", "Año"), ("mes", "Mes"), ("departamento", "Departamento")]
CALOR = [("dia_semana", "Día de la semana"), ("hora", "Hora"), ("mes", "Mes"), ("departamento", "Departamento"), ("anio", "Año"), ("grupo_edad", "Grupo de edad"),
         ("tipo_vehiculo", "Tipo de vehículo"), ("tipo_evento", "Tipo de evento"), ("sexo", "Sexo"), ("zona", "Zona"), ("municipio", "Municipio"), ("condicion", "Condición")]
G_ANIO = ("anio", "Víctimas por año", "bar", "anio", "sexo", None)
G_MES = ("mes", "Por mes, una línea por año", "line", "mes", "anio", None)
G_MAPA = ("mapa", "Mapa por departamento · clic para filtrar", "mapa", "departamento", None, None)

# ---------- Construcciones particulares ----------
C_REQ = ["ano", "trimestre", "departamento", "municipio", "num_construcciones", "area_con_m2", "costo_aprox_quetzales"]
def limpiar_constr(df):
    df = pedir(df, C_REQ)
    o = df.rename(columns={"ano": "anio", "departamento": "depto", "num_construcciones": "num", "area_con_m2": "area", "costo_aprox_quetzales": "costo"})
    return o[["anio", "trimestre", "depto", "municipio", "num", "area", "costo"]].apply(pd.to_numeric, errors="coerce").dropna(subset=["anio"])

def etiq_constr(df):
    o = pd.DataFrame(index=df.index); o["anio"] = df["anio"].astype(int)
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

DS = "https://datos.ine.gob.gt/dataset/"
PERFILES = {
 "transito": {"nombre": "Accidentes de tránsito · Fallecidos y lesionados", "apartado": "Accidentes de Tránsito", "icono": "🚑", "url_ine": DS + "accidentes-de-transito-fallecidos-y-lesionados",
  "desc": "Víctimas fallecidas y lesionadas en hechos de tránsito registradas por la PNC. Cada fila es una persona.",
  "tabla": "d_transito", "requeridas": COMUN + ["sexo_per", "edad_per", "fall_les"], "limpiar": limpiar_t(COMUN + ["sexo_per", "edad_per", "fall_les"]), "etiquetar": etiq_transito,
  "kpis": kpis_transito, "medidas": {}, "filtros": F_BASE + [("sexo", "Sexo"), ("condicion", "Condición"), ("tipo_vehiculo", "Tipo de vehículo"), ("tipo_evento", "Tipo de evento")],
  "calor": CALOR, "calor_def": ("dia_semana", "hora"),
  "charts": [("sexo", "Distribución por sexo", "doughnut", "sexo", None, None), G_ANIO, G_MES, G_MAPA, ("edad", "Por grupo de edad", "bar", "grupo_edad", "sexo", None),
             ("veh", "Por tipo de vehículo", "hbar", "tipo_vehiculo", "condicion", 8)]},
 "hechos": {"nombre": "Accidentes de tránsito · Hechos", "apartado": "Accidentes de Tránsito", "icono": "🚦", "url_ine": DS + "accidentes-de-transito-hechos",
  "desc": "Hechos de tránsito registrados por la PNC. Cada fila es un hecho.",
  "tabla": "d_hechos", "requeridas": COMUN, "limpiar": limpiar_t(COMUN), "etiquetar": etiq_transito, "kpis": kpis_hechos, "medidas": {},
  "filtros": F_BASE + [("dia_semana", "Día de la semana"), ("tipo_vehiculo", "Tipo de vehículo"), ("tipo_evento", "Tipo de evento")],
  "calor": CALOR, "calor_def": ("dia_semana", "hora"),
  "charts": [("anio", "Hechos por año", "bar", "anio", None, None), G_MES, G_MAPA, ("dia", "Por día de la semana", "bar", "dia_semana", None, None),
             ("eve", "Por tipo de evento", "doughnut", "tipo_evento", None, None), ("veh", "Por tipo de vehículo", "hbar", "tipo_vehiculo", None, 8)]},
 "vehiculos": {"nombre": "Accidentes de tránsito · Vehículos involucrados", "apartado": "Accidentes de Tránsito", "icono": "🚗", "url_ine": DS + "accidentes-de-transito-vehiculos-involucrados",
  "desc": "Vehículos involucrados en hechos de tránsito registrados por la PNC, con datos del vehículo y de la persona conductora.",
  "tabla": "d_vehiculos", "requeridas": COMUN + ["sexo_per", "edad_per", "tipo_veh"], "limpiar": limpiar_t(COMUN + ["sexo_per", "edad_per", "tipo_veh"]), "etiquetar": etiq_transito,
  "kpis": kpis_vehiculos, "medidas": {}, "filtros": F_BASE + [("sexo", "Sexo"), ("grupo_edad", "Grupo de edad"), ("tipo_vehiculo", "Tipo de vehículo"), ("tipo_evento", "Tipo de evento")],
  "calor": CALOR, "calor_def": ("dia_semana", "hora"),
  "charts": [("sexo", "Distribución por sexo", "doughnut", "sexo", None, None), G_ANIO, G_MES, G_MAPA, ("edad", "Por grupo de edad", "bar", "grupo_edad", "sexo", None),
             ("veh", "Por tipo de vehículo", "hbar", "tipo_vehiculo", None, 10), ("eve", "Por tipo de evento", "doughnut", "tipo_evento", None, None)]},
 "construcciones": {"nombre": "Construcciones particulares, departamento de Guatemala", "apartado": "Transporte y Servicios", "icono": "🏗️", "url_ine": DS + "construcciones-particulares-nivel-departamental",
  "desc": "Licencias de construcción particulares por trimestre y municipio con área y costo aproximado.",
  "tabla": "d_construcciones", "requeridas": C_REQ, "limpiar": limpiar_constr, "etiquetar": etiq_constr, "kpis": kpis_constr,
  "medidas": {"num": "Construcciones", "area": "Área construida (m²)", "costo": "Costo aproximado (Q)"},
  "filtros": [("anio", "Año"), ("trimestre", "Trimestre"), ("municipio", "Municipio"), ("rango_area", "Tamaño")],
  "calor": [("municipio", "Municipio"), ("trimestre", "Trimestre"), ("rango_area", "Tamaño"), ("anio", "Año")], "calor_def": ("municipio", "trimestre"),
  "charts": [("tri", "Por trimestre", "bar", "trimestre", None, None), ("mun", "Por municipio", "hbar", "municipio", None, 17), ("rango", "Por tamaño de construcción", "doughnut", "rango_area", None, None)]},
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

def eje(x, dim, top):
    v = x[dim].dropna().unique()
    if dim in ORDER: return ordenar(dim, v)
    if dim in NAT: return sorted(v)
    return x[dim].value_counts().head(top).index.tolist()

def calor(d, f, c, med):
    x = d.dropna(subset=[f, c])
    if x.empty: return {"filas": [], "columnas": [], "z": []}
    g = x.groupby([f, c])[med].sum() if med else x.groupby([f, c]).size()
    p = g.unstack(fill_value=0).reindex(index=eje(x, f, 22), columns=eje(x, c, 24), fill_value=0).fillna(0)
    return {"filas": [str(i) for i in p.index], "columnas": [str(i) for i in p.columns], "z": [[float(v) for v in r] for r in p.values.tolist()]}

def construir(slug, df, params, medida):
    P = PERFILES[slug]; d = P["etiquetar"](df); filtros = []
    anios = [{"anio": int(a), "filas": int(n)} for a, n in d["anio"].value_counts().sort_index().items()]
    for col, tit in P["filtros"]:
        if col in d.columns: filtros.append({"col": col, "label": tit, "opciones": [v if isinstance(v, str) else int(v) for v in ordenar(col, d[col].dropna().unique())]})
    for f in filtros:
        if params.get(f["col"]): d = d[d[f["col"]].astype(str) == params[f["col"]]]
    med = (medida if medida in P["medidas"] else next(iter(P["medidas"]))) if P["medidas"] else None
    charts = []
    for cid, t, tipo, dim, stack, top in P["charts"]:
        if dim not in d.columns or d[dim].dropna().empty: continue
        if cid == "anio" and len(anios) < 2: continue
        st = stack if stack in d.columns else None
        charts.append({"id": cid, "t": t, "tipo": tipo, **serie(d, dim, st, med, top)})
    ops = [{"k": k, "l": l} for k, l in P["calor"] if k in d.columns]
    f0, c0 = P["calor_def"]; f = params.get("f") if params.get("f") in [o["k"] for o in ops] else f0; c = params.get("c") if params.get("c") in [o["k"] for o in ops] else c0
    if f == c: c = next((o["k"] for o in ops if o["k"] != f), c)
    return {"nombre": P["nombre"], "apartado": P["apartado"], "descripcion": P["desc"], "filtros": filtros, "medidas": P["medidas"], "medida": med,
            "kpis": P["kpis"](d), "charts": charts, "filas": len(d), "anios": anios, "url_ine": P["url_ine"],
            "calor": {**calor(d, f, c, med), "f": f, "c": c, "opciones": ops}}
