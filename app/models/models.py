from app.database import get_db_connection

def init_db():
    conn = get_db_connection()
    
    # Tabela 1: Pacientes
    conn.execute('''
        CREATE TABLE IF NOT EXISTS pacientes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome_completo TEXT NOT NULL,
            email TEXT,
            telefone TEXT,
            data_nascimento DATE,
            cpf TEXT,
            historico_medico TEXT,
            termo_consentimento BOOLEAN,
            autorizacao_imagem BOOLEAN
        )
    ''')
    
    # Tabela 2: Agendamentos
    conn.execute('''
        CREATE TABLE IF NOT EXISTS agendamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            paciente_id INTEGER,
            data_hora DATETIME,
            status TEXT,
            status_pagamento TEXT DEFAULT 'Aguardando',
            tipo_procedimento TEXT,
            sessoes_previstas INTEGER,
            valor_cobrado REAL,
            forma_pagamento TEXT,
            observacoes TEXT,
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')
    
    # Tabela 3: Procedimentos (Execução)
    conn.execute('''
        CREATE TABLE IF NOT EXISTS procedimentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            agendamento_id INTEGER,
            paciente_id INTEGER,
            numero_sessao INTEGER,
            data_hora_iniciado DATETIME,
            data_hora_finalizacao DATETIME,
            acoes_realizadas TEXT,
            aluno_responsavel TEXT,
            professor_supervisor TEXT,
            receitas_recomendadas TEXT,
            foto_antes TEXT,
            foto_depois TEXT,
            observacoes_execucao TEXT,
            observacao_final TEXT,
            FOREIGN KEY (agendamento_id) REFERENCES agendamentos (id),
            FOREIGN KEY (paciente_id) REFERENCES pacientes (id)
        )
    ''')
    
    conn.commit()
    conn.close()