from flask import Blueprint, render_template, request, redirect, url_for
from app.services import paciente_service, agendamento_service

rotas_bp = Blueprint('rotas', __name__)

#1. Rota principal
@rotas_bp.route('/')
def index():
    return render_template('index.html')

#2. Rota da lista de pacientes
@rotas_bp.route('/pacientes')
def pacientes():
    lista = paciente_service.listar_pacientes()
    return render_template('pacientes.html', pacientes=lista)

#3. Rota de criação de pacientes
@rotas_bp.route('/paciente/novo', methods=('GET', 'POST'))
def novo_paciente():
    if request.method == 'POST':
        paciente_service.criar_paciente(request.form)
        
        return redirect(url_for('rotas.pacientes'))
    
    return render_template('form_paciente.html')

#4. Rota para o perfil do paciente
@rotas_bp.route('/paciente/<int:id>')
def perfil_paciente(id):
    paciente = paciente_service.obter_paciente(id)
    agendamentos = agendamento_service.listar_agendamentos_por_paciente(id)

    return render_template('perfil_paciente.html', paciente=paciente, agendamentos=agendamentos)

#5. Rota para agendar nova consulta
@rotas_bp.route('/paciente/<int:id>/agendar', methods=['GET', 'POST'])
def novo_agendamento(id):
    paciente = paciente_service.obter_paciente(id)

    if request.method == 'POST':
        agendamento_service.criar_agendamento(request.form, id)

        return redirect(url_for('rotas.perfil_paciente', id=id))
    
    return render_template('form_agendamento.html', paciente=paciente)

#6. Rota para editar paciente
@rotas_bp.route('/paciente/<int:id>/editar', methods=['GET', 'POST'])
def editar_paciente(id):
    paciente = paciente_service.obter_paciente(id)
    if request.method == 'POST':
        paciente_service.atualizar_pacientes(id, request.form)

        return redirect(url_for('rotas.perfil_paciente', id=id))
    
    return render_template('form_paciente.html', paciente=paciente)

#7. Rota para editar agendamento
@rotas_bp.route('/agendamento/<int:id>/editar', methods=['GET', 'POST'])
def editar_agendamento(id):
    agendamento = agendamento_service.obter_agendamento(id)
    if request.method == 'POST':
        agendamento_service.atualizar_agendamento(id, request.form)
        
        return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))
    
    return render_template('form_agendamento.html', agendamento=agendamento, paciente=paciente_service.obter_paciente(agendamento['paciente_id']))

#8. Rota para editar pagamento do agendamento
@rotas_bp.route('/agendamento/<int:id>/pagar', methods=['POST'])
def pagar_agendamento(id):
    agendamento = agendamento_service.obter_agendamento(id)
    agendamento_service.confirmar_pagamento_e_agendamento(id)
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))