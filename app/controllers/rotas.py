from flask import Blueprint, render_template, request, redirect, url_for
from app.services import paciente_service, agendamento_service, procedimento_service
from app.database import get_db_connection

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
    agendamentos_brutos = agendamento_service.listar_agendamentos_por_paciente(id)

    agendamentos = []
    for ag in agendamentos_brutos:
        sessoes = agendamento_service.listar_procedimentos_por_agendamento(ag['id'])
        agendamentos.append({
            'dados': ag,
            'sessoes': sessoes
        })

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
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])
    
    if request.method == 'POST':
        dados_form = dict(request.form)
        
        # REMOVIDO: A trava que forçava "Finalizado" foi tirada.
        # Agora ele salva exatamente como "Cancelado", do jeito que a tela de perfil espera.
        
        agendamento_service.atualizar_agendamento(id, dados_form)
        
        return redirect(url_for('rotas.perfil_paciente', id=paciente['id']))
    
    # --- Parte do GET (carregar a tela) ---
    conn = get_db_connection()
    qtd_sessoes = conn.execute('SELECT COUNT(*) FROM procedimentos WHERE agendamento_id = ?', (id,)).fetchone()[0]
    conn.close()
    
    return render_template('form_agendamento.html', agendamento=agendamento, paciente=paciente, qtd_sessoes=qtd_sessoes)

#8. Rota para editar pagamento do agendamento
@rotas_bp.route('/agendamento/<int:id>/pagar', methods=['POST'])
def pagar_agendamento(id):
    agendamento = agendamento_service.obter_agendamento(id)
    agendamento_service.confirmar_pagamento_e_agendamento(id)
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))

#9. Rota para registrar sessão
@rotas_bp.route('/agendamento/<int:id>/registrar_sessao', methods=['GET', 'POST'])
def registrar_sessao(id):
    agendamento = agendamento_service.obter_agendamento(id)
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])

    if request.method == 'POST':
        procedimento_service.registrar_procedimento(id, paciente['id'], request.form, request.files)
        return redirect(url_for('rotas.perfil_paciente', id=paciente['id']))

    return render_template('form_procedimento.html', agendamento=agendamento, paciente=paciente)

#10. Rota inteligente para Finalizar ou Cancelar via botões rápidos (Modal do perfil)
@rotas_bp.route('/agendamento/<int:id>/mudar_status/<novo_status>', methods=['POST'])
def mudar_status_agendamento(id, novo_status):
    conn = get_db_connection()
    agendamento = conn.execute('SELECT paciente_id FROM agendamentos WHERE id = ?', (id,)).fetchone()
    
    # Removemos a conversão forçada aqui também para manter o padrão
    conn.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))

#11. Rota para visualizar todas as sessões de um procedimento específico de forma detalhada
@rotas_bp.route('/agendamento/<int:id>/sessoes')
def ver_sessoes_detalhadas(id):
    agendamento = agendamento_service.obter_agendamento(id)
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])
    sessoes = agendamento_service.listar_procedimentos_por_agendamento(id)
    
    return render_template('sessoes_detalhadas.html', agendamento=agendamento, paciente=paciente, sessoes=sessoes)

#12. Rota opcional para editar apenas a data de retorno de uma sessão específica (enquanto pendente)
@rotas_bp.route('/sessao/<int:sessao_id>/editar_retorno', methods=['POST'])
def editar_retorno(sessao_id):
    nova_data = request.form.get('data_hora_retorno')
    conn = get_db_connection()
    
    # Verifica se a sessão existe e se o retorno ainda não foi realizado
    sessao = conn.execute('SELECT * FROM procedimentos WHERE id = ?', (sessao_id,)).fetchone()
    
    if sessao and sessao['status_retorno'] == 'Agendado':
        conn.execute('UPDATE procedimentos SET data_hora_retorno = ? WHERE id = ?', (nova_data, sessao_id))
        conn.commit()
    
    conn.close()
    return redirect(url_for('rotas.ver_sessoes_detalhadas', id=sessao['agendamento_id']))