from flask import Flask, render_template, request, redirect, url_for, flash
from flask_login import UserMixin, login_user, LoginManager, login_required, logout_user, current_user
from flask_sqlalchemy import SQLAlchemy
import logging

# Configuração de logging para verificação
logging.basicConfig(level=logging.INFO)

# --- Configuração da Aplicação ---
app = Flask(__name__)
app.config['SECRET_KEY'] = 'sua_chave_secreta_muito_segura'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Configuração do Flask-Login ---
login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))

# --- Modelos do Banco de Dados ---
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    role = db.Column(db.String(20), nullable=False) # 'ceo' ou 'admin'
    movimentacoes = db.relationship('Movimentacao', backref='autor', lazy=True)
    funcionarios = db.relationship('Funcionario', backref='empresa', lazy=True)

class Movimentacao(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    tipo = db.Column(db.String(10), nullable=False) # 'entrada' ou 'saida'
    descricao = db.Column(db.String(100), nullable=False)
    valor = db.Column(db.Float, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

class Funcionario(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), nullable=False)
    funcao = db.Column(db.String(50), nullable=False)
    salario = db.Column(db.Float, nullable=False)
    usuario_id = db.Column(db.Integer, db.ForeignKey('usuario.id'), nullable=False)

# --- Rotas (Páginas do Site) ---

@app.route('/')
def home():
    return render_template('home.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        usuario = Usuario.query.filter_by(username=username).first()
        if usuario and usuario.password == password:
            login_user(usuario)
            flash('Login efetuado com sucesso!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Credenciais inválidas. Por favor, verifique seu nome de usuário e senha.', 'danger')

    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('home'))

@app.route('/dashboard', methods=['GET', 'POST'])
@login_required
def dashboard():
    # Define o ID do usuário que detém os dados de gestão
    user_data_id = 1 

    if request.method == 'POST':
        tipo = request.form['tipo']
        descricao = request.form['descricao']
        valor = float(request.form['valor'])
        
        # Cria a movimentação vinculada ao usuário com o ID de gestão
        gestao_user = Usuario.query.get(user_data_id)
        if not gestao_user:
            flash('Usuário de gestão não encontrado. Erro interno.', 'danger')
            return redirect(url_for('dashboard'))

        nova_movimentacao = Movimentacao(tipo=tipo, descricao=descricao, valor=valor, autor=gestao_user)
        db.session.add(nova_movimentacao)
        db.session.commit()
        flash('Movimentação registrada com sucesso.', 'success')
        return redirect(url_for('dashboard'))
        
    # Consulta todas as movimentações do usuário de gestão
    todas_movimentacoes = Movimentacao.query.filter_by(usuario_id=user_data_id).all()
    total_entradas = sum(m.valor for m in todas_movimentacoes if m.tipo == 'entrada')
    total_saidas = sum(m.valor for m in todas_movimentacoes if m.tipo == 'saida')
    valor_total_em_caixa = total_entradas - total_saidas
    
    # Define a mensagem de boas-vindas com base na role do usuário logado
    if current_user.role == 'Cassia Leite':
        welcome_message = f'Bem Vinda, {current_user.username}'
    elif current_user.role == 'Joao vitor':
        welcome_message = f'Bem vindo, {current_user.username}'
    else:
        welcome_message = f'Bem-vindo(a), {current_user.username}!'

    movimentacoes = sorted(todas_movimentacoes, key=lambda m: m.id, reverse=True)

    return render_template('dashboard.html', 
                           movimentacoes=movimentacoes, 
                           valor_total_em_caixa=valor_total_em_caixa,
                           welcome_message=welcome_message)

@app.route('/dashboard/apagar_historico', methods=['POST'])
@login_required
def apagar_historico():
    # Define o ID do usuário que detém os dados de gestão
    user_data_id = 1
    
    try:
        # Exclui todas as movimentações do usuário de gestão
        Movimentacao.query.filter_by(usuario_id=user_data_id).delete()
        db.session.commit()
        flash('Histórico de movimentações apagado com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f'Ocorreu um erro ao apagar o histórico: {e}', 'danger')
    
    return redirect(url_for('dashboard'))

@app.route('/folha_pagamentos', methods=['GET', 'POST'])
@login_required
def folha_pagamentos_page():
    # Define o ID do usuário que detém os dados de gestão
    user_data_id = 1 
    
    if request.method == 'POST':
        nome = request.form['nome']
        funcao = request.form['funcao']
        salario = float(request.form['salario'])
        
        # Cria o funcionário vinculado ao usuário com o ID de gestão
        gestao_user = Usuario.query.get(user_data_id)
        novo_funcionario = Funcionario(nome=nome, funcao=funcao, salario=salario, empresa=gestao_user)
        
        db.session.add(novo_funcionario)
        db.session.commit()
        flash(f'Funcionário {nome} adicionado à folha de pagamentos.', 'success')
        
        return redirect(url_for('folha_pagamentos_page'))

    # Consulta todos os funcionários do usuário de gestão
    funcionarios = Funcionario.query.filter_by(usuario_id=user_data_id).order_by(Funcionario.nome).all()
    return render_template('folha_pagamentos.html', funcionarios=funcionarios)

@app.route('/funcionario/pagar/<int:funcionario_id>', methods=['POST'])
@login_required
def pagar_funcionario(funcionario_id):
    # Define o ID do usuário que detém os dados de gestão
    user_data_id = 1
    
    funcionario = Funcionario.query.get_or_404(funcionario_id)

    # Verifica se o funcionário pertence ao usuário de gestão
    if funcionario.usuario_id != user_data_id:
        flash('Você não tem permissão para realizar esta ação.', 'danger')
        return redirect(url_for('folha_pagamentos_page'))

    descricao_saida = f'Pagamento de salário para {funcionario.nome}'
    nova_saida = Movimentacao(tipo='saida', descricao=descricao_saida, valor=funcionario.salario, autor=funcionario.empresa)
    db.session.add(nova_saida)
    db.session.commit()
    flash(f'Salário de R$ {funcionario.salario:.2f} de {funcionario.nome} foi lançado como saída.', 'info')

    return redirect(url_for('folha_pagamentos_page'))

@app.route('/funcionario/excluir/<int:funcionario_id>', methods=['POST'])
@login_required
def excluir_funcionario(funcionario_id):
    # Define o ID do usuário que detém os dados de gestão
    user_data_id = 1
    
    funcionario = Funcionario.query.get_or_404(funcionario_id)
    
    # Verifica se o funcionário pertence ao usuário de gestão
    if funcionario.usuario_id != user_data_id:
        flash('Você não tem permissão para realizar esta ação.', 'danger')
        return redirect(url_for('folha_pagamentos_page'))

    db.session.delete(funcionario)
    db.session.commit()
    flash(f'Funcionário {funcionario.nome} foi removido com sucesso.', 'success')

    return redirect(url_for('folha_pagamentos_page'))

def setup_users():
    """Cria os usuários CEO e Administrador se eles não existirem."""
    with app.app_context():
        db.create_all()
        
        users_to_create = [
            {'username': 'Cassia Leite', 'password': '03052015', 'role': 'Cassia Leite'},
            {'username': 'João Vitor', 'password': '03052015', 'role': 'João Vitor'}
        ]

        for user_data in users_to_create:
            if not Usuario.query.filter_by(username=user_data['username']).first():
                new_user = Usuario(
                    username=user_data['username'],
                    password=user_data['password'],
                    role=user_data['role']
                )
                db.session.add(new_user)
                db.session.commit()
                logging.info(f"Usuário '{user_data['username']}' criado.")

if __name__ == '__main__':
    setup_users()
    app.run(debug=True)