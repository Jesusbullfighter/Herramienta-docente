import os

from flask import Flask, render_template

import config
from blueprints.cuaderno import bp as cuaderno_bp
from blueprints.cuestionarios import bp as cuestionarios_bp
from blueprints.materiales import bp as materiales_bp


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = config.FLASK_SECRET_KEY
    app.config["MAX_CONTENT_LENGTH"] = config.MAX_CONTENT_LENGTH

    app.register_blueprint(materiales_bp)
    app.register_blueprint(cuestionarios_bp)
    app.register_blueprint(cuaderno_bp)

    @app.route("/")
    def index():
        return render_template("index.html", ai_configurado=config.AI_CONFIGURADA)

    return app


app = create_app()

if __name__ == "__main__":
    debug_mode = os.environ.get("FLASK_DEBUG") == "1"
    app.run(debug=debug_mode, host="127.0.0.1", port=5000)
