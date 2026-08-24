"""Construcción de un archivo Moodle XML a partir de la lista de preguntas normalizadas
(ver services/question_generator.py para la forma de cada tipo de pregunta)."""
import re


def _cdata(text: str) -> str:
    text = "" if text is None else str(text)
    text = text.replace("]]>", "]]]]><![CDATA[>")
    return f"<![CDATA[{text}]]>"


def _text_block(tag: str, content: str, fmt: str | None = None) -> str:
    fmt_attr = f' format="{fmt}"' if fmt else ""
    return f"<{tag}{fmt_attr}><text>{_cdata(content)}</text></{tag}>"


def _question_multichoice(q: dict) -> str:
    name = q["enunciado"][:80] or "Pregunta de opción múltiple"
    answers_xml = []
    for opt in q.get("opciones", []):
        fraction = 100 if opt.get("correcta") else 0
        feedback = q.get("retroalimentacion_correcta") if opt.get("correcta") else q.get(
            "retroalimentacion_incorrecta"
        )
        answers_xml.append(
            f'<answer fraction="{fraction}" format="html">'
            f"<text>{_cdata(opt.get('texto', ''))}</text>"
            f'<feedback format="html"><text>{_cdata(feedback or "")}</text></feedback>'
            "</answer>"
        )
    return f"""
<question type="multichoice">
  {_text_block('name', _strip_html(name))}
  {_text_block('questiontext', q.get('enunciado', ''), 'html')}
  <defaultgrade>1.0000000</defaultgrade>
  <penalty>0.3333333</penalty>
  <hidden>0</hidden>
  <single>true</single>
  <shuffleanswers>true</shuffleanswers>
  <answernumbering>abc</answernumbering>
  {''.join(answers_xml)}
</question>"""


def _question_truefalse(q: dict) -> str:
    name = q["enunciado"][:80] or "Verdadero o falso"
    correcta = bool(q.get("correcta"))
    feedback = q.get("retroalimentacion", "")
    return f"""
<question type="truefalse">
  {_text_block('name', _strip_html(name))}
  {_text_block('questiontext', q.get('enunciado', ''), 'html')}
  <defaultgrade>1.0000000</defaultgrade>
  <penalty>1.0000000</penalty>
  <hidden>0</hidden>
  <answer fraction="{100 if correcta else 0}" format="moodle_auto_format">
    <text>true</text>
    <feedback format="html"><text>{_cdata(feedback)}</text></feedback>
  </answer>
  <answer fraction="{0 if correcta else 100}" format="moodle_auto_format">
    <text>false</text>
    <feedback format="html"><text>{_cdata(feedback)}</text></feedback>
  </answer>
</question>"""


def _question_shortanswer(q: dict) -> str:
    name = q["enunciado"][:80] or "Respuesta corta"
    respuestas = q.get("respuestas_aceptadas") or [""]
    feedback = q.get("retroalimentacion", "")
    answers_xml = []
    for r in respuestas:
        answers_xml.append(
            '<answer fraction="100" format="moodle_auto_format">'
            f"<text>{_cdata(r)}</text>"
            f"<feedback format=\"html\"><text>{_cdata(feedback)}</text></feedback>"
            "</answer>"
        )
    return f"""
<question type="shortanswer">
  {_text_block('name', _strip_html(name))}
  {_text_block('questiontext', q.get('enunciado', ''), 'html')}
  <defaultgrade>1.0000000</defaultgrade>
  <penalty>0.3333333</penalty>
  <hidden>0</hidden>
  <usecase>0</usecase>
  {''.join(answers_xml)}
</question>"""


_HUECO_RE = re.compile(r"\{\{respuesta:(.*?)\}\}")


def _question_cloze(q: dict) -> str:
    original = q.get("enunciado_con_huecos", "")
    contador = {"n": 0}

    def _replace(match: re.Match) -> str:
        contador["n"] += 1
        respuesta = match.group(1).strip().replace("~", "").replace("=", "")
        return "{1:SHORTANSWER:=" + respuesta + "}"

    texto_cloze = _HUECO_RE.sub(_replace, original)
    name_plano = _HUECO_RE.sub(lambda m: m.group(1).strip(), original)
    name = _strip_html(name_plano)[:80] or "Completar huecos"
    feedback = q.get("retroalimentacion", "")
    feedback_block = (
        f'<generalfeedback format="html"><text>{_cdata(feedback)}</text></generalfeedback>'
        if feedback
        else ""
    )
    return f"""
<question type="cloze">
  {_text_block('name', name)}
  {_text_block('questiontext', texto_cloze, 'html')}
  {feedback_block}
  <hidden>0</hidden>
</question>"""


def _question_matching(q: dict) -> str:
    name = q["enunciado"][:80] or "Emparejamiento"
    pares = q.get("pares") or []
    subquestions = []
    for p in pares:
        subquestions.append(
            '<subquestion format="html">'
            f"<text>{_cdata(p.get('izquierda', ''))}</text>"
            f"<answer><text>{_cdata(p.get('derecha', ''))}</text></answer>"
            "</subquestion>"
        )
    return f"""
<question type="matching">
  {_text_block('name', _strip_html(name))}
  {_text_block('questiontext', q.get('enunciado', ''), 'html')}
  <defaultgrade>1.0000000</defaultgrade>
  <penalty>0.3333333</penalty>
  <hidden>0</hidden>
  <shuffleanswers>true</shuffleanswers>
  {''.join(subquestions)}
</question>"""


_BUILDERS = {
    "opcion_multiple": _question_multichoice,
    "verdadero_falso": _question_truefalse,
    "respuesta_corta": _question_shortanswer,
    "completar": _question_cloze,
    "emparejamiento": _question_matching,
}


def _strip_html(text: str) -> str:
    return re.sub(r"<[^>]+>", "", text or "").strip()


def build_moodle_xml(preguntas: list[dict], categoria: str = "Cuestionario generado") -> str:
    parts = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        "<quiz>",
        "<question type=\"category\">",
        f"  <category><text>$course$/top/{_strip_html(categoria) or 'Cuestionario generado'}</text></category>",
        "</question>",
    ]
    for q in preguntas:
        builder = _BUILDERS.get(q.get("tipo"))
        if builder is None:
            continue
        parts.append(builder(q))
    parts.append("</quiz>")
    return "\n".join(parts)
