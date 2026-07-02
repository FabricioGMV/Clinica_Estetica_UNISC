from flask import Blueprint, render_template, request, redirect, url_for, flash
from app.services import paciente_service, agendamento_service, procedimento_service
from app.database import get_db_connection
import datetime

rotas_bp = Blueprint('rotas', __name__)

#1. Rota principal
@rotas_bp.route('/')
def index():
    conn = get_db_connection()
    
    # 1. Conta o Total de Pacientes cadastrados
    total_pacientes = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    
    # 2. Conta Agendamentos que estão com status 'Aguardando'
    agendamentos_pendentes = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE status = 'Aguardando'").fetchone()[0]
    
    # 3. Calcula a Receita do Mês Atual
    now = datetime.datetime.now()
    mes_atual_str = f"{now.year}-{now.month:02d}"
    
    receita_bruta = conn.execute(
        "SELECT SUM(valor_cobrado) FROM agendamentos WHERE status_pagamento = 'Pago' AND status != 'Cancelado' AND data_hora LIKE ?", 
        (f"{mes_atual_str}-%",)
    ).fetchone()[0]
    
    # Se não houver receita, garante que seja 0. Se houver, formata para o padrão Brasileiro (ex: 1.200,50)
    receita_total = float(receita_bruta) if receita_bruta else 0.0
    receita_formatada = "{:,.2f}".format(receita_total).replace(',', 'X').replace('.', ',').replace('X', '.')

    # 4. Busca os agendamentos de hoje (NOVA LÓGICA)
    today_str = now.strftime("%Y-%m-%d")
    agendamentos_hoje_db = conn.execute(
        """
        SELECT p.nome_completo, a.data_hora, a.tipo_procedimento
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE a.data_hora LIKE ?
        ORDER BY a.data_hora ASC
        """,
        (f"{today_str}%",)
    ).fetchall()
    
    conn.close()

    # Envia todos esses dados para o seu index.html
    return render_template('index.html', 
                           total_pacientes=total_pacientes, 
                           agendamentos_pendentes=agendamentos_pendentes, 
                           receita_total=receita_formatada,
                           agendamentos_hoje=agendamentos_hoje_db) # Passando os dados novos

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

#5. Rota para Visualizar Detalhes e Editar dados/foto do Paciente
@rotas_bp.route('/paciente/<int:id>/detalhes', methods=['GET', 'POST'])
def detalhes_paciente(id):
    paciente = paciente_service.obter_paciente(id)
    
    if request.method == 'POST':
        try:
            # 1. Atualiza todos os dados textuais e checkboxes com segurança
            paciente_service.atualizar_pacientes(id, request.form)
            
            # 2. Se o usuário enviou uma nova foto de perfil, salva ela no servidor
            if 'foto_perfil' in request.files:
                file = request.files['foto_perfil']
                if file and file.filename != '':
                    filename = f"paciente_{id}.jpg"
                    import os
                    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
                    upload_path = os.path.join(basedir, 'app', 'static', 'uploads', 'perfis')
                    os.makedirs(upload_path, exist_ok=True)
                    file.save(os.path.join(upload_path, filename))
            
            flash('Dados do paciente atualizados com sucesso!', 'success')
            return redirect(url_for('rotas.detalhes_paciente', id=id))
            
        except Exception as e:
            # === AQUI ESTÁ O TRATAMENTO DE ERRO ===
            # Isso vai imprimir o erro exato no terminal do seu VS Code / PyCharm
            print("\n" + "="*50)
            print("🚨 ERRO AO ATUALIZAR PACIENTE 🚨")
            print(f"Detalhes do erro: {e}")
            print("="*50 + "\n")
            
            # Isso vai mostrar uma mensagem de erro vermelha na tela do navegador
            flash(f'Erro ao salvar: {str(e)}', 'danger')
            return redirect(url_for('rotas.detalhes_paciente', id=id))
            
    return render_template('detalhes_paciente.html', paciente=paciente)

#6. Rota para agendar nova consulta
@rotas_bp.route('/paciente/<int:id>/agendar', methods=['GET', 'POST'])
def novo_agendamento(id):
    paciente = paciente_service.obter_paciente(id)

    if request.method == 'POST':
        agendamento_service.criar_agendamento(request.form, id)

        return redirect(url_for('rotas.perfil_paciente', id=id))
    
    return render_template('form_agendamento.html', paciente=paciente)

#7. Rota para editar paciente
@rotas_bp.route('/paciente/<int:id>/editar', methods=['GET', 'POST'])
def editar_paciente(id):
    paciente = paciente_service.obter_paciente(id)
    if request.method == 'POST':
        paciente_service.atualizar_pacientes(id, request.form)

        return redirect(url_for('rotas.perfil_paciente', id=id))
    
    return render_template('form_paciente.html', paciente=paciente)

#8. Rota para editar agendamento (CORRIGIDA A PROTEÇÃO DOS CAMPOS BLOQUEADOS)
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

#9. Rota para editar pagamento do agendamento
@rotas_bp.route('/agendamento/<int:id>/pagar', methods=['POST'])
def pagar_agendamento(id):
    agendamento = agendamento_service.obter_agendamento(id)
    agendamento_service.confirmar_pagamento_e_agendamento(id)
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))

#10. Rota para registrar sessão (ATUALIZADA PARA INJETAR QTD_SESSOES NO TEMPLATE)
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

#11. Rota inteligente para Finalizar ou Cancelar via botões rápidos (Modal do perfil)
@rotas_bp.route('/agendamento/<int:id>/mudar_status/<novo_status>', methods=['POST'])
def mudar_status_agendamento(id, novo_status):
    conn = get_db_connection()
    agendamento = conn.execute('SELECT paciente_id FROM agendamentos WHERE id = ?', (id,)).fetchone()
    
    # Removemos a conversão forçada aqui também para manter o padrão
    conn.execute('UPDATE agendamentos SET status = ? WHERE id = ?', (novo_status, id))
    conn.commit()
    conn.close()
    
    return redirect(url_for('rotas.perfil_paciente', id=agendamento['paciente_id']))

#12. Rota para visualizar todas as sessões de um procedimento específico de forma detalhada
@rotas_bp.route('/agendamento/<int:id>/sessoes')
def ver_sessoes_detalhadas(id):
    agendamento = agendamento_service.obter_agendamento(id)
    paciente = paciente_service.obter_paciente(agendamento['paciente_id'])
    sessoes = agendamento_service.listar_procedimentos_por_agendamento(id)
    
    return render_template('sessoes_detalhadas.html', agendamento=agendamento, paciente=paciente, sessoes=sessoes)

#13. Rota opcional para editar apenas a data de retorno de uma sessão específica (enquanto pendente)
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

#14. Rota do Painel Financeiro
@rotas_bp.route('/financeiro')
def financeiro():
    conn = get_db_connection()

    # 1. Captura os filtros vindos da URL
    data_inicio = request.args.get('data_inicio', '')
    data_fim = request.args.get('data_fim', '')
    paciente_nome = request.args.get('paciente', '').strip()
    status_agendamento = request.args.get('status', '')
    status_pagamento = request.args.get('status_pagamento', '')
    procedimento = request.args.get('procedimento', '')

    # 2. Monta a Query Base
    query = '''
        SELECT a.*, p.nome_completo 
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        WHERE 1=1
    '''
    params = []

    # 3. Aplica os filtros
    if data_inicio:
        query += " AND date(a.data_hora) >= ?"
        params.append(data_inicio)
    
    if data_fim:
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
        # Busca EXATA pelo value limpo ("Drenagem Linfatica", "Outro", etc)
        query += " AND a.tipo_procedimento = ?"
        params.append(procedimento)

    query += " ORDER BY a.data_hora DESC"

    agendamentos_filtrados = conn.execute(query, params).fetchall()
    conn.close()

    # 4. Processamento Matemático
    total_recebido = 0.0
    total_pendente = 0.0
    transacoes = []

    for ag in agendamentos_filtrados:
        valor = float(ag['valor_cobrado'] if ag['valor_cobrado'] else 0)
        status = ag['status']
        pagamento = ag['status_pagamento']
        
        if pagamento == 'Pago' and status != 'Cancelado':
            total_recebido += valor
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
                           filtros={
                               'data_inicio': data_inicio,
                               'data_fim': data_fim,
                               'paciente': paciente_nome,
                               'status': status_agendamento,
                               'status_pagamento': status_pagamento,
                               'procedimento': procedimento
                           })

#15. Rota de Estatísticas (Foco Operacional e Clínico)
@rotas_bp.route('/estatisticas')
def estatisticas():
    conn = get_db_connection()
    
    # Métricas Operacionais
    total_pacientes = conn.execute("SELECT COUNT(*) FROM pacientes").fetchone()[0]
    total_agendamentos = conn.execute("SELECT COUNT(*) FROM agendamentos").fetchone()[0]
    total_sessoes = conn.execute("SELECT COUNT(*) FROM procedimentos").fetchone()[0]
    
    cancelados = conn.execute("SELECT COUNT(*) FROM agendamentos WHERE status = 'Cancelado'").fetchone()[0]
    
    # Calcula a taxa de cancelamento
    taxa_cancelamento = round((cancelados / total_agendamentos * 100), 1) if total_agendamentos > 0 else 0
    
    # Agendamentos por Status (Para o Gráfico de Barras)
    status_counts = conn.execute("SELECT status, COUNT(*) as qtd FROM agendamentos GROUP BY status").fetchall()
    labels_status = [row['status'] for row in status_counts]
    dados_status = [row['qtd'] for row in status_counts]
    
    # Procedimentos mais agendados (Para o Gráfico de Pizza)
    proc_counts = conn.execute("SELECT tipo_procedimento, COUNT(*) as qtd FROM agendamentos WHERE status != 'Cancelado' GROUP BY tipo_procedimento ORDER BY qtd DESC").fetchall()
    labels_procedimentos = [row['tipo_procedimento'] for row in proc_counts]
    dados_procedimentos = [row['qtd'] for row in proc_counts]
    
    conn.close()

    return render_template('estatisticas.html', 
                           total_pacientes=total_pacientes,
                           total_agendamentos=total_agendamentos,
                           total_sessoes=total_sessoes,
                           taxa_cancelamento=taxa_cancelamento,
                           labels_status=labels_status,
                           dados_status=dados_status,
                           labels_procedimentos=labels_procedimentos,
                           dados_procedimentos=dados_procedimentos)


#16. Rota de Relatórios (Foco em Vendas, BI e Exportação)
@rotas_bp.route('/relatorios')
def relatorios():
    conn = get_db_connection()
    
    # 1. Pega a data atual e descobre qual foi o mês passado
    now = datetime.datetime.now()
    mes_atual_str = f"{now.year}-{now.month:02d}"
    
    primeiro_dia_mes = now.replace(day=1)
    ultimo_dia_mes_passado = primeiro_dia_mes - datetime.timedelta(days=1)
    mes_passado_str = f"{ultimo_dia_mes_passado.year}-{ultimo_dia_mes_passado.month:02d}"
    
    # 2. Receita: Mês Atual vs Mês Passado
    receita_atual = conn.execute("SELECT SUM(valor_cobrado) FROM agendamentos WHERE status_pagamento = 'Pago' AND status != 'Cancelado' AND data_hora LIKE ?", (f"{mes_atual_str}-%",)).fetchone()[0] or 0
    receita_passado = conn.execute("SELECT SUM(valor_cobrado) FROM agendamentos WHERE status_pagamento = 'Pago' AND status != 'Cancelado' AND data_hora LIKE ?", (f"{mes_passado_str}-%",)).fetchone()[0] or 0
    
    # 3. Calcula a % de Crescimento
    if receita_passado > 0:
        crescimento = ((receita_atual - receita_passado) / receita_passado) * 100
    else:
        crescimento = 100.0 if receita_atual > 0 else 0.0
        
    # 4. Top Procedimentos que dão mais LUCRO (Valor R$)
    receita_por_proc = conn.execute('''
        SELECT tipo_procedimento, SUM(valor_cobrado) as total_receita, COUNT(*) as qtd_vendas
        FROM agendamentos 
        WHERE status_pagamento = 'Pago' AND status != 'Cancelado'
        GROUP BY tipo_procedimento 
        ORDER BY total_receita DESC LIMIT 5
    ''').fetchall()
    top_procedimentos = [dict(row) for row in receita_por_proc]
    
    # 5. Receita Mensal dos últimos 6 meses (Para o Gráfico)
    receita_mensal_db = conn.execute('''
        SELECT substr(data_hora, 1, 7) as mes_ano, SUM(valor_cobrado) as total 
        FROM agendamentos 
        WHERE status_pagamento = 'Pago' AND status != 'Cancelado' 
        GROUP BY mes_ano 
        ORDER BY mes_ano DESC LIMIT 6
    ''').fetchall()
    
    # Inverte para o gráfico ficar da esquerda (mais antigo) para a direita (mais novo)
    meses_labels = [row['mes_ano'] for row in reversed(receita_mensal_db)]
    receita_dados = [row['total'] for row in reversed(receita_mensal_db)]
    
    # 6. Dados Brutos para Exportar
    dados_brutos = conn.execute('''
        SELECT a.data_hora, p.nome_completo, a.tipo_procedimento, a.sessoes_previstas, a.valor_cobrado, a.status_pagamento, a.status
        FROM agendamentos a
        JOIN pacientes p ON a.paciente_id = p.id
        ORDER BY a.data_hora DESC
    ''').fetchall()
    lista_relatorio = [dict(row) for row in dados_brutos]
    
    conn.close()

    return render_template('relatorios.html', 
                           lista_relatorio=lista_relatorio,
                           receita_atual=receita_atual,
                           receita_passado=receita_passado,
                           crescimento=round(crescimento, 1),
                           top_procedimentos=top_procedimentos,
                           meses_labels=meses_labels,
                           receita_dados=receita_dados)