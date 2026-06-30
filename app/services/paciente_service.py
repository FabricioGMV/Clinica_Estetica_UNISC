from app.database import get_db_connection

def tratar_campo_vazio(valor):
    if valor is None:
        return None
    return valor if str(valor).strip() != '' else None

def criar_paciente(dados):
    conn = get_db_connection()
    
    # Tratamento corrigido: aceita tanto 'on' quanto '1' vindo do formulário
    termo = 1 if dados.get('termo_consentimento') in ['on', '1', 1] else 0
    imagem = 1 if dados.get('autorizacao_imagem') in ['on', '1', 1] else 0

    conn.execute('''
        INSERT INTO pacientes 
        (nome_completo, email, telefone, data_nascimento, cpf, historico_medico, termo_consentimento, autorizacao_imagem)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        tratar_campo_vazio(dados.get('nome_completo')), 
        tratar_campo_vazio(dados.get('email')), 
        tratar_campo_vazio(dados.get('telefone')), 
        tratar_campo_vazio(dados.get('data_nascimento')), 
        tratar_campo_vazio(dados.get('cpf')), 
        tratar_campo_vazio(dados.get('historico_medico')), 
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

    # Tratamento corrigido: aceita tanto 'on' quanto '1' vindo do formulário
    termo = 1 if dados.get('termo_consentimento') in ['on', '1', 1] else 0
    imagem = 1 if dados.get('autorizacao_imagem') in ['on', '1', 1] else 0

    conn.execute('''
        UPDATE pacientes SET 
            nome_completo = ?, email = ?, telefone = ?, data_nascimento = ?, 
            cpf = ?, historico_medico = ?, termo_consentimento = ?, autorizacao_imagem = ?
        WHERE id = ?
    ''', (
        tratar_campo_vazio(dados.get('nome_completo')), 
        tratar_campo_vazio(dados.get('email')), 
        tratar_campo_vazio(dados.get('telefone')), 
        tratar_campo_vazio(dados.get('data_nascimento')), 
        tratar_campo_vazio(dados.get('cpf')), 
        tratar_campo_vazio(dados.get('historico_medico')), 
        termo, imagem, paciente_id
    ))
    conn.commit()
    conn.close()