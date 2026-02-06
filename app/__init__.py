from flask import Flask

from app.config import ensure_data_dir
from app.routes import web


def create_app():
    ensure_data_dir()
    app = Flask(__name__)
    app.register_blueprint(web)
    return app
