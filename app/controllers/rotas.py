from flask import Blueprint, render_template

rotas_bp = Blueprint('rotas', __name__)

@rotas_bp.route('/')
def index():
    return render_template('index.html')

@rotas_bp.route('/')
def cadastrar_pacientes():
    return render_template('pacientes')