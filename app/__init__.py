from flask import Flask

def create_app():
    app = Flask(__name__, template_folder='templates', static_folder='static')

    from app.controllers.rotas import rotas_bp
    app.register_blueprint(rotas_bp)

    return app