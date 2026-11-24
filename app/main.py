import io, os, json, re, unicodedata, hmac, hashlib, secrets, time, base64
from datetime import datetime, timedelta
import pandas as pd
from fastapi import BackgroundTasks, APIRouter, FastAPI, UploadFile, File, Form, HTTPException, Depends, Request, Response
from pydantic import BaseModel
from fastapi.responses import StreamingResponse, RedirectResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from sqlalchemy import create_engine, MetaData, Table, Column, Integer, String, Float, DateTime, Boolean, select, inspect, text, func

_RAIZ = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
def _cargar_env():
    ruta = os.path.join(_RAIZ, ".env")
    if os.path.exists(ruta):
        for linea in open(ruta, encoding="utf-8"):
            linea = linea.strip()
            if linea and not linea.startswith("#") and "=" in linea:
                k, v = linea.split("=", 1); os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
_cargar_env()
URL = os.getenv("DATABASE_URL") or "sqlite:///" + os.path.join(_RAIZ, "ine.db").replace("\\", "/")
if URL.startswith("postgres://"): URL = URL.replace("postgres://", "postgresql://", 1)
engine = create_engine(URL, pool_pre_ping=True)
md = MetaData()
T = Table("indicador", md,
    Column("id", Integer, primary_key=True),
    Column("tema", String(120), index=True), Column("indicador", String(200), index=True),
    Column("anio", Integer, index=True), Column("mes", Integer), Column("departamento", String(80), index=True),
    Column("sexo", String(20)), Column("grupo_edad", String(30)), Column("valor", Float),
    Column("fuente", String(300)), Column("cargado", DateTime, default=datetime.utcnow))
U = Table("usuario", md, Column("id", Integer, primary_key=True), Column("usuario", String(60), unique=True),
    Column("clave_hash", String(200)), Column("rol", String(20)), Column("activo", Boolean, default=True), Column("correo", String(200)))
L = Table("carga", md, Column("id", Integer, primary_key=True), Column("slug", String(40)), Column("filas", Integer),
    Column("archivo", String(200)), Column("usuario", String(60)), Column("fecha", DateTime))
Cj = Table("conjunto", md, Column("id", Integer, primary_key=True), Column("slug", String(80), unique=True), Column("nombre", String(200)),
    Column("categoria", String(80)), Column("descripcion", String(500)), Column("tabla", String(100)), Column("fecha", DateTime))
R = Table("recuperacion", md, Column("id", Integer, primary_key=True), Column("usuario_id", Integer, index=True), Column("token_hash", String(64), index=True),
    Column("creado", DateTime), Column("expira", DateTime), Column("usado", Boolean))
A = Table("intento", md, Column("id", Integer, primary_key=True), Column("usuario", String(60), index=True), Column("ip", String(60), index=True), Column("fecha", DateTime, index=True))
B = Table("bitacora", md, Column("id", Integer, primary_key=True), Column("fecha", DateTime, index=True), Column("usuario", String(80)),
    Column("accion", String(60)), Column("detalle", String(500)), Column("ip", String(60)))
md.create_all(engine)
def _migrar():
    if "correo" not in [c["name"] for c in inspect(engine).get_columns("usuario")]:
        with engine.begin() as c: c.execute(text("ALTER TABLE usuario ADD COLUMN correo VARCHAR(200)"))
_migrar()
from . import perfiles as pf
from .correo import enviar

COLS = ["tema", "indicador", "anio", "mes", "departamento", "sexo", "grupo_edad", "valor", "fuente"]
REQ = ["tema", "indicador", "anio", "departamento", "sexo", "valor", "fuente"]
PUBLIC = os.getenv("PUBLIC_ONLY", "0") == "1"
BASE = os.path.dirname(__file__)
app = FastAPI(title="Datos abiertos INE", docs_url=None, redoc_url=None, openapi_url=None)
admin = APIRouter()

SECRET = (os.getenv("SECRET_KEY") or secrets.token_hex(32)).encode()
FALLOS = {}

def hashear(clave):
    sal = secrets.token_hex(16)
    return sal + "$" + hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), 200000).hex()

def verificar(clave, h):
    sal, x = h.split("$")
    return hmac.compare_digest(hashlib.pbkdf2_hmac("sha256", clave.encode(), sal.encode(), 200000).hex(), x)

def etiqueta(h): return hashlib.sha256(h.encode()).hexdigest()[:12]

def firmar(usuario, clave_hash):
    d = base64.urlsafe_b64encode(f"{usuario}|{int(time.time()) + 8 * 3600}|{etiqueta(clave_hash)}".encode()).decode()
    return d + "." + hmac.new(SECRET, d.encode(), "sha256").hexdigest()

def quien(request: Request):
    t = request.cookies.get("sesion", "")
    try:
        d, f = t.split(".")
        if not hmac.compare_digest(hmac.new(SECRET, d.encode(), "sha256").hexdigest(), f): raise ValueError
        u, exp, tag = base64.urlsafe_b64decode(d).decode().split("|")
        if int(exp) < time.time(): raise ValueError
        with engine.connect() as c: r = c.execute(select(U).where(U.c.usuario == u)).first()
        if not r or not r.activo or etiqueta(r.clave_hash) != tag: raise ValueError
        return {"usuario": r.usuario, "rol": r.rol}
    except Exception:
        raise HTTPException(401, "Inicia sesión")

def solo_admin(u=Depends(quien)):
    if u["rol"] != "admin": raise HTTPException(403, "Solo el administrador puede hacer esto")
    return u

EMAIL = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
VENTANA = timedelta(minutes=15)

def ip_de(request):
    if request is None: return "local"
    if os.getenv("TRUST_PROXY") == "1":
        x = request.headers.get("x-forwarded-for", "").split(",")[0].strip()
        if x: return x[:60]
    return (request.client.host if request.client else "?")[:60]

def reg(request, usuario, accion, detalle=""):
    try:
        with engine.begin() as c:
            c.execute(B.insert().values(fecha=datetime.utcnow(), usuario=str(usuario)[:80], accion=accion[:60], detalle=str(detalle)[:500], ip=ip_de(request)))
    except Exception as e: print("No se pudo escribir la bitácora:", e)

def crear_usuario(usuario, clave, rol="cargador", correo=""):
    usuario, correo = usuario.strip().lower(), correo.strip().lower()
    if not re.fullmatch(r"[a-z0-9._-]{3,40}", usuario): raise ValueError("El usuario debe tener de 3 a 40 letras, números, punto, guion o guion bajo")
    if len(clave) < 10: raise ValueError("La contraseña debe tener al menos 10 caracteres")
    if clave.lower() == usuario: raise ValueError("La contraseña no puede ser igual al usuario")
    if not EMAIL.match(correo): raise ValueError("Escribe un correo válido para poder recuperar la contraseña")
    if rol not in ("admin", "cargador"): raise ValueError("Rol inválido")
    with engine.begin() as c:
        if c.execute(select(U.c.id).where(U.c.usuario == usuario)).first(): raise ValueError("Ese usuario ya existe")
        if c.execute(select(U.c.id).where(U.c.correo == correo)).first(): raise ValueError("Ese correo ya está registrado")
        c.execute(U.insert().values(usuario=usuario, clave_hash=hashear(clave), rol=rol, activo=True, correo=correo))

def sexo(s):
    s = str(s).strip().lower()
    if s.startswith(("mu", "fem")) or s in ("m", "f"): return "Mujer"
    if s.startswith(("hom", "mas")) or s == "h": return "Hombre"
    return "No identificado"

def todo(): return pd.read_sql(select(T), engine)
XL = "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"

@app.get("/api/filtros")
def filtros():
    d = todo(); f = lambda c: sorted(d[c].dropna().unique().tolist())
    return {"temas": f("tema"), "indicadores": f("indicador"), "anios": f("anio"),
            "meses": [int(m) for m in f("mes")], "departamentos": f("departamento")}

@app.get("/api/datos")
def datos(tema: str = "", indicador: str = "", anio: int = 0, mes: int = 0, departamento: str = "", sexo_f: str = ""):
    d0 = todo()
    def filt(skip=""):
        d = d0
        for c, v in (("tema", tema), ("indicador", indicador), ("anio", anio), ("mes", mes), ("departamento", departamento), ("sexo", sexo_f)):
            if v and c != skip: d = d[d[c] == v]
        return d
    def g(x, by):
        x = x.dropna(subset=[by])
        if not len(x): return {}
        if by in ("mes", "anio"): x = x.assign(**{by: x[by].astype(int)})
        p = x.pivot_table(index=by, columns="sexo", values="valor", aggfunc="sum").fillna(0)
        return {str(k): {s: float(v) for s, v in r.items()} for k, r in p.iterrows()}
    d = filt()
    return {"totales": d.groupby("sexo")["valor"].sum().to_dict() if len(d) else {},
            "por_mes": g(d, "mes"), "por_anio": g(d, "anio"), "por_edad": g(d, "grupo_edad"),
            "por_departamento": g(filt("departamento"), "departamento"),
            "fuentes": sorted(d["fuente"].dropna().unique().tolist()), "filas": len(d)}

def plantillas(): return json.load(open(os.path.join(BASE, "plantillas.json"), encoding="utf-8"))

@admin.get("/api/admin/plantillas")
def lista(u=Depends(quien)):
    return [p["nombre"] for p in plantillas()]

@admin.get("/api/admin/plantilla/{i}")
def plantilla(i: int, u=Depends(quien)):
    p = plantillas()[i]
    ej = pd.DataFrame([[p["tema"], p["indicador"], None, None, "", sx, "Todas", None, p["fuente"]]
                       for sx in ("Mujer", "Hombre", "No identificado")], columns=COLS)
    b = io.BytesIO(); ej.to_excel(b, index=False); b.seek(0)
    nom = re.sub(r"\W+", "_", unicodedata.normalize("NFKD", p["nombre"].lower()).encode("ascii", "ignore").decode())
    return StreamingResponse(b, media_type=XL, headers={"Content-Disposition": f"attachment; filename=plantilla_{nom}.xlsx"})

@admin.get("/admin")
def pagina_admin(): return FileResponse(os.path.join(BASE, "admin", "admin.html"))

@admin.post("/api/admin/subir")
async def subir(request: Request, archivo: UploadFile = File(...), u=Depends(quien)):
    raw, n = await archivo.read(), archivo.filename.lower()
    try:
        if n.endswith(".csv"): df = pd.read_csv(io.BytesIO(raw))
        elif n.endswith((".xlsx", ".xls")): df = pd.read_excel(io.BytesIO(raw))
        elif n.endswith(".docx"):
            from docx import Document
            rows = [[c.text.strip() for c in r.cells] for r in Document(io.BytesIO(raw)).tables[0].rows]
            df = pd.DataFrame(rows[1:], columns=rows[0])
        else: raise ValueError("Usa .xlsx, .csv o .docx con tabla")
        df.columns = [str(c).strip().lower() for c in df.columns]
        faltan = [c for c in REQ if c not in df.columns]
        if faltan: raise ValueError("Faltan columnas: " + ", ".join(faltan))
        for c in ("mes", "grupo_edad"):
            if c not in df.columns: df[c] = None
        df = df[COLS].copy(); df["valor"] = pd.to_numeric(df["valor"], errors="coerce")
        df["anio"] = pd.to_numeric(df["anio"], errors="coerce")
        df = df.dropna(subset=["valor", "anio"]); df["anio"] = df["anio"].astype(int)
        df["mes"] = pd.to_numeric(df["mes"], errors="coerce").astype("Int64")
        df["grupo_edad"] = df["grupo_edad"].fillna("Todas"); df["sexo"] = df["sexo"].map(sexo)
        df["cargado"] = datetime.utcnow()
    except Exception as e: raise HTTPException(400, str(e))
    df.to_sql("indicador", engine, if_exists="append", index=False)
    reg(request, u["usuario"], "carga_indicadores", f"{archivo.filename} · {len(df)} filas")
    return {"insertadas": len(df)}

@admin.get("/api/admin/exportar")
def exportar(request: Request, u=Depends(solo_admin)):
    reg(request, u["usuario"], "exportar_indicadores")
    b = io.BytesIO(); todo().to_excel(b, index=False); b.seek(0)
    return StreamingResponse(b, media_type=XL, headers={"Content-Disposition": "attachment; filename=datos_ine.xlsx"})

@admin.delete("/api/admin/limpiar")
def limpiar(request: Request, u=Depends(solo_admin)):
    reg(request, u["usuario"], "borrar_indicadores", "Se vació la tabla de indicadores")
    with engine.begin() as c: c.execute(T.delete())
    return {"ok": True}

class Cred(BaseModel):
    usuario: str
    clave: str

class Nuevo(Cred):
    rol: str = "cargador"
    correo: str = ""

class Olvide(BaseModel):
    correo: str

class Restab(BaseModel):
    token: str
    clave: str

@admin.post("/api/login")
def login(c: Cred, resp: Response, request: Request):
    k = c.usuario.strip().lower()[:60]; ip = ip_de(request); desde = datetime.utcnow() - VENTANA
    with engine.connect() as cx:
        par = cx.execute(select(func.count()).select_from(A).where(A.c.usuario == k, A.c.ip == ip, A.c.fecha > desde)).scalar()
        tot = cx.execute(select(func.count()).select_from(A).where(A.c.usuario == k, A.c.fecha > desde)).scalar()
        porip = cx.execute(select(func.count()).select_from(A).where(A.c.ip == ip, A.c.fecha > desde)).scalar()
        r = cx.execute(select(U).where(U.c.usuario == k)).first()
    if par >= 5 or tot >= 20 or porip >= 30:
        reg(request, k, "login_bloqueado", "Demasiados intentos")
        raise HTTPException(429, "Demasiados intentos. Espera 15 minutos o recupera tu contraseña por correo.")
    if not r or not r.activo or not verificar(c.clave, r.clave_hash):
        with engine.begin() as cx: cx.execute(A.insert().values(usuario=k, ip=ip, fecha=datetime.utcnow()))
        reg(request, k, "login_fallido"); raise HTTPException(401, "Usuario o contraseña incorrectos")
    with engine.begin() as cx:
        cx.execute(A.delete().where(A.c.usuario == k)); cx.execute(A.delete().where(A.c.fecha < datetime.utcnow() - timedelta(days=1)))
    resp.set_cookie("sesion", firmar(r.usuario, r.clave_hash), httponly=True, samesite="strict",
                    secure=os.getenv("COOKIE_SECURE", "0") == "1", max_age=8 * 3600)
    reg(request, r.usuario, "login_ok")
    return {"usuario": r.usuario, "rol": r.rol}

@admin.post("/api/logout")
def logout(resp: Response, request: Request):
    try: reg(request, quien(request)["usuario"], "logout")
    except Exception: pass
    resp.delete_cookie("sesion"); return {"ok": True}

@admin.get("/api/yo")
def yo(u=Depends(quien)): return u

@admin.get("/api/admin/usuarios")
def usuarios(u=Depends(solo_admin)):
    with engine.connect() as c: return [{"usuario": r.usuario, "rol": r.rol, "correo": r.correo or "", "activo": bool(r.activo)} for r in c.execute(select(U).order_by(U.c.id))]

@admin.post("/api/admin/usuarios")
def nuevo(n: Nuevo, request: Request, u=Depends(solo_admin)):
    try: crear_usuario(n.usuario, n.clave, n.rol, n.correo)
    except Exception as e: raise HTTPException(400, str(e))
    reg(request, u["usuario"], "usuario_creado", f"{n.usuario.strip().lower()} · rol {n.rol}")
    return {"ok": True}

@admin.post("/api/admin/usuarios/{usuario}/estado")
def estado(usuario: str, activo: bool, request: Request, u=Depends(solo_admin)):
    k = usuario.strip().lower()
    if k == u["usuario"]: raise HTTPException(400, "No puedes cambiar el estado de tu propio usuario")
    with engine.begin() as c: n = c.execute(U.update().where(U.c.usuario == k).values(activo=activo)).rowcount
    if not n: raise HTTPException(404, "El usuario no existe")
    reg(request, u["usuario"], "usuario_activado" if activo else "usuario_desactivado", k)
    return {"ok": True}

def enviar_seguro(para, asunto, texto):
    try: enviar(para, asunto, texto)
    except Exception as e: print("Error al enviar el correo:", e)

@admin.post("/api/olvide")
def olvide(d: Olvide, request: Request, tareas: BackgroundTasks):
    msg = {"ok": True, "mensaje": "Si el correo está registrado enviamos un enlace para cambiar la contraseña. Vence en 30 minutos."}
    correo = d.correo.strip().lower()[:200]; ahora = datetime.utcnow()
    with engine.connect() as c:
        r = c.execute(select(U).where(U.c.correo == correo)).first()
        n = c.execute(select(func.count()).select_from(R).where(R.c.usuario_id == r.id, R.c.creado > ahora - timedelta(hours=1))).scalar() if r else 0
    if not r or not r.activo:
        reg(request, "desconocido", "recuperacion_sin_cuenta", correo); return msg
    if n >= 3:
        reg(request, r.usuario, "recuperacion_limite", "Más de 3 solicitudes en una hora"); return msg
    tok = secrets.token_urlsafe(32)
    with engine.begin() as c:
        c.execute(R.insert().values(usuario_id=r.id, token_hash=hashlib.sha256(tok.encode()).hexdigest(), creado=ahora, expira=ahora + timedelta(minutes=30), usado=False))
    base = (os.getenv("BASE_URL") or str(request.base_url)).rstrip("/")
    texto = (f"Hola,\n\nRecibimos una solicitud para cambiar la contraseña del usuario {r.usuario} en el portal de datos del INE.\n\n"
             f"Abre este enlace para elegir una contraseña nueva. Vence en 30 minutos y solo se puede usar una vez:\n{base}/admin#reset={tok}\n\n"
             "Si no fuiste tú ignora este mensaje y tu contraseña seguirá igual.")
    tareas.add_task(enviar_seguro, r.correo, "Recuperación de contraseña · Portal INE", texto)
    reg(request, r.usuario, "recuperacion_solicitada"); return msg

@admin.post("/api/restablecer")
def restablecer(d: Restab, request: Request):
    h = hashlib.sha256(d.token.strip().encode()).hexdigest()
    with engine.connect() as c:
        r = c.execute(select(R).where(R.c.token_hash == h)).first()
        u = c.execute(select(U).where(U.c.id == r.usuario_id)).first() if r else None
    if not r or not u or r.usado or r.expira < datetime.utcnow():
        reg(request, "desconocido", "restablecer_invalido"); raise HTTPException(400, "El enlace no es válido o ya venció. Pide uno nuevo.")
    if len(d.clave) < 10 or d.clave.lower() == u.usuario: raise HTTPException(400, "La contraseña debe tener al menos 10 caracteres y no ser igual al usuario")
    with engine.begin() as c:
        c.execute(U.update().where(U.c.id == u.id).values(clave_hash=hashear(d.clave)))
        c.execute(R.update().where(R.c.usuario_id == u.id).values(usado=True)); c.execute(A.delete().where(A.c.usuario == u.usuario))
    reg(request, u.usuario, "clave_restablecida", "Por enlace de correo"); return {"ok": True}

@admin.get("/api/admin/bitacora")
def bitacora(u=Depends(solo_admin)):
    with engine.connect() as c: filas = list(c.execute(select(B).order_by(B.c.id.desc()).limit(200)))
    return [{"fecha": (r.fecha - timedelta(hours=6)).strftime("%d/%m/%Y %H:%M:%S"), "usuario": r.usuario, "accion": r.accion, "detalle": r.detalle or "", "ip": r.ip or ""} for r in filas]

def tiene(tabla): return inspect(engine).has_table(tabla)
def contar(tabla):
    if not tiene(tabla): return 0
    with engine.connect() as c: return c.execute(text(f"SELECT COUNT(*) FROM {tabla}")).scalar()
def ultima(slug):
    with engine.connect() as c: r = c.execute(select(L.c.fecha).where(L.c.slug == slug).order_by(L.c.id.desc())).first()
    return r[0].strftime("%d/%m/%Y") if r else None
ESPECIAL = {"indicadores": {"nombre": "Indicadores generales por sexo", "apartado": "Género", "icono": "📊", "tabla": "indicador",
    "desc": "Indicadores cargados con las plantillas por tema, año, departamento y sexo.", "requeridas": REQ, "url": "/static/indicadores.html"}}

def slugify(t):
    return re.sub(r"\W+", "-", unicodedata.normalize("NFKD", str(t).strip().lower()).encode("ascii", "ignore").decode()).strip("-")[:50] or "datos"

def conjunto(slug):
    with engine.connect() as c: r = c.execute(select(Cj).where(Cj.c.slug == slug)).first()
    return dict(r._mapping) if r else None

@app.get("/api/catalogo")
def catalogo():
    out = [{"slug": k, "nombre": P["nombre"], "apartado": P["apartado"], "desc": P["desc"], "icono": P["icono"], "filas": contar(P["tabla"]),
            "actualizado": ultima(k), "requeridas": P.get("requeridas", []), "url": P.get("url") or f"/static/apartado.html?slug={k}"}
           for k, P in {**pf.PERFILES, **ESPECIAL}.items()]
    ic = {n: i for _, n, i in pf.CATEGORIAS}
    with engine.connect() as c: libres = [dict(r._mapping) for r in c.execute(select(Cj))]
    for r in libres:
        out.append({"slug": r["slug"], "nombre": r["nombre"], "apartado": r["categoria"], "desc": r["descripcion"] or "", "icono": ic.get(r["categoria"], "📄"),
                    "filas": contar(r["tabla"]), "actualizado": ultima(r["slug"]), "requeridas": [], "libre": True, "url": f"/static/apartado.html?slug={r['slug']}"})
    return out

def ine_cat():
    try: return json.load(open(os.path.join(BASE, "catalogo_ine.json"), encoding="utf-8"))
    except Exception: return {}

@app.get("/api/ine")
def ine(): return ine_cat()

@app.get("/api/categorias")
def categorias():
    n = {k: len(v) for k, v in ine_cat().items()}
    for x in catalogo():
        if x["filas"] and x["slug"] not in pf.PERFILES: n[x["apartado"]] = n.get(x["apartado"], 0) + 1
    return [{"slug": s, "nombre": nm, "icono": ic, "conjuntos": n.get(nm, 0)} for s, nm, ic in pf.CATEGORIAS]

@app.get("/api/apartado/{slug}")
def apartado(slug: str, request: Request):
    P = pf.PERFILES.get(slug)
    if not P:
        cj = conjunto(slug)
        if not cj: raise HTTPException(404, "Apartado no existe")
        q = dict(request.query_params)
        return pf.construir_libre(cj["nombre"], cj["categoria"], cj["descripcion"], pd.read_sql_table(cj["tabla"], engine), q, q.get("medida"))
    if not contar(P["tabla"]): return {"vacio": True, "nombre": P["nombre"]}
    q = dict(request.query_params)
    return pf.construir(slug, pd.read_sql_table(P["tabla"], engine), q, q.get("medida"))

@app.get("/api/descargar/{slug}")
def descargar(slug: str, formato: str = "xlsx"):
    if slug == "indicadores": df = todo()
    elif conjunto(slug): df = pd.read_sql_table(conjunto(slug)["tabla"], engine)
    elif slug in pf.PERFILES and contar(pf.PERFILES[slug]["tabla"]):
        P = pf.PERFILES[slug]; df = P["etiquetar"](pd.read_sql_table(P["tabla"], engine))
    else: raise HTTPException(404, "Sin datos para descargar")
    b = io.BytesIO()
    if formato == "csv":
        b.write(df.to_csv(index=False).encode("utf-8-sig")); mt, ext = "text/csv", "csv"
    else:
        df.to_excel(b, index=False); mt, ext = XL, "xlsx"
    b.seek(0)
    return StreamingResponse(b, media_type=mt, headers={"Content-Disposition": f"attachment; filename={slug}.{ext}"})

def cargar_archivo(slug, raw, nombre, modo="reemplazar", usuario="sistema"):
    P = pf.PERFILES[slug]
    if nombre.lower().endswith(".csv"):
        try: df = pd.read_csv(io.BytesIO(raw))
        except UnicodeDecodeError: df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
    else: df = pd.read_excel(io.BytesIO(raw))
    df = P["limpiar"](df)
    df.to_sql(P["tabla"], engine, if_exists="replace" if modo == "reemplazar" else "append", index=False, chunksize=2000)
    with engine.begin() as c: c.execute(L.insert().values(slug=slug, filas=len(df), archivo=nombre[:200], usuario=usuario, fecha=datetime.utcnow()))
    return len(df)

@admin.post("/api/admin/cargar/{slug}")
async def cargar(request: Request, slug: str, archivo: UploadFile = File(...), modo: str = Form("agregar"), u=Depends(quien)):
    if slug not in pf.PERFILES: raise HTTPException(404, "Apartado no existe")
    if modo == "reemplazar" and u["rol"] != "admin": raise HTTPException(403, "Solo el administrador puede reemplazar una base")
    try: n = cargar_archivo(slug, await archivo.read(), archivo.filename, modo, u["usuario"])
    except Exception as e: raise HTTPException(400, str(e))
    reg(request, u["usuario"], "carga_" + modo, f"{slug} · {archivo.filename} · {n} filas")
    return {"insertadas": n}

@app.middleware("http")
async def sin_cache(request: Request, call_next):
    r = await call_next(request)
    if not request.url.path.startswith("/api"): r.headers["Cache-Control"] = "no-cache, must-revalidate"
    return r

@app.get("/static/admin.html")
def admin_viejo(): return RedirectResponse("/admin")

@app.get("/api/version")
def version(): return {"version": 3, "modo_publico": PUBLIC}

def cols_limpias(cols):
    out = []
    for c in cols:
        k = re.sub(r"\W+", "_", unicodedata.normalize("NFKD", str(c).strip().lower()).encode("ascii", "ignore").decode()).strip("_") or "col"
        b, i = k, 2
        while k in out: k = f"{b}_{i}"; i += 1
        out.append(k)
    return out

@admin.post("/api/admin/libre")
async def libre(request: Request, archivo: UploadFile = File(...), categoria: str = Form(...), nombre: str = Form(...), descripcion: str = Form(""), u=Depends(quien)):
    if categoria not in [n for _, n, _ in pf.CATEGORIAS]: raise HTTPException(400, "Apartado no válido")
    if not nombre.strip(): raise HTTPException(400, "Escribe un nombre para el conjunto de datos")
    raw = await archivo.read(); base = "libre-" + slugify(nombre); slug, n = base, 2
    while conjunto(slug) or slug in pf.PERFILES: slug = f"{base}-{n}"; n += 1
    tabla = "d_" + slug.replace("-", "_")
    try:
        if archivo.filename.lower().endswith(".csv"):
            try: df = pd.read_csv(io.BytesIO(raw))
            except UnicodeDecodeError: df = pd.read_csv(io.BytesIO(raw), encoding="latin-1")
        else: df = pd.read_excel(io.BytesIO(raw))
        df = df.dropna(how="all"); df.columns = cols_limpias(df.columns)
        if df.empty: raise ValueError("El archivo no tiene filas")
        df.to_sql(tabla, engine, if_exists="replace", index=False, chunksize=2000)
    except Exception as e: raise HTTPException(400, str(e))
    with engine.begin() as c:
        c.execute(Cj.insert().values(slug=slug, nombre=nombre.strip()[:200], categoria=categoria, descripcion=descripcion[:500], tabla=tabla, fecha=datetime.utcnow()))
        c.execute(L.insert().values(slug=slug, filas=len(df), archivo=archivo.filename[:200], usuario=u["usuario"], fecha=datetime.utcnow()))
    reg(request, u["usuario"], "conjunto_creado", f"{slug} · {categoria} · {len(df)} filas")
    return {"insertadas": len(df), "slug": slug}

@admin.delete("/api/admin/libre/{slug}")
def borrar_libre(slug: str, request: Request, u=Depends(solo_admin)):
    reg(request, u["usuario"], "conjunto_borrado", slug)
    cj = conjunto(slug)
    if not cj: raise HTTPException(404, "No existe")
    with engine.begin() as c:
        c.execute(text(f"DROP TABLE IF EXISTS {cj['tabla']}")); c.execute(Cj.delete().where(Cj.c.slug == slug))
    return {"ok": True}

@app.get("/")
def home(): return RedirectResponse("/static/index.html")
if not PUBLIC: app.include_router(admin)
app.mount("/static", StaticFiles(directory=os.path.join(BASE, "static")), name="static")
