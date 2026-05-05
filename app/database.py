import sqlite3
import os

def get_db_connection():

    basedir = os.path.abspath(os.path.dirname(os.path.dirname(__file__)))
    db_path = os.path.join(basedir, 'banco.db')

    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row

    return conn