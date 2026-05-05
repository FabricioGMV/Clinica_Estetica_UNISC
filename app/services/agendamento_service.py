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