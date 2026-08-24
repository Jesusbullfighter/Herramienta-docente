import io
import json
import uuid

from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for

import config
from services.ai_client import AIConfigError, AIGenerationError
from services.content_extractor import ExtractionError, extract_text
from services.moodle_xml import build_moodle_xml
from services.question_generator import TIPO_LABELS, generate_questions

bp = Blueprint("cuestionarios", __name__, url_prefix="/cuestionarios")


@bp.route("/", methods=["GET"])
def formulario():
    return render_template("cuestionarios/form.html", tipos=TIPO_LABELS)


@bp.route("/generar", methods=["POST"])
def generar():
    source_type = request.form.get("origen", "texto")
    tipos = request.form.getlist("tipos")
    try:
        contenido = extract_text(
            source_type,
            text=request.form.get("texto", ""),
            file_storage=request.files.get("archivo") or None,
            url=request.form.get("url", ""),
        )
        preguntas = generate_questions(
            contenido,
            nivel=request.form.get("nivel", ""),
            asignatura=request.form.get("asignatura", ""),
            num_preguntas=int(request.form.get("num_preguntas", 10) or 10),
            tipos=tipos,
            dificultad=request.form.get("dificultad", "media"),
        )
    except (ExtractionError, AIConfigError, AIGenerationError, ValueError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("cuestionarios.formulario"))

    quiz_id = uuid.uuid4().hex[:12]
    categoria = request.form.get("asignatura") or "Cuestionario generado"
    (config.TMP_DIR / f"quiz_{quiz_id}.json").write_text(
        json.dumps({"categoria": categoria, "preguntas": preguntas}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )

    return render_template(
        "cuestionarios/editar.html",
        preguntas=preguntas,
        quiz_id=quiz_id,
        categoria=categoria,
        tipos=TIPO_LABELS,
    )


@bp.route("/exportar", methods=["POST"])
def exportar():
    try:
        preguntas = json.loads(request.form.get("preguntas_json", "[]"))
    except json.JSONDecodeError:
        flash("No se ha podido leer el cuestionario editado.", "error")
        return redirect(url_for("cuestionarios.formulario"))

    categoria = request.form.get("categoria", "Cuestionario generado")
    if not preguntas:
        flash("El cuestionario no tiene preguntas para exportar.", "error")
        return redirect(url_for("cuestionarios.formulario"))

    xml = build_moodle_xml(preguntas, categoria=categoria)
    buffer = io.BytesIO(xml.encode("utf-8"))
    return send_file(
        buffer,
        mimetype="text/xml",
        as_attachment=True,
        download_name="cuestionario_moodle.xml",
    )
