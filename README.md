# Herramienta Docente

Aplicación web local (Flask) para optimizar el trabajo de preparación de clases:

1. **Materiales interactivos**: genera una lección interactiva (con IA, a partir de texto/PDF/Word/URL
   que tú aportes) que cubre la práctica totalidad del contenido de origen, con 10 preguntas de
   autoevaluación por apartado y el resultado visible al terminar cada uno, y la empaqueta como
   **SCORM** para importar en Moodle. El número de apartados se calcula automáticamente según la
   extensión del contenido (aprox. uno cada 300 palabras); con textos largos la generación puede
   tardar uno o dos minutos, porque cada apartado se genera con una llamada independiente a la IA.
2. **Cuestionarios autoevaluables**: genera preguntas (opción múltiple, verdadero/falso, respuesta
   corta, completar huecos, emparejamiento) con IA, permite editarlas, y las exporta en formato
   **Moodle XML**.
3. **Cuaderno de evaluación**: importa las hojas de calificaciones exportadas del calificador de
   Moodle (una por evaluación) y genera informes individualizados por alumno y la nota final.

## Instalación (paso a paso, para cualquier ordenador)

Necesitas tener **Python 3.10 o superior** instalado. Si no lo tienes:
- Windows/Mac: descárgalo de https://www.python.org/downloads/ (en Windows, marca la casilla
  "Add Python to PATH" durante la instalación).
- Linux: normalmente ya viene instalado (`python3 --version` para comprobarlo).

**1. Descarga el código.** Con git:

```bash
git clone https://github.com/jesusbullfighter/herramienta-docente.git
```

(o, si no tienes git, entra en la página del repositorio en GitHub → botón verde **Code** →
**Download ZIP**, y descomprímelo).

**2. Entra en la carpeta del proyecto:**

```bash
cd herramienta-docente
```

**3. Crea un entorno virtual e instala las dependencias:**

```bash
python3 -m venv .venv
```

En Linux/Mac, actívalo con:

```bash
source .venv/bin/activate
```

En Windows (símbolo del sistema), sería `.venv\Scripts\activate` en su lugar. Luego, en cualquier
sistema:

```bash
pip install -r requirements.txt
```

**4. Configura tu propia clave de IA (gratis):**

```bash
cp .env.example .env
```

Edita el archivo `.env` que se acaba de crear y añade tu clave **gratuita** de la API de Google
Gemini en la línea `GEMINI_API_KEY=` (necesaria para "Materiales interactivos" y "Cuestionarios";
el "Cuaderno de evaluación" funciona sin ella). Se crea en un minuto, con tu propia cuenta de
Google, en https://aistudio.google.com/apikey — cada persona necesita la suya, no se comparte.

Si prefieres usar Claude (Anthropic, de pago) en vez de Gemini, configura `ANTHROPIC_API_KEY` y
pon `AI_PROVIDER=anthropic` en el `.env`.

## Arrancar la aplicación

Cada vez que quieras usarla, dentro de la carpeta del proyecto (y con el entorno activado, paso 3):

```bash
python app.py
```

Abre http://127.0.0.1:5000 en el navegador. Para cerrarla, vuelve a la terminal y pulsa Ctrl+C.

### Acceso directo en el menú de aplicaciones (opcional, solo Linux)

El repositorio incluye `launch.sh` y un icono para crear un lanzador en el menú de aplicaciones,
pero las rutas que trae están pensadas para el ordenador original. Para usarlo en otro Linux, edita
`launch.sh` y el archivo `.desktop` que crees en `~/.local/share/applications/` para que apunten a
la ruta real donde hayas descargado el proyecto en tu equipo.

## Uso en Moodle

- **Materiales interactivos** → descarga el `.zip` y en Moodle: *Añadir una actividad o recurso →
  Paquete SCORM* → sube el `.zip` sin descomprimir.
- **Cuestionarios** → descarga el `.xml` y en Moodle: *Banco de preguntas → Importar* → formato
  *Moodle XML* → selecciona el archivo.
- **Cuaderno de evaluación** → en Moodle: *Calificaciones → Exportar → Hoja de cálculo Excel* (o
  Texto plano), descarga el archivo por cada evaluación e impórtalo en el cuaderno.

## Estructura del proyecto

```
app.py                  Aplicación Flask (arranque y registro de rutas)
config.py                Configuración (clave de API, rutas de datos)
blueprints/               Rutas web de cada módulo
services/                 Lógica de negocio (IA, extracción de contenido, SCORM, Moodle XML, notas)
templates/                Plantillas HTML (Jinja2)
static/                   CSS y JS de la interfaz
scorm_assets/              Plantillas de los paquetes SCORM generados
data/                     Datos generados en tiempo de ejecución (no versionar)
```

## Notas

- Los archivos temporales de lecciones/cuestionarios generados se guardan en `data/tmp/` y los
  cuadernos de evaluación en `data/cuadernos/` (excluidos de git).
- El emparejamiento de alumnos entre distintas hojas de evaluación se hace por correo electrónico
  si está disponible, o por nombre completo normalizado en caso contrario.
