"""Generación de baterías de preguntas con Claude a partir de un texto de origen."""
import random

from services.ai_client import ask_ai_json

TIPO_LABELS = {
    "opcion_multiple": "Opción múltiple (una respuesta correcta entre varias)",
    "verdadero_falso": "Verdadero o falso",
    "respuesta_corta": "Respuesta corta (palabra o frase breve)",
    "completar": "Completar huecos (texto con espacios en blanco)",
    "emparejamiento": "Emparejamiento (relacionar dos columnas)",
}

SYSTEM_PROMPT = """Eres un experto pedagogo que ayuda a un profesor de Educación Secundaria a crear
cuestionarios autoevaluables de calidad para importar en Moodle.
Generas preguntas claras, correctas, sin ambigüedades, adecuadas al nivel educativo indicado,
basadas ÚNICAMENTE en el contenido que te proporciona el profesor.
Respondes EXCLUSIVAMENTE con un JSON válido, sin texto adicional antes ni después, sin comentarios."""

USER_PROMPT_TEMPLATE = """Nivel educativo: {nivel}
Asignatura: {asignatura}
Idioma de las preguntas: {idioma}
Dificultad deseada: {dificultad}
Número total de preguntas a generar: {num_preguntas}
Tipos de pregunta permitidos (reparte el número total entre estos tipos de forma equilibrada,
salvo que se indique lo contrario): {tipos}

Contenido de origen (basa las preguntas solo en esto, no inventes datos externos):
---
{contenido}
---

Devuelve un JSON con esta forma exacta (una lista de objetos "preguntas"):

{{
  "preguntas": [
    {{
      "tipo": "opcion_multiple",
      "enunciado": "texto de la pregunta en HTML simple (puede llevar <p>, <strong>, <em>)",
      "opciones": [
        {{"texto": "opción A", "correcta": true}},
        {{"texto": "opción B", "correcta": false}},
        {{"texto": "opción C", "correcta": false}},
        {{"texto": "opción D", "correcta": false}}
      ],
      "retroalimentacion_correcta": "texto breve explicando por qué es correcta",
      "retroalimentacion_incorrecta": "texto breve orientando hacia la respuesta correcta"
    }},
    {{
      "tipo": "verdadero_falso",
      "enunciado": "afirmación a valorar",
      "correcta": true,
      "retroalimentacion": "explicación breve"
    }},
    {{
      "tipo": "respuesta_corta",
      "enunciado": "pregunta que se responde con una palabra o frase corta",
      "respuestas_aceptadas": ["respuesta principal", "sinónimo aceptado"],
      "retroalimentacion": "explicación breve"
    }},
    {{
      "tipo": "completar",
      "enunciado_con_huecos": "El texto con los huecos marcados así: la capital de Francia es {{{{respuesta:París}}}} y su moneda es {{{{respuesta:euro}}}}.",
      "retroalimentacion": "explicación breve"
    }},
    {{
      "tipo": "emparejamiento",
      "enunciado": "instrucción de la actividad, p.ej. Relaciona cada concepto con su definición",
      "pares": [
        {{"izquierda": "concepto 1", "derecha": "definición 1"}},
        {{"izquierda": "concepto 2", "derecha": "definición 2"}},
        {{"izquierda": "concepto 3", "derecha": "definición 3"}}
      ],
      "retroalimentacion": "explicación breve opcional"
    }}
  ]
}}

Reglas importantes:
- En "opcion_multiple" incluye entre 3 y 5 opciones, con exactamente una marcada como correcta.
  Varía en qué posición de la lista va la opción correcta entre una pregunta y otra (no la
  coloques siempre la primera).
- En "completar", usa el formato exacto {{{{respuesta:PALABRA}}}} para cada hueco dentro del texto.
- En "emparejamiento", incluye al menos 3 pares.
- No repitas preguntas ni reutilices casi literalmente el mismo enunciado.
- No incluyas nada fuera del JSON.
"""


def generate_questions(
    contenido: str,
    *,
    nivel: str,
    asignatura: str,
    num_preguntas: int,
    tipos: list[str],
    dificultad: str = "media",
    idioma: str = "español",
) -> list[dict]:
    tipos = [t for t in tipos if t in TIPO_LABELS] or ["opcion_multiple"]
    tipos_desc = ", ".join(f"{t} ({TIPO_LABELS[t]})" for t in tipos)

    prompt = USER_PROMPT_TEMPLATE.format(
        nivel=nivel or "Educación Secundaria Obligatoria",
        asignatura=asignatura or "no especificada",
        idioma=idioma,
        dificultad=dificultad,
        num_preguntas=num_preguntas,
        tipos=tipos_desc,
        contenido=contenido[:18000],
    )

    data = ask_ai_json(SYSTEM_PROMPT, prompt, max_tokens=8000)
    preguntas = data.get("preguntas", []) if isinstance(data, dict) else data
    if not isinstance(preguntas, list) or not preguntas:
        raise ValueError("Claude no ha devuelto ninguna pregunta utilizable.")
    return [_normalize_question(q, i) for i, q in enumerate(preguntas)]


def _normalize_question(q: dict, index: int) -> dict:
    """Añade un id estable y valores por defecto para que el editor y el exportador no fallen."""
    tipo = q.get("tipo", "opcion_multiple")
    normalized = {"id": f"q{index + 1}", "tipo": tipo}

    if tipo == "opcion_multiple":
        normalized["enunciado"] = q.get("enunciado", "")
        opciones = q.get("opciones") or []
        opciones_normalizadas = [
            {"texto": o.get("texto", ""), "correcta": bool(o.get("correcta"))} for o in opciones
        ]
        # La IA tiende a colocar siempre la respuesta correcta en la misma posición
        # (normalmente la primera); se baraja aquí para que sea realmente aleatoria.
        random.shuffle(opciones_normalizadas)
        normalized["opciones"] = opciones_normalizadas
        normalized["retroalimentacion_correcta"] = q.get("retroalimentacion_correcta", "")
        normalized["retroalimentacion_incorrecta"] = q.get("retroalimentacion_incorrecta", "")

    elif tipo == "verdadero_falso":
        normalized["enunciado"] = q.get("enunciado", "")
        normalized["correcta"] = bool(q.get("correcta"))
        normalized["retroalimentacion"] = q.get("retroalimentacion", "")

    elif tipo == "respuesta_corta":
        normalized["enunciado"] = q.get("enunciado", "")
        respuestas = q.get("respuestas_aceptadas") or []
        normalized["respuestas_aceptadas"] = [r for r in respuestas if str(r).strip()]
        normalized["retroalimentacion"] = q.get("retroalimentacion", "")

    elif tipo == "completar":
        normalized["enunciado_con_huecos"] = q.get("enunciado_con_huecos", "")
        normalized["retroalimentacion"] = q.get("retroalimentacion", "")

    elif tipo == "emparejamiento":
        normalized["enunciado"] = q.get("enunciado", "")
        pares = q.get("pares") or []
        normalized["pares"] = [
            {"izquierda": p.get("izquierda", ""), "derecha": p.get("derecha", "")} for p in pares
        ]
        normalized["retroalimentacion"] = q.get("retroalimentacion", "")

    else:
        normalized["tipo"] = "opcion_multiple"
        normalized["enunciado"] = q.get("enunciado", "Pregunta sin tipo reconocido")
        normalized["opciones"] = []
        normalized["retroalimentacion_correcta"] = ""
        normalized["retroalimentacion_incorrecta"] = ""

    return normalized
