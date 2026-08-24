from flask import Blueprint, render_template, request, send_file, flash, redirect, url_for

from services import gradebook
from services.gradebook import GradebookError

bp = Blueprint("cuaderno", __name__, url_prefix="/cuaderno")


@bp.route("/", methods=["GET"])
def listado():
    return render_template("cuaderno/index.html", cuadernos=gradebook.list_notebooks())


@bp.route("/crear", methods=["POST"])
def crear():
    nombre = request.form.get("nombre", "").strip()
    if not nombre:
        flash("Indica un nombre para el nuevo cuaderno (por ejemplo, el curso y la materia).", "error")
        return redirect(url_for("cuaderno.listado"))
    slug = gradebook.create_notebook(nombre)
    return redirect(url_for("cuaderno.detalle", slug=slug))


@bp.route("/<slug>", methods=["GET"])
def detalle(slug):
    try:
        meta = gradebook.get_meta(slug)
        tabla = gradebook.get_class_table(slug)
    except GradebookError as exc:
        flash(str(exc), "error")
        return redirect(url_for("cuaderno.listado"))
    return render_template("cuaderno/curso.html", slug=slug, meta=meta, tabla=tabla)


@bp.route("/<slug>/subir", methods=["POST"])
def subir(slug):
    archivo = request.files.get("archivo")
    label = request.form.get("label", "").strip()
    peso = request.form.get("peso", "1").strip()

    if not archivo or not archivo.filename:
        flash("Selecciona el archivo exportado del calificador de Moodle.", "error")
        return redirect(url_for("cuaderno.detalle", slug=slug))
    if not label:
        flash("Ponle un nombre a la evaluación (por ejemplo, '1ª Evaluación').", "error")
        return redirect(url_for("cuaderno.detalle", slug=slug))

    try:
        peso_valor = float(peso.replace(",", "."))
    except ValueError:
        peso_valor = 1.0

    try:
        gradebook.add_evaluation(slug, label, peso_valor, archivo, archivo.filename)
    except GradebookError as exc:
        flash(str(exc), "error")

    return redirect(url_for("cuaderno.detalle", slug=slug))


@bp.route("/<slug>/evaluacion/<eval_id>/eliminar", methods=["POST"])
def eliminar_evaluacion(slug, eval_id):
    gradebook.remove_evaluation(slug, eval_id)
    return redirect(url_for("cuaderno.detalle", slug=slug))


@bp.route("/<slug>/alumno/<student_key>", methods=["GET"])
def alumno(slug, student_key):
    try:
        informe = gradebook.get_student_report(slug, student_key)
        meta = gradebook.get_meta(slug)
    except GradebookError as exc:
        flash(str(exc), "error")
        return redirect(url_for("cuaderno.detalle", slug=slug))
    return render_template("cuaderno/alumno.html", slug=slug, meta=meta, informe=informe)


@bp.route("/<slug>/exportar", methods=["GET"])
def exportar(slug):
    try:
        buffer = gradebook.export_excel(slug)
    except GradebookError as exc:
        flash(str(exc), "error")
        return redirect(url_for("cuaderno.detalle", slug=slug))
    return send_file(
        buffer,
        mimetype="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        as_attachment=True,
        download_name=f"cuaderno_{slug}.xlsx",
    )
