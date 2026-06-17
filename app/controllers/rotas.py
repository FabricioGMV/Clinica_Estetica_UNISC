from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import paciente_service, agendamento_service, procedimento_service
from app.database import get_db_connection
import datetime

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

#4. Rota para o perfil do paciente (ATUALIZADA COM ORDENAÇÃO INTELIGENTE)
@rotas_bp.route('/paciente/<int:id>')
def perfil_paciente(id):
    paciente = paciente_service.obter_paciente(id)
    agendamentos_brutos = agendamento_service.listar_agendamentos_por_paciente(id)

    agendamentos = []
    for ag in agendamentos_brutos:
        sessoes = agendamento_service.listar_procedimentos_por_agendamento(ag['id'])
        agendamentos.append({
            'dados': dict(ag), # Convertido para dicionário para facilitar manuseio
            'sessoes': sessoes
        })

    # RN 4: Ordenação dos agendamentos
    ativos = [ag for ag in agendamentos if ag['dados']['status'] not in ['Finalizado', 'Cancelado']]
    inativos = [ag for ag in agendamentos if ag['dados']['status'] in ['Finalizado', 'Cancelado']]

    # Ativos: Do mais recente (próximo a hoje) pro mais longe (Crescente)
    ativos.sort(key=lambda x: x['dados']['data_hora'])
    # Inativos: Do mais recente finalizado pro mais antigo (Decrescente)
    inativos.sort(key=lambda x: x['dados']['data_hora'], reverse=True)

    # Junta as listas ordenadas
    agendamentos_ordenados = ativos + inativos

    return render_template('perfil_paciente.html', paciente=paciente, agendamentos=agendamentos_ordenados)

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

#7. Rota para editar agendamento (CORRIGIDA A PROTEÇÃO DOS CAMPOS BLOQUEADOS)
@rotas_bp.route('/agendamento/<int:id>/editar', methods=['GET', 'POST'])
def editar_agendamento(id):
    agendamento = dict(agendamento_service.obter_agendamento(id)) # Transformado em dicionário
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])
    
    conn = get_db_connection()
    qtd_sessoes = conn.execute('SELECT COUNT(*) FROM procedimentos WHERE agendamento_id = ?', (id,)).fetchone()[0]
    conn.close()
    
    # RN - Se o agendamento já está Finalizado ou Cancelado, bloqueia totalmente
    if agendamento['status'] in ['Finalizado', 'Cancelado']:
        return redirect(url_for('rotas.perfil_paciente', id=paciente['id']))

    if request.method == 'POST':
        dados_form = dict(request.form)
        
        # Repõe os valores originais ignorando o formulário HTML (que estava disabled)
        if qtd_sessoes > 0:
            campos_protegidos = ['data_hora', 'tipo_procedimento', 'sessoes_previstas', 'valor_cobrado', 'forma_pagamento']
            for campo in campos_protegidos:
                dados_form[campo] = agendamento[campo]
                    
        elif agendamento['status_pagamento'] == 'Pago':
            for campo in ['valor_cobrado', 'forma_pagamento']:
                dados_form[campo] = agendamento[campo]

        agendamento_service.atualizar_agendamento(id, dados_form)
        return redirect(url_for('rotas.perfil_paciente', id=paciente['id']))
    
    return render_template('form_agendamento.html', agendamento=agendamento, paciente=paciente, qtd_sessoes=qtd_sessoes)

#8. Rota para editar pagamento do agendamento
@rotas_bp.route('/agendamento/<int:id>/pagar', methods=['POST'])
def pagar_agendamento(id):
    agendamento = agendamento_service.obter_agendamento(id)
    agendamento_service.confirmar_pagamento_e_agendamento(id)
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))

#9. Rota para registrar sessão (ATUALIZADA PARA INJETAR QTD_SESSOES NO TEMPLATE)
@rotas_bp.route('/agendamento/<int:id>/registrar_sessao', methods=['GET', 'POST'])
def registrar_sessao(id):
    agendamento = agendamento_service.obter_agendamento(id)
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])

    # Descobre quantas sessões já foram salvas para este agendamento para injetar no form de validação de retorno
    conn = get_db_connection()
    qtd_sessoes = conn.execute('SELECT COUNT(*) FROM procedimentos WHERE agendamento_id = ?', (id,)).fetchone()[0]
    conn.close()

    if request.method == 'POST':
        procedimento_service.registrar_procedimento(id, paciente['id'], request.form, request.files)
        return redirect(url_for('rotas.perfil_paciente', id=paciente['id']))

    # Repassado "qtd_sessoes" para que o form_procedimento saiba se exige retorno ou não
    return render_template('form_procedimento.html', agendamento=agendamento, paciente=paciente, qtd_sessoes=qtd_sessoes)

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

#13. Rota do Painel Financeiro (Atualizada com Filtros Avançados)
@rotas_bp.route('/financeiro')
def financeiro():
    conn = get_db_connection()

    # 1. Captura os filtros vindos da URL (se houver)
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    paciente_nome = request.args.get('paciente', '').strip()
    status_agendamento = request.args.get('status', '')
    status_pagamento = request.args.get('status_pagamento', '')
    procedimento = request.args.get('procedimento', '').strip()

    # 2. Monta a Query Base de forma inteligente
    query = '''
        SELECT a.*, p.nome_completo 
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE 1=1
    '''
    params = []

    # 3. Aplica os filtros apenas se o usuário tiver preenchido algo
    if data_inicio:
        # Pega tudo a partir da data inicial (ignorando a hora)
        query += " AND date(a.data_hora) >= ?"
        params.append(data_inicio)
    
    if data_fim:
        # Pega tudo até a data final
        query += " AND date(a.data_hora) <= ?"
        params.append(data_fim)
        
    if paciente_nome:
        query += " AND p.nome_completo LIKE ?"
        params.append(f"%{paciente_nome}%")
        
    if status_agendamento:
        query += " AND a.status = ?"
        params.append(status_agendamento)
        
    if status_pagamento:
        query += " AND a.status_pagamento = ?"
        params.append(status_pagamento)
        
    if procedimento:
        query += " AND a.tipo_procedimento LIKE ?"
        params.append(f"%{procedimento}%")

    # Ordena para os mais recentes ficarem no topo
    query += " ORDER BY a.data_hora DESC"

    # Executa a busca no Banco de Dados
    agendamentos_filtrados = conn.execute(query, params).fetchall()
    conn.close()

    # 4. Variáveis do Painel
    total_recebido = 0.0
    total_pendente = 0.0
    transacoes = []

    # 5. Processamento Matemático (Calcula com base APENAS no que foi filtrado)
    for ag in agendamentos_filtrados:
        valor = float(ag['valor_cobrado'] if ag['valor_cobrado'] else 0)
        status = ag['status']
        pagamento = ag['status_pagamento']
        
        # Só soma em RECEBIDO se estiver Pago E não for um agendamento Cancelado 
        # (caso alguém tenha pago e depois cancelado, isso vira um caso de reembolso, não receita líquida)
        if pagamento == 'Pago' and status != 'Cancelado':
            total_recebido += valor
            
        # Só soma em PENDENTE se não estiver pago E o agendamento ainda estiver ativo (Aguardando/Confirmado/Finalizado)
        elif pagamento != 'Pago' and status != 'Cancelado':
            total_pendente += valor
            
        transacoes.append(dict(ag))

    total_saidas = 0.0 
    saldo_atual = total_recebido - total_saidas

    return render_template('financeiro.html', 
                           total_recebido=total_recebido,
                           total_pendente=total_pendente,
                           total_saidas=total_saidas,
                           saldo_atual=saldo_atual,
                           transacoes=transacoes,
                           # Passando os valores de volta para manter o form preenchido na tela
                           filtros={
                               'data_inicio': data_inicio,
                               'data_fim': data_fim,
                               'paciente': paciente_nome,
                               'status': status_agendamento,
                               'status_pagamento': status_pagamento,
                               'procedimento': procedimento
                           })