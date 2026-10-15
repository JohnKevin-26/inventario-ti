from flask import Flask, render_template, request, redirect, url_for, session
from database import inicializar_banco, obter_conexao

app = Flask(__name__)
app.secret_key = "chave_secreta_super_segura_inventario"

# Inicializa o banco de dados e as tabelas assim que a aplicação sobe
inicializar_banco()

# --- ROTAS DE AUTENTICAÇÃO ---

@app.route("/login", methods=["GET", "POST"])
def login():
    erro = None
    if request.method == "POST":
        username = request.form.get("username")
        senha = request.form.get("senha")
        
        conexao = obter_conexao()
        cursor = conexao.cursor()
        cursor.execute("SELECT * FROM usuarios WHERE username = ? AND senha = ?", (username, senha))
        usuario = cursor.fetchone()
        conexao.close()
        
        if usuario:
            session['user_id'] = usuario['id']
            session['username'] = usuario['username']
            session['nome_completo'] = usuario['nome_completo']
            return redirect(url_for("inicio"))
        else:
            erro = "Utilizador ou palavra-passe incorretos."
            
    return render_template("login.html", erro=erro)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("login"))


# --- DASHBOARD (INÍCIO) ---

@app.route("/")
def inicio():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos")
    total_equipamentos = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos WHERE status = 'Em Uso'")
    total_em_uso = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos WHERE status = 'Disponível'")
    total_disponivel = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos WHERE status = 'Em Manutenção'")
    total_manutencao = cursor.fetchone()['total']
    
    # Notificações reais (equipamentos em manutenção)
    cursor.execute("SELECT patrimonio, tipo, modelo FROM equipamentos WHERE status = 'Em Manutenção'")
    alertas_manutencao = cursor.fetchall()
    
    # Últimos equipamentos cadastrados
    cursor.execute("""
        SELECT e.*, c.nome as nome_colaborador 
        FROM equipamentos e
        LEFT JOIN colaboradores c ON e.colaborador_id = c.id
        ORDER BY e.id DESC LIMIT 5
    """)
    ultimos_equipamentos = cursor.fetchall()
    
    conexao.close()
    
    return render_template("index.html", 
                           total_equipamentos=total_equipamentos,
                           total_em_uso=total_em_uso,
                           total_disponivel=total_disponivel,
                           total_manutencao=total_manutencao,
                           alertas_manutencao=alertas_manutencao,
                           ultimos_equipamentos=ultimos_equipamentos)


# --- EQUIPAMENTOS ---

@app.route("/equipamentos")
def listar_equipamentos():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    termo_busca = request.args.get("q", "").strip()
    
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    if termo_busca:
        cursor.execute("""
            SELECT e.*, c.nome as nome_colaborador, c.departamento as dep_colaborador 
            FROM equipamentos e
            LEFT JOIN colaboradores c ON e.colaborador_id = c.id
            WHERE e.patrimonio LIKE ? 
               OR e.tipo LIKE ? 
               OR e.setor LIKE ? 
               OR c.nome LIKE ?
            ORDER BY e.id DESC
        """, (f"%{termo_busca}%", f"%{termo_busca}%", f"%{termo_busca}%", f"%{termo_busca}%"))
    else:
        cursor.execute("""
            SELECT e.*, c.nome as nome_colaborador, c.departamento as dep_colaborador 
            FROM equipamentos e
            LEFT JOIN colaboradores c ON e.colaborador_id = c.id
            ORDER BY e.id DESC
        """)
        
    equipamentos = cursor.fetchall()
    conexao.close()
    
    return render_template("equipamentos.html", equipamentos=equipamentos, termo_busca=termo_busca)


@app.route("/novo-equipamento", methods=["GET", "POST"])
def novo_equipamento():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    if request.method == "POST":
        patrimonio = request.form.get("patrimonio")
        numero_serie = request.form.get("numero_serie")
        tipo = request.form.get("tipo")
        fabricante = request.form.get("fabricante")
        modelo = request.form.get("modelo")
        setor = request.form.get("setor")
        colaborador_id = request.form.get("colaborador_id")
        
        if not colaborador_id:
            colaborador_id = None
            
        status = request.form.get("status")
        observacoes = request.form.get("observacoes")
        
        cursor.execute("""
            INSERT INTO equipamentos (patrimonio, numero_serie, tipo, fabricante, modelo, setor, colaborador_id, status, observacoes)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (patrimonio, numero_serie, tipo, fabricante, modelo, setor, colaborador_id, status, observacoes))
        
        conexao.commit()
        conexao.close()
        
        return redirect(url_for("listar_equipamentos"))
    
    cursor.execute("SELECT * FROM colaboradores ORDER BY nome ASC")
    colaboradores = cursor.fetchall()
    conexao.close()
        
    return render_template("novo_equipamento.html", colaboradores=colaboradores)


# --- COLABORADORES ---

@app.route("/colaboradores", methods=["GET", "POST"])
def colaboradores():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    if request.method == "POST":
        nome = request.form.get("nome")
        cargo = request.form.get("cargo")
        departamento = request.form.get("departamento")
        email = request.form.get("email")
        
        cursor.execute("""
            INSERT INTO colaboradores (nome, cargo, departamento, email)
            VALUES (?, ?, ?, ?)
        """, (nome, cargo, departamento, email))
        
        conexao.commit()
        conexao.close()
        return redirect(url_for("colaboradores"))
        
    cursor.execute("SELECT * FROM colaboradores ORDER BY nome ASC")
    lista_colaboradores = cursor.fetchall()
    conexao.close()
    
    return render_template("colaboradores.html", colaboradores=lista_colaboradores)


# --- ATRIBUIÇÕES, MANUTENÇÃO E ESTOQUE ---

@app.route("/atribuicoes")
def atribuicoes():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    cursor.execute("""
        SELECT e.patrimonio, e.tipo, c.nome as colaborador, e.status 
        FROM equipamentos e
        JOIN colaboradores c ON e.colaborador_id = c.id
        WHERE e.colaborador_id IS NOT NULL
    """)
    atribuicoes = cursor.fetchall()
    conexao.close()
    return render_template("atribuicoes.html", atribuicoes=atribuicoes)


@app.route("/manutencao")
def manutencao():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM equipamentos WHERE status = 'Em Manutenção'")
    itens_manutencao = cursor.fetchall()
    conexao.close()
    return render_template("manutencao.html", itens_manutencao=itens_manutencao)


@app.route("/estoque")
def estoque():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    cursor.execute("SELECT * FROM equipamentos WHERE status = 'Disponível'")
    itens_estoque = cursor.fetchall()
    conexao.close()
    return render_template("estoque.html", itens_estoque=itens_estoque)


# --- MOVIMENTAÇÃO ---

@app.route("/movimentacao", methods=["GET", "POST"])
def movimentacao():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    if request.method == "POST":
        equipamento_id = request.form.get("equipamento_id")
        novo_colaborador_id = request.form.get("colaborador_id")
        novo_status = request.form.get("status")
        
        cursor.execute("""
            UPDATE equipamentos 
            SET colaborador_id = ?, status = ?
            WHERE id = ?
        """, (novo_colaborador_id if novo_colaborador_id else None, novo_status, equipamento_id))
        
        conexao.commit()
        conexao.close()
        return redirect(url_for("listar_equipamentos"))
        
    cursor.execute("SELECT * FROM equipamentos ORDER BY patrimonio ASC")
    equipamentos = cursor.fetchall()
    
    cursor.execute("SELECT * FROM colaboradores ORDER BY nome ASC")
    colaboradores = cursor.fetchall()
    
    conexao.close()
    return render_template("movimentacao.html", equipamentos=equipamentos, colaboradores=colaboradores)


# --- RELATÓRIOS E CONFIGURAÇÕES ---

@app.route("/relatorios")
def relatorios():
    if 'user_id' not in session:
        return redirect(url_for("login"))
        
    conexao = obter_conexao()
    cursor = conexao.cursor()
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos")
    total_geral = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos WHERE status = 'Em Manutenção'")
    total_manutencao = cursor.fetchone()['total']
    
    cursor.execute("SELECT COUNT(*) as total FROM equipamentos WHERE status = 'Disponível'")
    total_disponivel = cursor.fetchone()['total']
    
    conexao.close()
    
    return render_template("relatorios.html", 
                           total_geral=total_geral, 
                           total_manutencao=total_manutencao, 
                           total_disponivel=total_disponivel)


@app.route("/configuracoes")
def configuracoes():
    if 'user_id' not in session:
        return redirect(url_for("login"))
    return render_template("configuracoes.html")


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)