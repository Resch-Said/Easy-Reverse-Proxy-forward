import os

from flask import Flask

from app.config import ensure_data_dir
from app.routes import web


def create_app():
    ensure_data_dir()
    templates_path = os.path.join(os.path.dirname(__file__), "..", "templates")
    app = Flask(__name__, template_folder=templates_path)
    app.register_blueprint(web)
    return app
