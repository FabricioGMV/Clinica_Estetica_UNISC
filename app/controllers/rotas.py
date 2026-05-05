from flask import Blueprint, render_template, request, redirect, url_for
from app.services import paciente_service

rotas_bp = Blueprint('rotas', __name__)

@rotas_bp.route('/')
def index():
    return render_template('index.html')

@rotas_bp.route('/pacientes')
def pacientes():
    lista = paciente_service.listar_pacientes()
    return render_template('pacientes.html', pacientes=lista)

@rotas_bp.route('/paciente/novo', methods=('GET', 'POST'))
def novo_paciente():
    if request.method == 'POST':
        paciente_service.criar_paciente(request.form)
        
        return redirect(url_for('rotas.pacientes'))
    
    return render_template('form_paciente.html')