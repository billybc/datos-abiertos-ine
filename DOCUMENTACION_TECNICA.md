# Documentación técnica · Portal Estadístico Interactivo

**Equipo Hackspace · Datatón INE 2026 · Categoría 2 (Tecnológica y ciencias de datos)**
Repositorio: https://github.com/billybc/datos-abiertos-ine

---

## 1. Visión general

Aplicación web de una sola base de código (Python + HTML/JS puro) que carga archivos oficiales del INE, los normaliza con un **motor ETL declarativo** y los publica como tableros interactivos, mapas y descargas, junto con un panel administrativo protegido para que el INE incorpore nuevos años o conjuntos sin tocar el código.

```
 Excel/CSV del INE ──► limpiar() ──► SQLite (ine.db) ──► etiquetar() ──► construir() ──► API JSON ──► Tableros
   (datos/*.xls*)      perfiles.py    d_<conjunto>        códigos→texto     KPIs/series     /api/...     (Chart.js)
                                                                                                          │
                                                                   Panel /admin (carga, usuarios, bitácora)┘
```

## 2. Estructura del repositorio

| Ruta | Función |
|---|---|
| `app/main.py` | Servidor FastAPI: API REST, autenticación, carga de archivos, descargas |
| `app/perfiles.py` | **Perfiles ETL**: limpieza, etiquetado, KPIs y gráficas de cada conjunto |
| `app/catalogo_ine.json` | Catálogo de conjuntos del INE por categoría (Precios = 11) |
| `app/diccionarios.json`, `app/mun_codigos.json` | Catálogos de códigos (tipo de vehículo, evento, municipios) |
| `app/correo.py` | Envío SMTP para recuperación de contraseña |
| `app/static/` | Vistas: `index`, `categoria`, `apartado`, `descargas`, `indicadores`, `style.css`, `brand/` (logos y Ubuntu Sans), `geo/` (GeoJSON) |
| `app/admin/admin.html` | Panel administrativo |
| `cargar_iniciales.py` | Carga masiva de `datos/` a la base |
| `crear_usuario.py` | Crea el primer administrador por consola |
| `.env.example` | Variables de entorno de ejemplo |

## 3. Motor ETL declarativo (`perfiles.py`)

Cada conjunto es una entrada del diccionario `PERFILES`. Agregar un conjunto nuevo es **escribir un perfil, no programar un módulo**:

| Clave del perfil | Qué define |
|---|---|
| `tabla` | Tabla SQLite destino (`d_transito`, `d_costos_cba`, …) |
| `requeridas` | Columnas mínimas; si faltan, la carga se rechaza con mensaje claro |
| `limpiar(df)` | Normaliza nombres de columna, tipos y filas inválidas |
| `etiquetar(df)` | Convierte códigos a texto legible (sexo, departamento, municipio, vehículo…) |
| `kpis(d)` | Indicadores de cabecera |
| `filtros`, `medidas` | Filtros disponibles y métricas seleccionables |
| `charts` | Lista de gráficas: `(id, título, tipo, dimensión, apilado, top)` |
| `calor`, `calor_def` | Dimensiones del mapa de calor y par por defecto |
| `multi_hoja`, `por_vista` | El libro trae varias hojas / el conjunto tiene vistas internas |

Perfiles incluidos: `transito`, `hechos`, `vehiculos`, `construcciones`, `costos-cba`, `ipc-2024`. Además, el panel permite **conjuntos libres**: se sube cualquier Excel/CSV/Word con tabla y el sistema detecta dimensiones y medidas (`construir_libre`).

### Reglas de rigor estadístico implementadas

1. **Precios e índices no se suman.** Precio unitario e índices (IPC) se **promedian**; los costos mensuales se **dividen entre el número de meses** del periodo, no se acumulan.
2. **Mapa de calor de costos**: cada celda es el promedio mensual (suma ÷ meses distintos), nunca la suma de varios años.
3. **Meses sin dato** en las líneas se envían como `null` (hueco), no como 0, para no dibujar caídas falsas.
4. **Niveles no mezclados**: por defecto CBA muestra «Grupos alimenticios (13)» y el IPC «Por División de Gasto»; los productos se consultan con el filtro de nivel de detalle.
5. **IPC**: el KPI usa el *Índice general oficial* del último mes cuando existe; si no, rotula explícitamente «promedio simple de los rubros».
6. **Formato**: precios y costos con 2 decimales (Q), índices con 2 decimales, conteos con 0 decimales (`dec` y `moneda` viajan en la respuesta de la API).

## 4. Base de datos (`ine.db`, SQLite)

El motor se elige con `DATABASE_URL`; sin ella se usa `ine.db` local. Para la nube se admite PostgreSQL.

| Tabla | Contenido |
|---|---|
| `d_transito`, `d_hechos`, `d_vehiculos` | Accidentes de tránsito (PNC): víctimas, hechos, vehículos |
| `d_construcciones` | Licencias de construcción particulares, depto. Guatemala |
| `d_costos_cba` | Costos de CBA (vistas: grupos y productos) |
| `d_ipc_2024` | IPC (vistas: división de gasto y producto/región) |
| `usuario` | `usuario`, `clave_hash` (PBKDF2-SHA256, 200 000 iteraciones, sal propia), `rol`, `activo`, `correo` |
| `carga` | Historial de cargas por conjunto (archivo, filas, usuario, fecha, modo) |
| `conjunto` | Conjuntos libres creados desde el panel |
| `diccionario` | Códigos editables desde el panel |
| `recuperacion` | Tokens de recuperación (solo hash, vencen en 30 min) |
| `intento` | Intentos fallidos de acceso (bloqueo persistente) |
| `bitacora` | Registro de acciones (solo lectura) |
| `indicador` | Tabla genérica de indicadores (carga por plantilla) |

> `ine.db` **no se sube a GitHub** (`.gitignore`): contiene usuarios. Se regenera con `python cargar_iniciales.py`.

### Modos de carga
- `actualizar`: borra los años presentes en el archivo y los vuelve a insertar (idempotente).
- `agregar`: añade filas sin borrar (series de precios mensuales).
- `reemplazar`: sustituye toda la tabla (solo rol `admin`).

## 5. API REST

**Públicas (solo cifras agregadas)**

| Método | Ruta | Descripción |
|---|---|---|
| GET | `/api/catalogo` | Conjuntos disponibles con filas, años y última actualización |
| GET | `/api/categorias` | Categorías y número de conjuntos del catálogo INE |
| GET | `/api/ine` | Catálogo oficial `catalogo_ine.json` |
| GET | `/api/apartado/{slug}` | Tablero completo: filtros, KPIs, gráficas, mapa y mapa de calor. Parámetros: columnas de filtro, `medida`, `f`, `c` |
| GET | `/api/actividad/{slug}` | Últimas cargas del conjunto |
| GET | `/api/descargar/{slug}?formato=xlsx\|csv&anio=` | Descarga de la base agregada/etiquetada |
| GET | `/api/diccionario` | Diccionario de códigos (CSV) |
| GET | `/api/filtros`, `/api/datos` | Consulta de la tabla genérica de indicadores |
| GET | `/api/version` | Versión y modo público |

**Administrativas (sesión requerida)**

| Método | Ruta | Rol |
|---|---|---|
| POST | `/api/login`, `/api/logout`; GET `/api/yo` | — |
| POST | `/api/olvide`, `/api/restablecer` | Recuperación por correo |
| POST | `/api/admin/cargar/{slug}` | admin / cargador |
| DELETE | `/api/admin/anio/{slug}/{anio}` | admin |
| POST | `/api/admin/libre` (crear conjunto libre) | admin / cargador |
| DELETE | `/api/admin/libre/{slug}` | admin |
| POST | `/api/admin/subir`; GET `/api/admin/plantillas`, `/api/admin/plantilla/{i}` | admin / cargador |
| GET | `/api/admin/exportar` | admin |
| DELETE | `/api/admin/limpiar` | admin |
| GET/POST | `/api/admin/usuarios`, POST `/api/admin/usuarios/{usuario}/estado` | admin |
| GET/POST | `/api/admin/diccionarios` | admin |
| GET | `/api/admin/bitacora` | admin |

## 6. Instalación y ejecución

```bash
git clone https://github.com/billybc/datos-abiertos-ine.git
cd datos-abiertos-ine
python -m venv .venv && source .venv/bin/activate     # Windows: .venv\Scripts\activate
pip install -r requirements.txt                       # incluye xlrd para los .xls del INE
python cargar_iniciales.py                            # crea ine.db desde datos/
python crear_usuario.py                               # crea el administrador (ver §8)
uvicorn app.main:app --port 8001
```

- Portal público: http://127.0.0.1:8001/
- Panel administrativo: http://127.0.0.1:8001/admin
- Docker: `docker build -t portal-ine . && docker run -p 8000:8000 portal-ine` (la base se carga con `cargar_iniciales.py` dentro del contenedor o con `DATABASE_URL`).

## 7. Manual de usuario (público)

1. **Portada**: buscador global y 21 categorías de datos del INE.
2. **Categoría**: lista los conjuntos oficiales; los que tienen datos cargados muestran «Ver estadísticas», Excel y CSV.
3. **Tablero de un conjunto** (pestañas):
   - *Resumen*: filtros (año, mes, departamento, municipio, etc.), KPIs y gráficas. Con **Limpiar filtros** se reinicia.
   - *Mapa de calor*: elegir dos dimensiones (p. ej. día de la semana × hora). En precios, la celda es el promedio mensual.
   - *Datos y descargas*: Excel/CSV por año o completo, diccionario de códigos, fuente y licencia, historial de cargas.
4. **Mapa municipal**: clic en un municipio para filtrar todo el tablero.
5. **Descargar bases**: centro unificado con todos los conjuntos.

## 8. Manual de administración y acceso al panel

### Crear el administrador
Por el Lineamiento de Seguridad del Datatón **no existen contraseñas en el código fuente**. Cada persona evaluadora genera su acceso local:

```bash
python crear_usuario.py
```
Solicita: **Usuario**, **Correo** (para recuperar contraseña), **Contraseña** (mínimo 10 caracteres, se pide dos veces y no se muestra en pantalla). La contraseña se guarda **cifrada con PBKDF2-SHA256 + sal** en la tabla `usuario` de `ine.db`; nunca en texto plano. Luego ingresar en **http://127.0.0.1:8001/admin**.

### Operaciones del panel
- **Cargar datos** a un conjunto existente: elegir archivo y modo (`actualizar`/`agregar`/`reemplazar`). Se validan las columnas requeridas.
- **Crear conjunto nuevo**: subir Excel/CSV/Word con tabla; aparece en su categoría con filtros y gráficas automáticas.
- **Borrar un año** de un conjunto (solo admin).
- **Diccionarios**: editar códigos de tipo de vehículo/evento.
- **Usuarios**: crear usuarios (rol `admin` o `cargador`) y activar/desactivar.
- **Bitácora**: inicios de sesión, cargas, borrados, exportaciones y cambios de usuarios.

### Variables de entorno (`.env`)
`DATABASE_URL`, `SECRET_KEY` (obligatoria en nube; sin ella se genera una al arrancar y las sesiones caducan al reiniciar), `COOKIE_SECURE`, `PUBLIC_ONLY=1` (apaga el panel), `TRUST_PROXY`, `BASE_URL`, `SMTP_*`.

## 9. Seguridad
Ver `SEGURIDAD.md`: PBKDF2, cookie HttpOnly/SameSite, bloqueo de 15 min tras 5 intentos, tokens de recuperación de un solo uso (30 min), bitácora de solo lectura, roles, modo `PUBLIC_ONLY`.

## 10. Verificación realizada
Totales cargados desde `datos/`: 55 771 víctimas, 17 282 hechos, 64 099 vehículos, 5 489 registros de construcciones (6 621 construcciones). Los KPIs de costos se verificaron contra los valores del archivo fuente (CBA rural: Q654.40 en enero 2024 y Q767.51 en octubre 2026).
