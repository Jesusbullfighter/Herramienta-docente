"""Generación de una lección interactiva estructurada (para empaquetar como SCORM) con IA.

El contenido de origen se trocea en fragmentos de tamaño similar (uno por apartado), de forma
que el número de apartados esté relacionado con la extensión del texto en vez de ser un valor
fijo, y se hace una llamada a la IA por fragmento para poder cubrirlo con detalle y generar
varias preguntas de autoevaluación por apartado.
"""
import random
import re
import time
from math import ceil

from services.ai_client import ask_ai_json

PALABRAS_POR_APARTADO = 300
MIN_PALABRAS_FUSION = 120
MAX_APARTADOS = 20
MAX_CARACTERES_ORIGEN = 150_000
PREGUNTAS_POR_APARTADO = 10

SECTION_SYSTEM_PROMPT = """Eres un diseñador instruccional experto que ayuda a un profesor de
Educación Secundaria a transformar un fragmento de un texto en un apartado de una lección
interactiva, con preguntas de autoevaluación, basado ÚNICAMENTE en el fragmento proporcionado.
Respondes EXCLUSIVAMENTE con un JSON válido, sin texto adicional antes ni después."""

SECTION_PROMPT_TEMPLATE = """Nivel educativo: {nivel}
Asignatura: {asignatura}
Idioma: {idioma}
Este es el apartado {indice} de {total} de la lección.

Fragmento del contenido de origen a explicar en este apartado (cúbrelo de forma completa, sin
omitir datos, cifras, ejemplos o matices relevantes; no inventes información que no esté aquí):
---
{fragmento}
---

Devuelve un JSON con esta forma exacta:

{{
  "titulo": "Título breve del apartado, que refleje su contenido específico",
  "contenido_html": "Explicación completa y clara en HTML simple (<p>, <strong>, <em>, <ul><li>), que cubra todo el fragmento, adaptada al nivel educativo",
  "terminos_clave": [
    {{"termino": "concepto importante del fragmento", "definicion": "definición breve en una frase"}}
  ],
  "preguntas": [
    {{
      "pregunta": "pregunta de opción múltiple sobre el contenido de este apartado",
      "opciones": ["opción correcta", "distractor 1", "distractor 2", "distractor 3"],
      "correcta_index": 0,
      "feedback_correcto": "breve explicación de refuerzo",
      "feedback_incorrecto": "breve pista hacia la respuesta correcta"
    }}
  ]
}}

Reglas:
- Genera EXACTAMENTE {num_preguntas} preguntas en "preguntas", variadas entre sí, que cubran
  distintos aspectos del fragmento (no repitas la misma idea en varias preguntas). Si el
  fragmento es muy breve, puedes reformular el mismo contenido desde ángulos distintos, pero
  no inventes datos que no estén en el fragmento.
- Cada pregunta debe tener entre 3 y 4 opciones con exactamente una correcta.
- Varía la posición de la opción correcta entre las preguntas (no la coloques siempre en el
  mismo lugar ni siempre la primera); "correcta_index" debe reflejar dónde la hayas puesto.
- "terminos_clave" puede tener entre 0 y 5 términos (lista vacía si no hay términos destacables).
- No incluyas nada fuera del JSON.
"""

FINAL_SYSTEM_PROMPT = """Eres un diseñador instruccional experto que redacta el título, el
objetivo y el resumen final de una lección para Educación Secundaria, a partir de los títulos
de sus apartados. Respondes EXCLUSIVAMENTE con un JSON válido, sin texto adicional."""

FINAL_PROMPT_TEMPLATE = """Nivel educativo: {nivel}
Asignatura: {asignatura}
Apartados de la lección, en orden:
{lista_titulos}

Devuelve un JSON con esta forma exacta:
{{"titulo": "...", "objetivo": "...", "resumen": "..."}}

- "titulo": título breve y atractivo para toda la lección.
- "objetivo": una frase que resuma qué aprenderá el alumno en conjunto.
- "resumen": resumen final de dos o tres frases con las ideas clave de toda la lección.
No incluyas nada fuera del JSON.
"""


def generate_lesson(
    contenido: str,
    *,
    nivel: str,
    asignatura: str,
    idioma: str = "español",
) -> dict:
    contenido = contenido.strip()[:MAX_CARACTERES_ORIGEN]
    fragmentos = _limitar_fragmentos(_dividir_en_fragmentos(contenido), MAX_APARTADOS)

    secciones = []
    for i, fragmento in enumerate(fragmentos):
        prompt = SECTION_PROMPT_TEMPLATE.format(
            nivel=nivel or "Educación Secundaria Obligatoria",
            asignatura=asignatura or "no especificada",
            idioma=idioma,
            indice=i + 1,
            total=len(fragmentos),
            fragmento=fragmento,
            num_preguntas=PREGUNTAS_POR_APARTADO,
        )
        data = _generar_apartado_con_reintento(prompt, i + 1)
        secciones.append(_normalize_section(data, i))
        if i < len(fragmentos) - 1:
            time.sleep(1)

    resumen_data = _generar_resumen_final(nivel, asignatura, secciones)

    return {
        "titulo": resumen_data.get("titulo", "Lección interactiva"),
        "objetivo": resumen_data.get("objetivo", ""),
        "secciones": secciones,
        "resumen": resumen_data.get("resumen", ""),
    }


def _dividir_en_fragmentos(contenido: str) -> list[str]:
    parrafos = [p.strip() for p in re.split(r"\n\s*\n", contenido) if p.strip()]
    if not parrafos:
        parrafos = [contenido.strip()] if contenido.strip() else []
    if not parrafos:
        return []

    fragmentos = []
    actual = []
    palabras_actual = 0

    for parrafo in parrafos:
        palabras_parrafo = len(parrafo.split())

        if palabras_parrafo > PALABRAS_POR_APARTADO * 2:
            if actual:
                fragmentos.append("\n\n".join(actual))
                actual, palabras_actual = [], 0
            fragmentos.extend(_dividir_parrafo_largo(parrafo))
            continue

        actual.append(parrafo)
        palabras_actual += palabras_parrafo
        if palabras_actual >= PALABRAS_POR_APARTADO:
            fragmentos.append("\n\n".join(actual))
            actual, palabras_actual = [], 0

    if actual:
        texto_restante = "\n\n".join(actual)
        if fragmentos and palabras_actual < MIN_PALABRAS_FUSION:
            fragmentos[-1] += "\n\n" + texto_restante
        else:
            fragmentos.append(texto_restante)

    return fragmentos or [contenido.strip()]


def _dividir_parrafo_largo(parrafo: str) -> list[str]:
    frases = re.split(r"(?<=[.!?])\s+", parrafo)
    trozos = []
    actual = []
    palabras_actual = 0
    for frase in frases:
        actual.append(frase)
        palabras_actual += len(frase.split())
        if palabras_actual >= PALABRAS_POR_APARTADO:
            trozos.append(" ".join(actual))
            actual, palabras_actual = [], 0
    if actual:
        trozos.append(" ".join(actual))
    return trozos or [parrafo]


def _limitar_fragmentos(fragmentos: list[str], maximo: int) -> list[str]:
    if len(fragmentos) <= maximo:
        return fragmentos
    factor = ceil(len(fragmentos) / maximo)
    return ["\n\n".join(fragmentos[i : i + factor]) for i in range(0, len(fragmentos), factor)]


def _generar_apartado_con_reintento(prompt: str, numero: int, intentos: int = 2) -> dict:
    ultimo_error = None
    for _ in range(intentos):
        try:
            return ask_ai_json(SECTION_SYSTEM_PROMPT, prompt, max_tokens=6000)
        except Exception as exc:  # noqa: BLE001
            ultimo_error = exc
            time.sleep(2)
    raise RuntimeError(f"No se pudo generar el apartado {numero} de la lección: {ultimo_error}") from ultimo_error


def _generar_resumen_final(nivel: str, asignatura: str, secciones: list[dict]) -> dict:
    lista_titulos = "\n".join(f"{i + 1}. {s['titulo']}" for i, s in enumerate(secciones))
    prompt = FINAL_PROMPT_TEMPLATE.format(
        nivel=nivel or "Educación Secundaria Obligatoria",
        asignatura=asignatura or "no especificada",
        lista_titulos=lista_titulos,
    )
    try:
        return ask_ai_json(FINAL_SYSTEM_PROMPT, prompt, max_tokens=1000)
    except Exception:  # noqa: BLE001
        return {"titulo": "Lección interactiva", "objetivo": "", "resumen": ""}


def _normalize_section(data: dict, index: int) -> dict:
    preguntas = []
    for q in data.get("preguntas", []) or []:
        opciones = [str(o) for o in q.get("opciones", [])]
        if len(opciones) < 2:
            continue
        idx = q.get("correcta_index", 0)
        if not isinstance(idx, int) or idx < 0 or idx >= len(opciones):
            idx = 0

        # La IA tiende a colocar siempre la respuesta correcta en la misma posición (normalmente
        # la primera); se baraja aquí para que la posición sea realmente aleatoria.
        pares = [(texto, i == idx) for i, texto in enumerate(opciones)]
        random.shuffle(pares)
        opciones_barajadas = [p[0] for p in pares]
        idx_barajado = next(i for i, p in enumerate(pares) if p[1])

        preguntas.append(
            {
                "pregunta": q.get("pregunta", ""),
                "opciones": opciones_barajadas,
                "correcta_index": idx_barajado,
                "feedback_correcto": q.get("feedback_correcto", ""),
                "feedback_incorrecto": q.get("feedback_incorrecto", ""),
            }
        )

    return {
        "id": f"sec{index + 1}",
        "titulo": data.get("titulo", f"Apartado {index + 1}"),
        "contenido_html": data.get("contenido_html", ""),
        "terminos_clave": [
            {"termino": t.get("termino", ""), "definicion": t.get("definicion", "")}
            for t in (data.get("terminos_clave") or [])
            if t.get("termino")
        ],
        "preguntas": preguntas,
    }
