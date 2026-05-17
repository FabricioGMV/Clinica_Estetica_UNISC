from app.database import get_db_connection

def criar_paciente(dados):
    conn = get_db_connection()
    
    # Tratamento para os checkboxes (Booleans)
    termo = 1 if dados.get('termo_consentimento') == 'on' else 0
    imagem = 1 if dados.get('autorizacao_imagem') == 'on' else 0

    conn.execute('''
        INSERT INTO pacientes 
        (nome_completo, email, telefone, data_nascimento, cpf, historico_medico, termo_consentimento, autorizacao_imagem)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        dados['nome_completo'], dados['email'], dados['telefone'], 
        dados['data_nascimento'], dados['cpf'], dados['historico_medico'], 
        termo, imagem
    ))
    
    conn.commit()
    conn.close()

def listar_pacientes():
    conn = get_db_connection()
    pacientes = conn.execute('SELECT * FROM pacientes ORDER BY nome_completo').fetchall()
    conn.close()
    return pacientes

def obter_paciente(paciente_id):
    conn = get_db_connection()
    paciente = conn.execute('SELECT * FROM pacientes WHERE id = ?', (paciente_id,)).fetchone()
    conn.close()

    return paciente

def atualizar_pacientes(paciente_id, dados):
    conn = get_db_connection()

    termo = 1 if dados.get('termo_consentimento') == 'on' else 0
    imagem = 1 if dados.get('autorizacao_imagem') == 'on' else 0

    conn.execute('''
        UPDATE pacientes SET 
            nome_completo = ?, email = ?, telefone = ?, data_nascimento = ?, 
            cpf = ?, historico_medico = ?, termo_consentimento = ?, autorizacao_imagem = ?
        WHERE id = ?
    ''', (
        dados['nome_completo'], dados['email'], dados['telefone'], 
        dados['data_nascimento'], dados['cpf'], dados['historico_medico'], 
        termo, imagem, paciente_id
    ))
    conn.commit()
    conn.close()