import json
import uuid

from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for

import config
from services.ai_client import AIConfigError, AIGenerationError
from services.content_extractor import ExtractionError, extract_text
from services.material_generator import generate_lesson
from services.scorm_builder import build_scorm_package

bp = Blueprint("materiales", __name__, url_prefix="/materiales")


@bp.route("/", methods=["GET"])
def formulario():
    return render_template("materiales/form.html")


@bp.route("/generar", methods=["POST"])
def generar():
    source_type = request.form.get("origen", "texto")
    try:
        contenido = extract_text(
            source_type,
            text=request.form.get("texto", ""),
            file_storage=request.files.get("archivo") or None,
            url=request.form.get("url", ""),
        )
        lesson = generate_lesson(
            contenido,
            nivel=request.form.get("nivel", ""),
            asignatura=request.form.get("asignatura", ""),
        )
    except (ExtractionError, AIConfigError, AIGenerationError, ValueError, RuntimeError) as exc:
        flash(str(exc), "error")
        return redirect(url_for("materiales.formulario"))

    lesson_id = uuid.uuid4().hex[:12]
    (config.TMP_DIR / f"leccion_{lesson_id}.json").write_text(
        json.dumps(lesson, ensure_ascii=False, indent=2), encoding="utf-8"
    )

    return render_template("materiales/previsualizar.html", lesson=lesson, lesson_id=lesson_id)


@bp.route("/descargar/<lesson_id>", methods=["GET"])
def descargar(lesson_id):
    path = config.TMP_DIR / f"leccion_{lesson_id}.json"
    if not path.exists():
        flash("La lección ha expirado, vuelve a generarla.", "error")
        return redirect(url_for("materiales.formulario"))

    lesson = json.loads(path.read_text(encoding="utf-8"))
    buffer = build_scorm_package(lesson)
    nombre_archivo = f"{lesson_id}_paquete_scorm.zip"
    return send_file(
        buffer,
        mimetype="application/zip",
        as_attachment=True,
        download_name=nombre_archivo,
    )
