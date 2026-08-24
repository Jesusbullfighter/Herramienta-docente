import os
from pathlib import Path

from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

AI_PROVIDER = os.environ.get("AI_PROVIDER", "gemini").strip().lower()

GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "")
GEMINI_MODEL = os.environ.get("GEMINI_MODEL", "gemini-3.6-flash")

ANTHROPIC_API_KEY = os.environ.get("ANTHROPIC_API_KEY", "")
CLAUDE_MODEL = os.environ.get("CLAUDE_MODEL", "claude-sonnet-5")

FLASK_SECRET_KEY = os.environ.get("FLASK_SECRET_KEY", "dev-secret-key-cambiar")

AI_CONFIGURADA = bool(GEMINI_API_KEY or ANTHROPIC_API_KEY)

DATA_DIR = BASE_DIR / "data"
TMP_DIR = DATA_DIR / "tmp"
CUADERNOS_DIR = DATA_DIR / "cuadernos"

for d in (DATA_DIR, TMP_DIR, CUADERNOS_DIR):
    d.mkdir(parents=True, exist_ok=True)

MAX_CONTENT_LENGTH = 25 * 1024 * 1024  # 25 MB, para permitir subir PDFs/exportaciones de notas
