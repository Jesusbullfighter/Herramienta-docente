"""Empaquetado de una lección interactiva (dict, ver material_generator.py) como paquete SCORM 1.2 (.zip)."""
import html
import io
import json
import re
import zipfile
from pathlib import Path

ASSETS_DIR = Path(__file__).resolve().parent.parent / "scorm_assets"

INDEX_HTML_TEMPLATE = """<!DOCTYPE html>
<html lang="es">
<head>
<meta charset="UTF-8">
<title>{titulo}</title>
<link rel="stylesheet" href="lesson.css">
</head>
<body>
  <div class="lesson-header">
    <h1>{titulo}</h1>
    <p>{objetivo}</p>
    <div class="lesson-progress"><div class="lesson-progress-bar"></div></div>
  </div>
  <div class="lesson-body" id="lesson-root"></div>

  <script type="application/json" id="lesson-data">{lesson_json}</script>
  <script src="scorm_api_wrapper.js"></script>
  <script src="lesson.js"></script>
</body>
</html>
"""

MANIFEST_TEMPLATE = """<?xml version="1.0" encoding="UTF-8"?>
<manifest identifier="COM_{identifier}" version="1.2"
  xmlns="http://www.imsproject.org/xsd/imscp_rootv1p1p2"
  xmlns:adlcp="http://www.adlnet.org/xsd/adlcp_rootv1p2"
  xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
  xsi:schemaLocation="http://www.imsproject.org/xsd/imscp_rootv1p1p2 imscp_rootv1p1p2.xsd
                      http://www.adlnet.org/xsd/adlcp_rootv1p2 adlcp_rootv1p2.xsd">
  <metadata>
    <schema>ADL SCORM</schema>
    <schemaversion>1.2</schemaversion>
  </metadata>
  <organizations default="ORG_{identifier}">
    <organization identifier="ORG_{identifier}">
      <title>{titulo}</title>
      <item identifier="ITEM_{identifier}" identifierref="RES_{identifier}">
        <title>{titulo}</title>
      </item>
    </organization>
  </organizations>
  <resources>
    <resource identifier="RES_{identifier}" type="webcontent" adlcp:scormtype="sco" href="index.html">
      <file href="index.html"/>
      <file href="lesson.css"/>
      <file href="lesson.js"/>
      <file href="scorm_api_wrapper.js"/>
    </resource>
  </resources>
</manifest>
"""


def _slugify(text: str) -> str:
    text = re.sub(r"[^a-zA-Z0-9]+", "_", text.strip().lower())
    return re.sub(r"_+", "_", text).strip("_") or "leccion"


def build_scorm_package(lesson: dict) -> io.BytesIO:
    """Devuelve un BytesIO con el .zip del paquete SCORM listo para descargar/subir a Moodle."""
    identifier = _slugify(lesson.get("titulo", "leccion"))
    index_html = INDEX_HTML_TEMPLATE.format(
        titulo=html.escape(lesson.get("titulo", "Lección")),
        objetivo=html.escape(lesson.get("objetivo", "")),
        lesson_json=json.dumps(lesson, ensure_ascii=False),
    )
    manifest_xml = MANIFEST_TEMPLATE.format(
        identifier=identifier,
        titulo=html.escape(lesson.get("titulo", "Lección")),
    )

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as zf:
        zf.writestr("imsmanifest.xml", manifest_xml)
        zf.writestr("index.html", index_html)
        zf.writestr("lesson.css", (ASSETS_DIR / "lesson.css").read_text(encoding="utf-8"))
        zf.writestr("lesson.js", (ASSETS_DIR / "lesson.js").read_text(encoding="utf-8"))
        zf.writestr(
            "scorm_api_wrapper.js",
            (ASSETS_DIR / "scorm_api_wrapper.js").read_text(encoding="utf-8"),
        )

    buffer.seek(0)
    return buffer
