import os

from flask import Flask, jsonify, send_from_directory

from .config import Config
from .db import init_db


def create_app(overrides=None):
    app = Flask(__name__, static_folder="static", static_url_path="/static")
    app.config.from_object(Config)
    if overrides:
        app.config.update(overrides)
    os.makedirs(app.config["UPLOAD_DIR"], exist_ok=True)
    app.config["MAX_CONTENT_LENGTH"] = app.config["MAX_UPLOAD_BYTES"] + 1024
    init_db(app.config["DB_PATH"])

    from .api import bp
    app.register_blueprint(bp)

    @app.get("/")
    def index():
        return send_from_directory(app.static_folder, "index.html")

    @app.errorhandler(413)
    def too_large(_):
        return jsonify(error="file terlalu besar"), 400

    @app.errorhandler(404)
    def nf(_):
        return jsonify(error="tidak ditemukan"), 404

    @app.errorhandler(405)
    def na(_):
        return jsonify(error="metode tidak diizinkan"), 405

    return app
