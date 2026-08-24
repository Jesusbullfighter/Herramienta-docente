"""Cuaderno de evaluación: importa exportaciones del calificador de Moodle (Excel/CSV),
las asocia por evaluación y calcula informes individualizados y finales por alumno."""
import io
import json
import re
import unicodedata
from datetime import datetime
from pathlib import Path

import pandas as pd

import config

NON_GRADE_KEYWORDS = [
    "nombre", "apellid", "correo", "email", "institucion", "departamento",
    "numero de identificacion", "id de usuario", "grupos", "curso", "usuario",
]


class GradebookError(RuntimeError):
    pass


def _slugify(text: str) -> str:
    text = _strip_accents(text).lower()
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text or "cuaderno"


def _strip_accents(text: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFD", text or "") if unicodedata.category(c) != "Mn")


def _normalize_key(text: str) -> str:
    return re.sub(r"\s+", " ", _strip_accents(str(text)).strip().lower())


# ---------------------------------------------------------------------------
# Gestión de cuadernos (uno por curso/materia) sobre disco, en data/cuadernos/
# ---------------------------------------------------------------------------

def _notebook_dir(slug: str) -> Path:
    return config.CUADERNOS_DIR / slug


def _meta_path(slug: str) -> Path:
    return _notebook_dir(slug) / "meta.json"


def list_notebooks() -> list[dict]:
    notebooks = []
    for d in sorted(config.CUADERNOS_DIR.glob("*")):
        meta_file = d / "meta.json"
        if meta_file.exists():
            meta = json.loads(meta_file.read_text(encoding="utf-8"))
            notebooks.append(
                {
                    "slug": d.name,
                    "nombre": meta.get("nombre", d.name),
                    "num_evaluaciones": len(meta.get("evaluaciones", [])),
                }
            )
    return notebooks


def create_notebook(nombre: str) -> str:
    slug = _slugify(nombre)
    base_slug = slug
    n = 2
    while _notebook_dir(slug).exists():
        slug = f"{base_slug}-{n}"
        n += 1
    _notebook_dir(slug).mkdir(parents=True, exist_ok=True)
    meta = {"nombre": nombre, "creado": datetime.now().isoformat(), "evaluaciones": []}
    _meta_path(slug).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")
    return slug


def get_meta(slug: str) -> dict:
    if not _meta_path(slug).exists():
        raise GradebookError(f"No existe el cuaderno '{slug}'.")
    return json.loads(_meta_path(slug).read_text(encoding="utf-8"))


def _save_meta(slug: str, meta: dict) -> None:
    _meta_path(slug).write_text(json.dumps(meta, ensure_ascii=False, indent=2), encoding="utf-8")


# ---------------------------------------------------------------------------
# Lectura y normalización de un archivo exportado de Moodle
# ---------------------------------------------------------------------------

def _read_dataframe(file_stream, filename: str) -> pd.DataFrame:
    lower = filename.lower()
    try:
        if lower.endswith(".csv"):
            return pd.read_csv(file_stream)
        return pd.read_excel(file_stream)
    except Exception as exc:  # noqa: BLE001
        raise GradebookError(f"No se pudo leer el archivo '{filename}': {exc}") from exc


def _is_grade_column(col_name: str) -> bool:
    name = _strip_accents(str(col_name)).lower()
    if "%" in str(col_name):
        return False
    if "total del curso" in name or "total" == name.strip():
        return False
    return not any(kw in name for kw in NON_GRADE_KEYWORDS)


def _find_name_columns(df: pd.DataFrame) -> tuple[str | None, str | None, str | None]:
    nombre_col = apellido_col = email_col = None
    for col in df.columns:
        low = _strip_accents(str(col)).lower()
        if nombre_col is None and low.strip() == "nombre":
            nombre_col = col
        elif apellido_col is None and "apellid" in low:
            apellido_col = col
        elif email_col is None and ("correo" in low or "email" in low):
            email_col = col
    return nombre_col, apellido_col, email_col


def parse_gradebook_file(file_stream, filename: str) -> dict:
    """Convierte un archivo del calificador de Moodle en una estructura por alumno."""
    df = _read_dataframe(file_stream, filename)
    df = df.dropna(how="all")

    nombre_col, apellido_col, email_col = _find_name_columns(df)
    if nombre_col is None and email_col is None:
        raise GradebookError(
            "No se han reconocido columnas de nombre/correo en el archivo. "
            "Comprueba que es una exportación del calificador de Moodle."
        )

    grade_cols = [c for c in df.columns if c not in (nombre_col, apellido_col, email_col) and _is_grade_column(c)]

    total_col = next(
        (c for c in df.columns if "total del curso" in _strip_accents(str(c)).lower() and "%" not in str(c)),
        None,
    )

    students = {}
    for _, row in df.iterrows():
        nombre = str(row[nombre_col]).strip() if nombre_col and pd.notna(row.get(nombre_col)) else ""
        apellido = str(row[apellido_col]).strip() if apellido_col and pd.notna(row.get(apellido_col)) else ""
        email = str(row[email_col]).strip() if email_col and pd.notna(row.get(email_col)) else ""
        nombre_completo = f"{nombre} {apellido}".strip()

        if not nombre_completo and not email:
            continue

        key = _normalize_key(email) if email else _normalize_key(nombre_completo)

        notas = {}
        for col in grade_cols:
            valor = row.get(col)
            numero = _to_number(valor)
            if numero is not None:
                notas[str(col)] = numero

        total_moodle = _to_number(row.get(total_col)) if total_col else None
        media = round(sum(notas.values()) / len(notas), 2) if notas else None

        students[key] = {
            "nombre_completo": nombre_completo or email,
            "email": email,
            "notas": notas,
            "media": media,
            "total_moodle": total_moodle,
        }

    return {"columns": [str(c) for c in grade_cols], "total_col": str(total_col) if total_col else None, "students": students}


def _to_number(value):
    if value is None or (isinstance(value, float) and pd.isna(value)):
        return None
    if isinstance(value, (int, float)):
        return float(value)
    text = str(value).strip().replace(",", ".")
    if not text or text in ("-", "—"):
        return None
    match = re.search(r"-?\d+(\.\d+)?", text)
    if not match:
        return None
    try:
        return float(match.group())
    except ValueError:
        return None


# ---------------------------------------------------------------------------
# Añadir una evaluación a un cuaderno existente
# ---------------------------------------------------------------------------

def add_evaluation(slug: str, label: str, peso: float, file_stream, filename: str) -> str:
    meta = get_meta(slug)
    parsed = parse_gradebook_file(file_stream, filename)

    eval_id = f"ev{len(meta['evaluaciones']) + 1}_{_slugify(label)}"
    data_path = _notebook_dir(slug) / f"{eval_id}.json"
    data_path.write_text(json.dumps(parsed, ensure_ascii=False, indent=2), encoding="utf-8")

    meta["evaluaciones"].append(
        {
            "id": eval_id,
            "label": label,
            "peso": peso,
            "filename": filename,
            "num_alumnos": len(parsed["students"]),
            "num_actividades": len(parsed["columns"]),
            "importado": datetime.now().isoformat(),
        }
    )
    _save_meta(slug, meta)
    return eval_id


def _load_evaluation_data(slug: str, eval_id: str) -> dict:
    path = _notebook_dir(slug) / f"{eval_id}.json"
    if not path.exists():
        raise GradebookError(f"No se encuentra la evaluación '{eval_id}'.")
    return json.loads(path.read_text(encoding="utf-8"))


def remove_evaluation(slug: str, eval_id: str) -> None:
    meta = get_meta(slug)
    meta["evaluaciones"] = [e for e in meta["evaluaciones"] if e["id"] != eval_id]
    _save_meta(slug, meta)
    path = _notebook_dir(slug) / f"{eval_id}.json"
    if path.exists():
        path.unlink()


# ---------------------------------------------------------------------------
# Cálculo de tablas e informes
# ---------------------------------------------------------------------------

def _merge_students(meta: dict, slug: str) -> dict:
    """Devuelve {key: {"nombre":.., "email":.., "por_evaluacion": {eval_id: media_o_None}}}."""
    merged: dict = {}
    for ev in meta["evaluaciones"]:
        data = _load_evaluation_data(slug, ev["id"])
        for key, s in data["students"].items():
            if key not in merged:
                merged[key] = {"nombre_completo": s["nombre_completo"], "email": s["email"], "por_evaluacion": {}}
            merged[key]["por_evaluacion"][ev["id"]] = s["media"]
    return merged


def get_class_table(slug: str) -> dict:
    meta = get_meta(slug)
    merged = _merge_students(meta, slug)
    evaluaciones = meta["evaluaciones"]

    filas = []
    for key, info in sorted(merged.items(), key=lambda kv: kv[1]["nombre_completo"].lower()):
        medias = []
        pesos = []
        for ev in evaluaciones:
            media = info["por_evaluacion"].get(ev["id"])
            if media is not None:
                medias.append(media)
                pesos.append(ev.get("peso", 1.0))
        final = round(sum(m * p for m, p in zip(medias, pesos)) / sum(pesos), 2) if pesos else None
        filas.append(
            {
                "key": key,
                "nombre_completo": info["nombre_completo"],
                "por_evaluacion": info["por_evaluacion"],
                "final": final,
            }
        )

    return {"evaluaciones": evaluaciones, "filas": filas}


def get_student_report(slug: str, student_key: str) -> dict:
    meta = get_meta(slug)
    detalle_por_evaluacion = []
    medias = []
    pesos = []
    nombre_completo = None
    email = None

    for ev in meta["evaluaciones"]:
        data = _load_evaluation_data(slug, ev["id"])
        alumno = data["students"].get(student_key)
        if alumno is None:
            detalle_por_evaluacion.append({"evaluacion": ev, "encontrado": False})
            continue
        nombre_completo = nombre_completo or alumno["nombre_completo"]
        email = email or alumno["email"]
        detalle_por_evaluacion.append(
            {
                "evaluacion": ev,
                "encontrado": True,
                "notas": alumno["notas"],
                "media": alumno["media"],
                "total_moodle": alumno.get("total_moodle"),
            }
        )
        if alumno["media"] is not None:
            medias.append(alumno["media"])
            pesos.append(ev.get("peso", 1.0))

    if nombre_completo is None:
        raise GradebookError("No se encuentra ese alumno en el cuaderno.")

    final = round(sum(m * p for m, p in zip(medias, pesos)) / sum(pesos), 2) if pesos else None

    return {
        "nombre_completo": nombre_completo,
        "email": email,
        "detalle_por_evaluacion": detalle_por_evaluacion,
        "nota_final": final,
    }


def export_excel(slug: str) -> io.BytesIO:
    meta = get_meta(slug)
    tabla = get_class_table(slug)

    columnas = ["Alumno"] + [ev["label"] for ev in tabla["evaluaciones"]] + ["Nota final"]
    filas = []
    for fila in tabla["filas"]:
        row = [fila["nombre_completo"]]
        for ev in tabla["evaluaciones"]:
            row.append(fila["por_evaluacion"].get(ev["id"]))
        row.append(fila["final"])
        filas.append(row)

    df = pd.DataFrame(filas, columns=columnas)

    buffer = io.BytesIO()
    with pd.ExcelWriter(buffer, engine="openpyxl") as writer:
        df.to_excel(writer, sheet_name="Resumen", index=False)

        for ev in tabla["evaluaciones"]:
            data = _load_evaluation_data(slug, ev["id"])
            registros = []
            for s in data["students"].values():
                fila = {"Alumno": s["nombre_completo"], **s["notas"], "Media": s["media"]}
                registros.append(fila)
            if registros:
                pd.DataFrame(registros).to_excel(writer, sheet_name=ev["label"][:31], index=False)

    buffer.seek(0)
    return buffer
