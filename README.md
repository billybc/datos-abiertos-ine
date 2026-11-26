Portal Estadístico Interactivo · Datatón INE 2026

Equipo: Hackspace

Integrantes: Billy Eduardo Cardona López · Jessica Valezka Cardona López · Joshua Abinadi Cirilo Alegría

Categoría: 2 · Tecnológica y ciencias de datos (Datatón INE 2026)

Repositorio Oficial: https://github.com/billybc/datos-abiertos-ine

Problema que resuelve y usuarios a quienes está dirigida

Las bases de datos estadísticas publicadas por el Instituto Nacional de Estadística (INE) de Guatemala constituyen un activo estratégico para el país; sin embargo, suelen distribuirse en múltiples archivos planos independientes (.xls, .xlsx) separados por año, hoja de cálculo o desglose temático. Esto dificulta su exploración rápida, la comparación interanual y su comprensión por parte de usuarios sin conocimientos avanzados de programación o análisis estadístico.

Solución desarrollada:

Construimos una plataforma web interactiva de consulta, visualización, análisis geoespacial y descarga estandarizada que unifica las series históricas del INE en tableros dinámicos con filtros multidimensionales, indicadores clave (KPIs), mapas coropléticos municipales, mapas de calor y exportación inmediata en Excel y CSV, respetando fielmente los catálogos oficiales, unidades de medida y definiciones metodológicas del INE.

Usuarios a quienes está dirigida:

Ciudadanía general, estudiantes y periodistas de datos: consulta visual inmediata sin necesidad de descargar ni procesar hojas de cálculo complejas.

Investigadores, academia y analistas económicos: comparación interanual, análisis detallado de precios (Canasta Básica Alimentaria e IPC) y descarga limpia de series consolidadas.

Equipo técnico del INE: panel administrativo (/admin) con motor ETL configurable para incorporar nuevos años o conjuntos de datos en minutos sin modificar el código fuente.

Arquitectura general y tecnologías empleadas

El sistema sigue una arquitectura modular cliente-servidor basada en estándares abiertos y software libre:

Backend y API REST: Python 3.10+ con FastAPI y Uvicorn para el enrutamiento de vistas, consultas filtradas dinámicamente y generación de exportaciones en Excel/CSV.

Motor ETL y Procesamiento Estadístico: Pandas, OpenPyXL y xlrd mediante perfiles declarativos (app/perfiles.py) que normalizan columnas, aplican diccionarios oficiales de códigos (diccionarios.json, mun_codigos.json), unifican vistas multi-hoja y evitan distorsiones matemáticas al agregar precios unitarios o índices.

Persistencia de Datos: SQLAlchemy sobre SQLite (ine.db), con soporte para carga incremental por año o por vista (actualizar, agregar, reemplazar) y bitácora administrativa de cargas.

Frontend e Identidad Visual: HTML5, CSS3 y JavaScript con identidad institucional del Kit de Diseño Datatón INE 2026 (tipografía oficial Ubuntu Sans, paleta institucional #004080 / #0080ff y logotipos oficiales del INE).

Librerías de terceros y licencias

Todas las dependencias empleadas son de código abierto y sin costo de licenciamiento:

FastAPI — Licencia MIT

Uvicorn — Licencia BSD-3-Clause

SQLAlchemy — Licencia MIT

Pandas — Licencia BSD-3-Clause

OpenPyXL — Licencia MIT

xlrd — Licencia BSD

Estructura del proyecto

datos-abiertos-ine/
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
│       ├── indicadores.html    # Vista de indicadores estadísticos
│       ├── style.css           # Estilos institucionales con tipografía Ubuntu Sans
│       ├── brand/              # Logotipos oficiales INE y fuentes Ubuntu Sans
│       └── geo/                # Cartografía GeoJSON municipal de Guatemala
├── datos/                      # Archivos fuente oficiales descargados del portal del INE
├── cargar_iniciales.py         # Script de carga masiva inicial hacia la base de datos
├── crear_usuario.py            # Utilidad CLI para crear usuarios administradores
├── requirements.txt            # Dependencias exactas del entorno Python
├── SEGURIDAD.md                # Lineamientos de seguridad y confidencialidad
└── README.md                   # Documentación oficial del proyecto


Instrucciones de instalación y uso

Requisitos previos

Python 3.10 o superior.

Git instalado.

1. Clonar el repositorio e instalar dependencias

git clone https://github.com/billybc/datos-abiertos-ine.git
cd datos-abiertos-ine
python -m venv .venv


Activar el entorno virtual:

En Windows (PowerShell):

.\.venv\Scripts\Activate.ps1


En Linux / macOS:

source .venv/bin/activate


Instalar dependencias:

pip install -r requirements.txt
pip install xlrd


2. Cargar los conjuntos de datos oficiales del INE

Con los archivos Excel oficiales del INE ubicados en la carpeta datos/, ejecuta:

python cargar_iniciales.py


3. Crear un usuario administrador (para acceso al panel /admin)

Por seguridad y cumplimiento de los lineamientos del Datatón INE 2026, el repositorio no incluye contraseñas fijas ni credenciales expuestas en el código fuente. Para habilitar el acceso al panel de administración local, ejecuta en la terminal:

python crear_usuario.py


El asistente interactivo solicitará:

Nombre de usuario (ej. admin o jurado_ine).

Contraseña (mínimo 8 caracteres; se almacena cifrada en ine.db, nunca en texto plano).

Correo electrónico (opcional).

4. Iniciar y usar la aplicación

uvicorn app.main:app --host 127.0.0.1 --port 8001 --reload


Portal ciudadano (http://127.0.0.1:8001): Permite buscar conjuntos de datos, navegar por las categorías oficiales del INE, aplicar filtros cruzados, visualizar KPIs, mapas municipales y mapas de calor, y descargar series filtradas en Excel o CSV.

Panel administrativo (http://127.0.0.1:8001/admin): Inicia sesión con el usuario creado en el paso 3 para cargar nuevos archivos Excel/CSV (actualizar, agregar o reemplazar), administrar diccionarios de códigos y revisar la bitácora de cargas.

Conjuntos de datos utilizados

Todos los datos empleados son de acceso público y fueron obtenidos del portal oficial de datos abiertos del Instituto Nacional de Estadística (INE) (https://datos.ine.gob.gt / https://www.ine.gob.gt), descargados entre el 24 y el 26 de noviembre de 2026:

Accidentes de tránsito · Fallecidos y lesionados (PNC):

Fuente: INE / Policía Nacional Civil (accidentes-de-transito-fallecidos-y-lesionados).

Archivos procesados: Series anuales 2024–2025 (base-de-datos-fallecidos-y-lesionados-pnc-*.xlsx).

Fecha de descarga: 24 de noviembre de 2026.

Accidentes de tránsito · Hechos (PNC):

Fuente: INE / Policía Nacional Civil (accidentes-de-transito-hechos).

Archivos procesados: Series anuales 2024–2025 (base-de-datos-hechos-de-transito-pnc-*.xlsx).

Fecha de descarga: 24 de noviembre de 2026.

Accidentes de tránsito · Vehículos involucrados (PNC):

Fuente: INE / Policía Nacional Civil (accidentes-de-transito-vehiculos-involucrados).

Archivos procesados: Series anuales 2021–2025 (vehiculos-involucrados-*.xlsx, base-de-datos-vehiculos-involucrados-pnc-*.xlsx).

Fecha de descarga: 24 de noviembre de 2026.

Construcciones particulares a nivel departamental (Guatemala):

Fuente: INE (construcciones-particulares-nivel-departamental).

Archivo procesado: bd-construcciones-particulares-departamento-de-guatemala.xlsx.

Fecha de descarga: 24 de noviembre de 2026.

Costos de la Canasta Ampliada (CA) y Canasta Básica Alimentaria (CBA) Urbana y Rural:

Fuente: INE (costos-de-la-cba-urbana-y-rural).

Archivos procesados: historico-cbar_es_2024-2026.xlsx y costo-cba-percapita_r.xlsx (unificados en un único conjunto oficial del catálogo mediante filtro de vista: 13 grupos alimenticios y 60 productos con precios unitarios de mercado en quetzales y aporte energético diario).

Fecha de descarga: 25 de noviembre de 2026.

Índice de Precios al Consumidor (IPC) Base Anual 2024 = 100.00:

Fuente: INE (ipc-por-producto-ano-2024-100-0).

Archivos procesados: base-de-datos-ipc-ano-2025_es.xls (por producto y 8 regiones) e ipc_divgasto_25.xlsx (por división de gasto), integrados bajo un único conjunto oficial del catálogo del INE.

Fecha de descarga: 26 de noviembre de 2026.

Limitaciones y posibles mejoras

Limitaciones actuales: La carga de nuevos conjuntos fuera de los perfiles predefinidos utiliza un motor de inferencia automática (construir_libre) que prioriza variables numéricas y categóricas generales; asimismo, la base de datos SQLite local está orientada a despliegues ligeros y demostraciones institucionales.

Posibles mejoras:

Conexión directa mediante API/CKAN al portal datos.ine.gob.gt para sincronización automática de nuevas publicaciones.

Migración opcional a PostgreSQL + PostGIS para consultas geoespaciales de alta concurrencia.

Incorporación de perfiles analíticos dedicados adicionales para comercio exterior, estadísticas vitales y encuestas de empleo (ENEI).

Seguridad, confidencialidad y uso de Inteligencia Artificial

Secreto estadístico: En cumplimiento estricto de la Ley Orgánica del INE, la plataforma presenta exclusivamente cifras agregadas, distribuciones, promedios e índices. No realiza cruces ni inferencias orientadas a identificar personas, hogares o empresas individuales.

Seguridad de credenciales: No se almacenan contraseñas ni llaves privadas en el código fuente; los accesos administrativos se gestionan localmente mediante contraseñas cifradas generadas con crear_usuario.py y tokens firmados en memoria.

Uso de Inteligencia Artificial: En conformidad con los lineamientos del Datatón INE 2026, el equipo Hackspace declara que se utilizaron herramientas de inteligencia artificial generativa como apoyo para la estructuración de funciones de limpieza ETL en Pandas, pruebas automatizadas y redacción de documentación técnica. Todo el código y validación estadística han sido revisados y verificados por los integrantes del equipo.

Integrantes del Equipo (Hackspace)

Billy Eduardo Cardona López

Jessica Valezka Cardona López

Joshua Abinadi Cirilo Alegría