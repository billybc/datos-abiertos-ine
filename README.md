# Portal Estadístico Interactivo · Datatón INE 2026

**Equipo:** Hackspace  
**Categoría:** 2 · Tecnológica y ciencias de datos  
**Evento:** Datatón INE 2026 — Instituto Nacional de Estadística (INE), Guatemala  

---

## 1. Integrantes del Equipo (Hackspace)

* **Billy Eduardo Cardona López**
* **Jessica Valezka Cardona López**
* **Joshua Abinadi Cirilo Alegría**

---

## 2. Problema que resuelve y usuarios a quienes está dirigida

Las bases de datos estadísticas publicadas por el Instituto Nacional de Estadística (INE) de Guatemala constituyen un activo estratégico para el país, pero suelen distribuirse en múltiples archivos planos (`.xls`, `.xlsx`) por año, hoja o desglose temático, lo que dificulta su exploración rápida, comparación interanual y visualización por parte de usuarios sin conocimientos avanzados de programación o análisis estadístico.

**Solución:**  
Desarrollamos una plataforma web interactiva de consulta, visualización, análisis espacial y descarga estandarizada que unifica las series históricas del INE en tableros dinámicos con filtros multidimensionales, indicadores clave (KPIs), mapas coropléticos municipales, mapas de calor y exportación inmediata en Excel y CSV, respetando fielmente los catálogos, unidades de medida y definiciones metodológicas oficiales del INE.

**Usuarios objetivo:**
* **Ciudadanía general, estudiantes y periodistas de datos:** consulta visual inmediata sin necesidad de descargar ni procesar hojas de cálculo complejas.
* **Investigadores, academia y analistas económicos:** comparación interanual, análisis de precios (CBA/IPC) y descarga limpia de series consolidadas.
* **Equipo técnico del INE:** panel administrativo con motor ETL configurable para incorporar nuevos años o conjuntos de datos en minutos sin modificar el código fuente.

---

## 3. Arquitectura general y tecnologías empleadas

El sistema sigue una arquitectura modular cliente-servidor basada en estándares abiertos y software libre:

* **Backend y API REST:** Python 3.11+ con **FastAPI** y **Uvicorn** para el enrutamiento de vistas, consultas filtradas y generación de descargas dinámicas.
* **Motor ETL y Procesamiento Estadístico:** **Pandas** y **OpenPyXL / xlrd** mediante perfiles declarativos (`app/perfiles.py`) que normalizan columnas, aplican diccionarios oficiales de códigos (`diccionarios.json`, `mun_codigos.json`) y evitan distorsiones al agregar precios unitarios o índices.
* **Persistencia de Datos:** **SQLAlchemy** sobre **SQLite** (`ine.db`), con soporte para carga incremental por año o por vista (`actualizar`, `agregar`, `reemplazar`) y bitácora de cargas.
* **Frontend e Identidad Visual:** HTML5, CSS3 y JavaScript puro con identidad institucional del **Kit de Diseño Datatón INE 2026** (tipografía **Ubuntu Sans**, paleta institucional `#004080` / `#0080ff` y logotipos oficiales del INE).

### Librerías de terceros y licencias
Todas las dependencias empleadas son de código abierto y sin costo de licenciamiento:
* **FastAPI** (Licencia MIT)
* **Uvicorn** (Licencia BSD-3-Clause)
* **SQLAlchemy** (Licencia MIT)
* **Pandas** (Licencia BSD-3-Clause)
* **OpenPyXL** (Licencia MIT)
* **xlrd** (Licencia BSD)

---

## 4. Estructura del proyecto

```text
dataton-ine/
├── app/
│   ├── main.py                 # Servidor FastAPI, API REST, autenticación y motor de descargas
│   ├── perfiles.py             # Perfiles ETL, reglas de limpieza, KPIs y configuración de gráficas
│   ├── catalogo_ine.json       # Catálogo oficial de conjuntos de datos del INE por categoría
│   ├── diccionarios.json       # Catálogos de códigos (vehículos, eventos, colores, etc.)
│   ├── mun_codigos.json        # Códigos oficiales de municipios de Guatemala
│   ├── admin/
│   │   └── admin.html          # Panel de administración para carga de archivos y diccionarios
│   └── static/
│       ├── index.html          # Portada principal y buscador global
│       ├── categoria.html      # Listado de conjuntos por temática
│       ├── apartado.html       # Tablero interactivo (KPIs, gráficas, mapa de calor y descargas)
│       ├── descargas.html      # Centro unificado de descarga de bases
│       ├── style.css           # Estilos institucionales con tipografía Ubuntu Sans
│       ├── brand/              # Logotipos oficiales INE y fuentes Ubuntu Sans
│       └── geo/                # Cartografía GeoJSON municipal de Guatemala
├── datos/                      # Archivos fuente oficiales descargados del portal del INE
├── cargar_iniciales.py         # Script de carga masiva inicial hacia la base de datos
├── crear_usuario.py            # Utilidad CLI para crear usuarios administradores
├── requirements.txt            # Dependencias exactas del entorno Python
└── README.md                   # Documentación técnica del proyecto