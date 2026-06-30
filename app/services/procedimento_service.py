import os
from werkzeug.utils import secure_filename
from app.database import get_db_connection

UPLOAD_FOLDER = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'static', 'uploads')

def registrar_procedimento(agendamento_id, paciente_id, dados, arquivos):
    conn = get_db_connection()
    
    total_sessoes = conn.execute('SELECT COUNT(*) FROM procedimentos WHERE agendamento_id = ?', (agendamento_id,)).fetchone()[0]
    numero_sessao = total_sessoes + 1
    
    foto_antes_nome = ""
    foto_depois_nome = ""
    
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)
    
    if 'foto_antes' in arquivos and arquivos['foto_antes'].filename != '':
        foto = arquivos['foto_antes']
        foto_antes_nome = f"antes_{agendamento_id}_{numero_sessao}_{secure_filename(foto.filename)}"
        foto.save(os.path.join(UPLOAD_FOLDER, foto_antes_nome))
        
    if 'foto_depois' in arquivos and arquivos['foto_depois'].filename != '':
        foto = arquivos['foto_depois']
        foto_depois_nome = f"depois_{agendamento_id}_{numero_sessao}_{secure_filename(foto.filename)}"
        foto.save(os.path.join(UPLOAD_FOLDER, foto_depois_nome))

    data_retorno = dados.get('data_hora_retorno') if dados.get('data_hora_retorno') != '' else None

    conn.execute('''
        INSERT INTO procedimentos 
        (agendamento_id, paciente_id, numero_sessao, data_hora_iniciado, data_hora_finalizacao, 
         acoes_realizadas, aluno_responsavel, professor_supervisor, receitas_recomendadas, 
         foto_antes, foto_depois, observacoes_execucao, observacao_final, data_hora_retorno)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    ''', (
        agendamento_id, paciente_id, numero_sessao, 
        dados['data_hora_iniciado'], dados['data_hora_finalizacao'],
        dados['acoes_realizadas'], dados['aluno_responsavel'], dados['professor_supervisor'],
        dados['receitas_recomendadas'], foto_antes_nome, foto_depois_nome,
        dados['observacoes_execucao'], dados['observacao_final'], data_retorno
    ))
    
    conn.execute('''
        UPDATE procedimentos 
        SET status_retorno = 'Realizado' 
        WHERE agendamento_id = ? AND numero_sessao = ?
    ''', (agendamento_id, total_sessoes))
    
    conn.commit()
    conn.close()