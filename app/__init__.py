# app/__init__.py
from flask import Flask, render_template, request, redirect, url_for as flask_url_for, flash
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from app.forms import UsuarioForm, OrdemServicoForm
import os

# Inicializa extensões
db = SQLAlchemy()
login_manager = LoginManager()


def create_app():
    app = Flask(
        __name__,
        template_folder='../templates',
        static_folder='../static'
    )

    app.config['SECRET_KEY'] = 'chave-secreta-para-dev'
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///sistema.db'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False

    # Inicializa extensões
    db.init_app(app)
    login_manager.init_app(app)
    login_manager.login_view = 'login'
    login_manager.login_message = 'Por favor, faça login para acessar esta página.'

    # Safe url_for — evita erro se endpoint não existir
    def safe_url_for(endpoint, **values):
        try:
            return flask_url_for(endpoint, **values)
        except Exception:
            return '#'
    app.jinja_env.globals['url_for'] = safe_url_for

    # Importa modelos
    from app.models.usuario import Usuario
    from app.models.funcionario import Funcionario

    @login_manager.user_loader
    def load_user(user_id):
        return Usuario.query.get(int(user_id))

    # ====================================================
    # LOGIN E LOGOUT
    # ====================================================
    @app.route('/login', methods=['GET', 'POST'])
    def login():
        if request.method == 'POST':
            username = request.form['username'].upper()
            password = request.form['password']

            user = Usuario.query.filter_by(username=username).first()

            if user and user.check_password(password):
                login_user(user)
                return redirect(flask_url_for('index'))
            else:
                flash('Usuário ou senha inválidos.', 'error')

        return render_template('login.html')

    @app.route('/logout')
    @login_required
    def logout():
        logout_user()
        return redirect(flask_url_for('login'))

    # ====================================================
    # PÁGINA INICIAL
    # ====================================================
    @app.route('/')
    @login_required
    def index():
        return render_template('index.html', usuario=current_user.username)

    # ====================================================
    # CADASTRO DE USUÁRIOS — com Flask-WTF
    # ====================================================
    @app.route('/cadastro_usuarios', methods=['GET', 'POST'])
    @login_required
    def cadastro_usuarios():
        form = UsuarioForm()

        if form.validate_on_submit():
            novo = Usuario(
                username=form.username.data.upper(),
                email=form.email.data,
                funcionario_id=1,  # temporário — depois conectaremos ao funcionário real
                precisa_trocar_senha=False
            )
            novo.set_password(form.senha.data)
            db.session.add(novo)
            db.session.commit()
            flash('✅ Usuário cadastrado com sucesso!', 'success')
            return redirect(flask_url_for('cadastro_usuarios'))

        usuarios = Usuario.query.all()
        return render_template('cadastro_usuarios.html', form=form, usuarios=usuarios)

    # ====================================================
    # ABRIR NOVA OS — com Flask-WTF
    # ====================================================
    @app.route('/abrir_os', methods=['GET', 'POST'])
    @login_required
    def abrir_os():
        form = OrdemServicoForm()
        form.tecnico.choices = [('1', 'Vincy Admin')]  # depois carregaremos do banco

        if form.validate_on_submit():
            flash('✅ Ordem de serviço criada (simulação).', 'success')
            return redirect(flask_url_for('ordens_servico'))

        return render_template('abrir_os.html', form=form)

    # ====================================================
    # ORDENS DE SERVIÇO
    # ====================================================
    @app.route('/ordens_servico')
    @login_required
    def ordens_servico():
        ordens = []
        return render_template('ordens_servico.html', ordens=ordens)

    @app.route('/os/editar/<int:os_id>', methods=['GET', 'POST'])
    @login_required
    def editar_os(os_id):
        return render_template('editar_os.html', os_id=os_id)

    @app.route('/os/finalizar/<int:os_id>', methods=['GET', 'POST'])
    @login_required
    def finalizar_os(os_id):
        return render_template('finalizar_os.html', os_id=os_id)

    # ====================================================
    # PARCEIROS DE NEGÓCIO
    # ====================================================
    @app.route('/parceiros')
    @login_required
    def parceiros():
        parceiros_list = []
        return render_template('parceiros.html', parceiros=parceiro_list)

    @app.route('/parceiros/editar/<int:parceiro_id>', methods=['GET', 'POST'])
    @login_required
    def editar_parceiro(parceiro_id):
        parceiro = {'id': parceiro_id}
        return render_template('editar_parceiro.html', parceiro=parceiro)

    @app.route('/parceiros/inativar/<int:parceiro_id>', methods=['GET', 'POST'])
    @login_required
    def inativar_parceiro(parceiro_id):
        return render_template('inativar_parceiro.html', parceiro_id=parceiro_id)

    # ====================================================
    # FUNCIONÁRIOS E CARREIRAS
    # ====================================================
    @app.route('/funcionarios')
    @login_required
    def funcionarios():
        funcionarios_list = []
        return render_template('funcionarios.html', funcionarios=funcionarios_list)

    @app.route('/carreiras')
    @login_required
    def carreiras():
        carreiras_list = []
        return render_template('carreiras.html', carreiras=carreiras_list)

    @app.route('/carreiras/editar/<int:cargo_id>', methods=['GET', 'POST'])
    @login_required
    def editar_carreira(cargo_id):
        return render_template('editar_carreira.html', cargo_id=cargo_id)

    # ====================================================
    # TROCAR SENHA
    # ====================================================
    @app.route('/trocar-senha', methods=['GET', 'POST'])
    @login_required
    def trocar_senha():
        return render_template('trocar_senha.html')

    # ====================================================
    # PÁGINAS AUXILIARES E TESTE
    # ====================================================
    @app.route('/sobre')
    @login_required
    def sobre():
        return render_template('sobre.html')

    @app.route('/relatorios')
    @login_required
    def relatorios():
        return render_template('relatorios.html') if os.path.exists('../templates/relatorios.html') else render_template('index.html', usuario=current_user.username)

    # ====================================================
    # ROTA GENÉRICA (DEBUG DE TEMPLATES)
    # ====================================================
    @app.route('/_placeholder/<path:name>')
    @login_required
    def placeholder(name):
        template_name = f"{name}.html"
        try:
            return render_template(template_name)
        except Exception:
            return render_template('index.html', usuario=current_user.username)

    return app
