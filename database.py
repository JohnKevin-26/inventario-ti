import sqlite3

def obter_conexao():
    conexao = sqlite3.connect("inventario.db")
    conexao.row_factory = sqlite3.Row
    conexao.execute("PRAGMA foreign_keys = ON")
    return conexao

def inicializar_banco():
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    # Tabela de Usuários para o Login
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            senha TEXT NOT NULL,
            nome_completo TEXT NOT NULL
        )
    """)
    
    # Insere um utilizador padrão se não existir (admin / admin123)
    cursor.execute("SELECT COUNT(*) as total FROM usuarios WHERE username = 'admin'")
    if cursor.fetchone()['total'] == 0:
        cursor.execute("INSERT INTO usuarios (username, senha, nome_completo) VALUES (?, ?, ?)", 
                       ('admin', 'admin123', 'Kevin TI'))

    # Tabela de Colaboradores
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS colaboradores (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nome TEXT NOT NULL,
            cargo TEXT,
            departamento TEXT,
            email TEXT
        )
    """)
    
    # Tabela de Equipamentos
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS equipamentos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            patrimonio TEXT NOT NULL,
            numero_serie TEXT,
            tipo TEXT NOT NULL,
            fabricante TEXT,
            modelo TEXT,
            setor TEXT,
            colaborador_id INTEGER,
            status TEXT NOT NULL,
            observacoes TEXT,
            FOREIGN KEY (colaborador_id) REFERENCES colaboradores(id) ON DELETE SET NULL
        )
    """)
    
    conexao.commit()
    conexao.close()