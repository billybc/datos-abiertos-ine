# Portal de datos abiertos del INE

Datatón INE 2026 · Categoría 2: Herramienta tecnológica para análisis de datos

## Problema y usuarios
Las bases que publica datos.ine.gob.gt vienen en Excel y CSV con códigos que solo entiende quien ya conoce los diccionarios, así que una persona que consulta tiene que descargar, traducir los códigos y armar sus propios gráficos. Del otro lado el personal que publica no tiene un lugar sencillo para subir una base nueva y verla convertida en estadísticas.

Este portal convierte esas bases en un tablero que se entiende a primera vista y le da al personal del INE un panel con usuario y contraseña para cargar bases sin programar.

Usuarios a quienes está dirigido:
- Ciudadanía, periodistas, estudiantes e investigadores que consultan estadísticas
- Personal del INE que carga y publica bases
- Administradores que gestionan usuarios y revisan la bitácora

## Qué hace
- Portada con las 21 categorías de datos del INE, buscador y cantidad de conjuntos por categoría
- Tablero por apartado con filtros por mes, departamento, sexo y más, mapa de departamentos y gráficos
- En todos los gráficos por sexo las mujeres van en rosado, los hombres en azul y las personas no identificadas en gris
- Cuatro apartados con estadísticas completas: accidentes de tránsito en sus tres bases, que son fallecidos y lesionados, hechos y vehículos involucrados desde 2021 hasta 2025, y construcciones particulares del departamento de Guatemala
- Mapa de Guatemala por municipio con los 340 municipios coloreados según la cantidad, que se acerca al departamento elegido y resalta el municipio seleccionado
- Mapa de calor que muestra dónde se concentran los casos y que el usuario arma eligiendo qué va en las filas y qué en las columnas
- Pestaña de datos y descargas con una fila por año, información adicional y flujo de actividad de las cargas
- Catálogo de 95 conjuntos publicados por el INE con enlace a su ficha para descargarlos
- Descarga en Excel y CSV de las bases cargadas con los códigos ya convertidos a nombres
- Panel de carga donde se suben varios archivos a la vez, cada año se actualiza sin duplicar y los gráficos aparecen solos
- Editor de nombres para los códigos que traen las bases y opción para crear un conjunto nuevo en cualquier categoría con estadísticas automáticas
- Seguridad con login, roles, recuperación de contraseña por correo, bloqueo por intentos fallidos y bitácora

## Arquitectura y tecnologías
```
Navegador con HTML y Chart.js  →  FastAPI en Python  →  SQLAlchemy y pandas  →  SQLite en local o PostgreSQL en la nube
```
- `app/main.py` servidor, API, login y bitácora
- `app/perfiles.py` formato de cada base, conversión de códigos y gráficos
- `app/static/` páginas públicas
- `app/admin/` panel de carga
- `app/catalogo_ine.json` catálogo de los 95 conjuntos del INE
- `app/diccionarios.json` nombres de los códigos que faltan
- `datos/` bases de partida descargadas del INE

Se eligió Python por su ecosistema de análisis de datos y PostgreSQL por ser abierta y sin costo de licencia.

## Instalación y uso
Requisitos: Python 3.11 o superior y Git.
```
git clone https://github.com/billybc/datos-abiertos-ine.git
cd datos-abiertos-ine
pip install -r requirements.txt
python cargar_iniciales.py
python crear_usuario.py
python -m uvicorn app.main:app --port 8001
```
- Portal público en http://localhost:8001
- Panel de carga en http://localhost:8001/admin con el usuario creado en el paso anterior
- Para recuperar contraseñas por correo se copia `.env.example` como `.env` y se completan las variables SMTP. Sin ellas el enlace aparece en la consola del servidor en modo local

## Despliegue en la nube
Se definen estas variables de entorno: `DATABASE_URL` con la dirección de PostgreSQL, `SECRET_KEY` con una clave larga y aleatoria, `COOKIE_SECURE=1`, `BASE_URL` con la dirección pública y `PUBLIC_ONLY=1` para apagar el panel en el servidor público. Incluye un `Dockerfile`. Después se corre `python cargar_iniciales.py` y `python crear_usuario.py` apuntando a esa base.

## Conjuntos de datos utilizados
| Base | Fuente | Archivos en `datos/` | Fecha de descarga |
|---|---|---|---|
| Accidentes de tránsito, fallecidos y lesionados | datos.ine.gob.gt/dataset/accidentes-de-transito-fallecidos-y-lesionados | `base-de-datos-fallecidos-y-lesionados-pnc-2024.xlsx` y `2025` | [COMPLETAR] |
| Accidentes de tránsito, hechos | datos.ine.gob.gt/dataset/accidentes-de-transito-hechos | `base-de-datos-hechos-de-transito-pnc-2024.xlsx` y `2025` | [COMPLETAR] |
| Accidentes de tránsito, vehículos involucrados | datos.ine.gob.gt/dataset/accidentes-de-transito-vehiculos-involucrados | cinco archivos de 2021 a 2025 | [COMPLETAR] |
| Construcciones particulares a nivel departamental | datos.ine.gob.gt/dataset/construcciones-particulares-nivel-departamental | `bd-construcciones-particulares-departamento-de-guatemala.xlsx` | [COMPLETAR] |

El catálogo de 95 conjuntos se tomó de las páginas de categorías de datos.ine.gob.gt el [COMPLETAR].

Todas las cifras tienen como fuente al Instituto Nacional de Estadística. Los códigos de departamento, sexo, mes, día de la semana y condición se tradujeron con las claves estándar y se comprobó el día de la semana contra el calendario. Los nombres del tipo de vehículo, tipo de evento, marca, color y otros campos se muestran como código hasta que el administrador los escribe en el panel con el diccionario oficial del INE.

## Uso de inteligencia artificial generativa
Se usó Claude de Anthropic como asistente de código para generar la primera versión del sistema, y el equipo revisó, probó y puede explicar y defender todo el código presentado.

## Seguridad y secreto estadístico
- La herramienta no identifica personas, hogares ni empresas porque trabaja con las bases públicas del INE que no traen nombres y muestra solo cifras agrupadas
- No hay credenciales ni claves en el código y todo se configura por variables de entorno
- Las contraseñas se guardan cifradas, la sesión se invalida al cambiar la contraseña y hay bloqueo de 15 minutos tras 5 intentos fallidos
- Una bitácora registra quién inicia sesión, carga, borra o exporta
- El detalle está en `SEGURIDAD.md`

## Componentes de terceros
| Componente | Licencia |
|---|---|
| FastAPI | MIT |
| Uvicorn | BSD 3 |
| SQLAlchemy | MIT |
| pandas | BSD 3 |
| openpyxl | MIT |
| python-docx | MIT |
| python-multipart | Apache 2.0 |
| psycopg2-binary | LGPL |
| Chart.js | MIT |
| Límites de departamentos y municipios | Ministerio de Finanzas Públicas, repositorio minfin-bi/Mapas-TopoJSON-Guatemala, sin licencia indicada en el repositorio |
| Montserrat | SIL Open Font License |

## Mapa
Los límites vienen de los archivos TopoJSON de `datos/mapa/` y `python preparar_mapa.py` los convierte en `app/static/geo/gt_paths.json` y en la lista de nombres de los 340 municipios `app/mun_codigos.json`. Los códigos de municipio de ese mapa coinciden con los de las bases del INE.

## Limitaciones y posibles mejoras
- Solo dos apartados tienen formato propio con nombres, mapa y colores por sexo, los demás conjuntos cargados usan estadísticas automáticas con los códigos tal como vienen
- Falta completar el diccionario de tipo de vehículo y tipo de evento
- Falta doble factor de autenticación para administradores
- Falta una revisión de seguridad por parte del INE
- Mejoras previstas: más apartados con formato propio, mapa por municipio y carga programada desde la API de datos.ine.gob.gt

## Equipo
[COMPLETAR con los nombres de las y los integrantes]
