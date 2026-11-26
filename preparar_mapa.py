"""Convierte los mapas TopoJSON de datos/mapa/ en un archivo ligero de trazos SVG y en la lista de nombres de municipios.
Fuente de los límites: repositorio minfin-bi/Mapas-TopoJSON-Guatemala del Ministerio de Finanzas Públicas.
Uso: python preparar_mapa.py"""
import json, math, os

def arcos(t):
    sx, sy = t["transform"]["scale"]; tx, ty = t["transform"]["translate"]; out = []
    for a in t["arcs"]:
        x = y = 0; pts = []
        for dx, dy in a: x += dx; y += dy; pts.append((x * sx + tx, y * sy + ty))
        out.append(pts)
    return out

def anillo(A, idx):
    pts = []
    for i in idx:
        seg = A[i] if i >= 0 else A[~i][::-1]
        pts.extend(seg if not pts else seg[1:])
    return pts

def poligonos(g, A):
    polys = g["arcs"] if g["type"] == "MultiPolygon" else [g["arcs"]]
    return [[anillo(A, r) for r in p] for p in polys]

LON0, LAT0, K = -92.3, 18.1, 70.0  # esquina noroeste del mapa y escala
COS = math.cos(math.radians(15.5))
proy = lambda lon, lat: ((lon - LON0) * COS * K, (LAT0 - lat) * K)

def trazo(polys):
    d, xs, ys = [], [], []
    for p in polys:
        for r in p:
            q, ult = [], None
            for lon, lat in r:
                x, y = proy(lon, lat); x, y = round(x, 1), round(y, 1)
                if ult and abs(x - ult[0]) < 0.25 and abs(y - ult[1]) < 0.25: continue
                q.append((x, y)); ult = (x, y); xs.append(x); ys.append(y)
            if len(q) > 2: d.append("M" + "L".join(f"{x} {y}" for x, y in q) + "Z")
    return "".join(d), [min(xs), min(ys), max(xs), max(ys)]

PEQ = {"Del", "De", "La", "Las", "Los", "El", "Y"}
def bonito(s):
    p = s.split(); return " ".join(w.lower() if i and w in PEQ else w for i, w in enumerate(p))

M = json.load(open("datos/mapa/munis.json", encoding="utf-8")); A = arcos(M)
D = json.load(open("datos/mapa/deptos.json", encoding="utf-8")); AD = arcos(D)
geos = M["objects"]["municipios_gtm"]["geometries"]
nombres = {}; veces = {}
for g in geos:
    p = g["properties"]
    if p["id"] not in (0, 4000): veces[bonito(p["Municipio"])] = veces.get(bonito(p["Municipio"]), 0) + 1
out = {"munis": [], "deptos": [], "lagos": [], "belice": ""}
for g in geos:
    p = g["properties"]; d, bb = trazo(poligonos(g, A)); n = bonito(p["Municipio"])
    if p["id"] == 0: out["lagos"].append(d); continue
    if p["id"] == 4000: out["belice"] = d; continue
    etiqueta = f"{n}, {bonito(p['Departamento'])}" if veces[n] > 1 else n
    nombres[str(p["id"])] = etiqueta
    out["munis"].append({"id": p["id"], "n": etiqueta, "dep": p["id_depto"], "d": d})
xs = []
for g in D["objects"]["departamentos_gtm"]["geometries"]:
    p = g["properties"]; d, bb = trazo(poligonos(g, AD)); xs.append(bb)
    out["deptos"].append({"id": p["id"], "n": p["Departamento"], "d": d, "bbox": bb})
out["bbox"] = [min(b[0] for b in xs), min(b[1] for b in xs), max(b[2] for b in xs), max(b[3] for b in xs)]
os.makedirs("app/static/geo", exist_ok=True)
json.dump(out, open("app/static/geo/gt_paths.json", "w", encoding="utf-8"), ensure_ascii=False, separators=(",", ":"))
json.dump(nombres, open("app/mun_codigos.json", "w", encoding="utf-8"), ensure_ascii=False, indent=0)
print("municipios", len(out["munis"]), "departamentos", len(out["deptos"]), "tamaño KB", os.path.getsize("app/static/geo/gt_paths.json") // 1024, "caja", out["bbox"])
