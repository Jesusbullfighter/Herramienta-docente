#!/bin/bash
# Lanzador de "Herramienta Docente": arranca el servidor local si no está ya en marcha
# y abre la aplicación en el navegador predeterminado.
set -e

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$APP_DIR"

URL="http://127.0.0.1:5000/"
LOG_FILE="$APP_DIR/data/servidor.log"
mkdir -p "$APP_DIR/data"

servidor_activo() {
    curl -s -o /dev/null --max-time 1 "$URL"
}

if ! servidor_activo; then
    if [ ! -d "$APP_DIR/.venv" ]; then
        zenity --error --text="Falta el entorno virtual (.venv).\nAbre una terminal en:\n$APP_DIR\ny ejecuta:\npython3 -m venv .venv\nsource .venv/bin/activate\npip install -r requirements.txt" 2>/dev/null \
            || notify-send "Herramienta Docente" "Falta instalar las dependencias (.venv). Consulta el README." 2>/dev/null \
            || echo "Falta el entorno virtual (.venv). Consulta el README para instalarlo."
        exit 1
    fi

    source "$APP_DIR/.venv/bin/activate"
    nohup python "$APP_DIR/app.py" > "$LOG_FILE" 2>&1 &
    disown

    for i in $(seq 1 30); do
        sleep 0.5
        if servidor_activo; then
            break
        fi
    done
fi

if command -v xdg-open >/dev/null 2>&1; then
    xdg-open "$URL" >/dev/null 2>&1 &
else
    sensible-browser "$URL" >/dev/null 2>&1 &
fi
