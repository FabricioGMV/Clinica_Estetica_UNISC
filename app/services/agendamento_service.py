from app.database import get_db_connection

def criar_agendamento(dados, paciente_id):
    conn = get_db_connection()
    conn.execute('''
        INSERT INTO agendamentos 
        (paciente_id, data_hora, status, tipo_procedimento, sessoes_previstas, valor_cobrado, forma_pagamento, observacoes)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        paciente_id, dados['data_hora'], dados['status'], dados['tipo_procedimento'],
        dados['sessoes_previstas'], dados['valor_cobrado'], dados['forma_pagamento'],
        dados['observacoes']
    ))
    conn.commit()
    conn.close()

def listar_agendamentos_por_paciente(paciente_id):
    conn = get_db_connection()
    agendamentos = conn.execute('''
        SELECT * FROM agendamentos 
        WHERE paciente_id = ? 
        ORDER BY data_hora DESC
    ''', (paciente_id,)).fetchall()
    conn.close()
    return agendamentos

def obter_agendamento(agendamento_id):
    conn = get_db_connection()
    agendamento = conn.execute('SELECT * FROM agendamentos WHERE id = ?', (agendamento_id,)).fetchone()
    conn.close()
    return agendamento

def atualizar_agendamento(agendamento_id, dados):
    conn = get_db_connection()
    conn.execute('''
        UPDATE agendamentos SET 
            data_hora = ?, status = ?, tipo_procedimento = ?, 
            sessoes_previstas = ?, valor_cobrado = ?, forma_pagamento = ?, observacoes = ?
        WHERE id = ?
    ''', (
        dados['data_hora'], dados['status'], dados['tipo_procedimento'],
        dados['sessoes_previstas'], dados['valor_cobrado'], dados['forma_pagamento'],
        dados['observacoes'], agendamento_id
    ))
    conn.commit()
    conn.close()

def confirmar_pagamento_e_agendamento(agendamento_id):
    conn = get_db_connection()
    conn.execute('''
        UPDATE agendamentos 
        SET status_pagamento = 'Pago', status = 'Confirmado' 
        WHERE id = ?
    ''', (agendamento_id,))
    conn.commit()
    conn.close()

def listar_procedimentos_por_agendamento(agendamento_id):
    conn = get_db_connection()
    procedimentos = conn.execute('SELECT * FROM procedimentos WHERE agendamento_id = ? ORDER BY numero_sessao ASC', (agendamento_id,)).fetchall()
    conn.close()
    return procedimentos