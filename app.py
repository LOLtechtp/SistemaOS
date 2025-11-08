# 1. Importar as ferramentas
from flask import Flask, render_template, request, redirect, url_for, flash, jsonify
from flask_sqlalchemy import SQLAlchemy
import re
import os 
from flask_migrate import Migrate
import logging 
from dotenv import load_dotenv 
from flask_login import LoginManager, UserMixin, login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
import cloudinary
import cloudinary.uploader
import cloudinary.api
from werkzeug.utils import secure_filename 
import secrets
import string
from functools import wraps 
from flask_mail import Mail, Message 
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadTimeSignature 

# --- NOVO BLOCO: CONFIGURAÇÃO DE LOGS E AMBIENTE ---
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env')) # <-- "Lê" o .env (para o Local e para o Bash)

# --- BLOCO DE LOGGING COMENTADO (PARA NÃO DAR ERRO DE PERMISSÃO) ---
# ... (bloco de logging continua comentado) ...
# --- FIM DO BLOCO COMENTADO ---


# 2. Criar a aplicação
app = Flask(__name__)
# PARA:
app.config['SECRET_KEY'] = os.environ.get('SECRET_KEY') or 'chave-secreta-para-dev'

# ----- **** "REFORMA" (O "CONSERTO" DO "ALICERCE") **** -----
database_url = os.environ.get('DATABASE_URL') 
mysql_user = os.environ.get('MYSQL_USER')     
mysql_password = os.environ.get('MYSQL_PASSWORD')
mysql_host = os.environ.get('MYSQL_HOST')
mysql_db = os.environ.get('MYSQL_DB')

if database_url:
    app.config['SQLALCHEMY_DATABASE_URI'] = database_url.replace("postgres://", "postgresql://", 1)
elif mysql_user and mysql_password and mysql_host and mysql_db:
    app.config['SQLALCHEMY_DATABASE_URI'] = f"mysql+pymysql://{mysql_user}:{mysql_password}@{mysql_host}/{mysql_db}"
else:
    app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'sistema.db')
# ----- **** FIM DA "REFORMA" **** -----


# --- **** CONFIGURAÇÃO DO "CARTEIRO" (ETAPA 4) **** ---
app.config['MAIL_SERVER'] = os.environ.get('MAIL_SERVER')
app.config['MAIL_PORT'] = int(os.environ.get('MAIL_PORT', 587))
app.config['MAIL_USE_TLS'] = os.environ.get('MAIL_USE_TLS', 'true').lower() in ['true', 'on', '1']
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = ('GestorOS (Não Responda)', app.config['MAIL_USERNAME'])

# 3. Iniciar o "Carteiro"
mail = Mail(app)
# --- **** FIM DA MUDANÇA **** ---


# 3. **** NOVA CONFIGURAÇÃO: CLOUDINARY ****
cloudinary.config( 
    cloud_name = os.environ.get('CLOUDINARY_CLOUD_NAME'), 
    api_key = os.environ.get('CLOUDINARY_API_KEY'), 
    api_secret = os.environ.get('CLOUDINARY_API_SECRET')
)
app.config['MAX_CONTENT_LENGTH'] = 10 * 1024 * 1024
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'mp4', 'mov', 'avi'}

def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS
# --- **** FIM DA MUDANÇA **** ---


# 4. Iniciar o "tradutor" (SQLAlchemy)
db = SQLAlchemy(app)

# 5. INICIAR O "MESTRE DE OBRAS" (Migrate)
migrate = Migrate(app, db)


# 5.5 **** NOVO: CONFIGURAR O "SEGURANÇA" (Login Manager) ****
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "error" 


# --- **** "MOLDE" DE PERFIL (ETAPA 3) **** ---
class Perfil(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(50), unique=True, nullable=False) # Ex: "Gerente", "Técnico"
    # "Ponte" 1-para-N: Um Perfil pode ter N Usuários
    usuarios = db.relationship('Usuario', backref='perfil', lazy=True)
    
    def __repr__(self):
        return f'<Perfil {self.nome}>'
# --- **** FIM DA MUDANÇA **** ---


# 6. **** "MOLDE" DE USUÁRIO (ATUALIZADO) ****
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) 
    
    email = db.Column(db.String(120), unique=True, nullable=False)
    status = db.Column(db.String(20), nullable=False, default='Ativo') # Ativo, Férias, Demitido
    observacoes = db.Column(db.Text, nullable=True)
    precisa_trocar_senha = db.Column(db.Boolean, default=True, nullable=False) # Força a troca
    
    # "Ponte" 1-para-1: Um Usuário está ligado a UM Funcionário
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True, nullable=False)

    # --- "PONTE" PARA O PERFIL (ETAPA 3) ---
    perfil_id = db.Column(db.Integer, db.ForeignKey('perfil.id'), nullable=False)
    # --- FIM ---

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

    # --- **** MUDANÇA (FASE 4): FUNÇÕES DE TOKEN **** ---
    def get_reset_token(self):
        """ Cria um token seguro para resetar a senha (válido por 1 hora) """
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        return s.dumps(self.id, salt='password-reset-salt')

    @staticmethod
    def verify_reset_token(token, max_age_segundos=3600):
        """ Verifica o token. Retorna o ID do usuário se for válido, ou None se expirar/falhar """
        s = URLSafeTimedSerializer(app.config['SECRET_KEY'])
        try:
            user_id = s.loads(
                token, 
                salt='password-reset-salt', 
                max_age=max_age_segundos
            )
        except (SignatureExpired, BadTimeSignature):
            return None # Token expirado ou inválido
        return user_id
    # --- **** FIM DA MUDANÇA **** ---

# 6.5 **** NOVO: Ensina o LoginManager a encontrar um usuário ****
@login_manager.user_loader
def load_user(user_id):
    return Usuario.query.get(int(user_id))


# 7. CRIAR O "MOLDE" DO PARCEIRO DE NEGÓCIO (Sem mudança)
class ParceiroNegocio(db.Model):
    __tablename__ = 'parceiro_negocio' 
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=True) 
    cpf_cnpj = db.Column(db.String(18), nullable=True, unique=True) 
    endereco = db.Column(db.String(200), nullable=True)
    eh_cliente = db.Column(db.Boolean, default=False, nullable=False)
    eh_fornecedor = db.Column(db.Boolean, default=False, nullable=False)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    motivo_inativacao = db.Column(db.String(200), nullable=True)
    ordens_servico = db.relationship('OrdemServico', backref='parceiro', lazy=True)


# 8. **** NOVO "MOLDE": CARREIRA ****
class Carreira(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome_cargo = db.Column(db.String(100), unique=True, nullable=False)
    competencias = db.Column(db.Text, nullable=True)
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    funcionarios = db.relationship('Funcionario', backref='cargo', lazy=True)


# 9. **** "MOLDE" REFORMADO: Funcionario (ATUALIZADO) ****
class Funcionario(db.Model):
    __tablename__ = 'funcionario' 
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    cargo_id = db.Column(db.Integer, db.ForeignKey('carreira.id'), nullable=False)
    ordens_servico_funcionario = db.relationship('OrdemServico', backref='funcionario', lazy=True)
    
    usuario = db.relationship('Usuario', backref='funcionario', uselist=False)


# 10. **** "MOLDE" ATUALIZADO: ORDEM DE SERVIÇO ****
class OrdemServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipamento = db.Column(db.String(200), nullable=False)
    defeito_reclamado = db.Column(db.String(500), nullable=False)
    acessorios = db.Column(db.String(200), nullable=True)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False) 
    estado = db.Column(db.String(50), nullable=False, default='Aguardando Orçamento')
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiro_negocio.id'), nullable=False)
    valor_servico = db.Column(db.Float, nullable=True)
    observacao_final = db.Column(db.String(500), nullable=True)
    midias = db.relationship('MidiaOS', backref='ordem_servico', lazy=True, cascade="all, delete-orphan")


# 11. **** NOVO "MOLDE": MIDIA OS ****
class MidiaOS(db.Model):
    __tablename__ = 'midia_os'
    id = db.Column(db.Integer, primary_key=True)
    link_midia = db.Column(db.String(500), nullable=False) 
    tipo_midia = db.Column(db.String(50), nullable=True) 
    public_id = db.Column(db.String(200), nullable=True) 
    os_id = db.Column(db.Integer, db.ForeignKey('ordem_servico.id'), nullable=False)


# --- **** NOVA FUNÇÃO: Gerador de Senha **** ---
def gerar_senha_aleatoria(tamanho=10):
    caracteres = string.ascii_letters + string.digits + string.punctuation
    senha = [
        secrets.choice(string.ascii_lowercase),
        secrets.choice(string.ascii_uppercase),
        secrets.choice(string.digits),
        secrets.choice(string.punctuation)
    ]
    for _ in range(tamanho - 4):
        senha.append(secrets.choice(caracteres))
    
    secrets.SystemRandom().shuffle(senha) 
    return "".join(senha)
# --- **** FIM DA MUDANÇA **** ---


# --- **** FUNÇÃO DE ENVIAR E-MAIL (AGORA "INTELIGENTE") **** ---
def enviar_email_senha(destinatario, username, nova_senha, tipo="criacao"):
    """
    Função "carteiro" para enviar a senha temporária.
    Agora "inteligente", com base no 'tipo'.
    """
    try:
        # Define o Título (Subject) e o Corpo (html) com base no 'tipo'
        if tipo == "reset":
            subject = "Sua senha do GestorOS foi redefinida"
            corpo_html = f"""
            <p>Olá, {username}!</p>
            <p>Sua senha no GestorOS foi <b>redefinida</b> por um administrador.</p>
            <p>Use esta nova senha temporária para fazer seu próximo login:</p>
            <p><strong>{nova_senha}</strong></p>
            <p>Você será solicitado a trocar esta senha assim que entrar.</p>
            <br>
            <p><em>(Esta é uma mensagem automática, não responda.)</em></p>
            """
        else: # O padrão é "criacao"
            subject = "Seu acesso ao GestorOS foi criado!"
            corpo_html = f"""
            <p>Olá, {username}!</p>
            <p>Um novo usuário foi criado para você no GestorOS.</p>
            <p>Use esta senha temporária para fazer seu primeiro login:</p>
            <p><strong>{nova_senha}</strong></p>
            <p>Você será solicitado a trocar esta senha assim que entrar.</p>
            <br>
            <p><em>(Esta é uma mensagem automática, não responda.)</em></p>
            """

        # Monta a mensagem
        msg = Message(
            subject=subject,
            recipients=[destinatario] 
        )
        msg.html = corpo_html
        
        mail.send(msg)
        return True # Sucesso
        
    except Exception as e:
        # Se falhar, registra o erro no log (ou no console)
        print(f"ERRO AO ENVIAR E-MAIL: {str(e)}")
        logging.error(f"Falha ao enviar e-mail para {destinatario}: {str(e)}")
        return False # Falha
# --- **** FIM DA MUDANÇA 1 **** ---


# --- **** O "GUARDIÃO" (DECORATOR DE PERMISSÃO) **** ---
def permissao_necessaria(perfil_nome):
    """
    Verifica se o usuário logado tem o perfil necessário para acessar a rota.
    """
    def decorator(f):
        @wraps(f)
        def decorated_function(*args, **kwargs):
            # 1. Se não estiver logado, o @login_required (que vem antes) já barrou.
            if not current_user.is_authenticated:
                return redirect(url_for('login'))
                
            # 2. Verifica se o perfil do usuário é o perfil necessário
            if current_user.perfil.nome != perfil_nome:
                # 3. Se não for, barra o acesso
                flash(f'Acesso negado. Você precisa de permissão de "{perfil_nome}" para acessar esta página.', 'error')
                return redirect(url_for('ola_mundo'))
                
            # 4. Se for, permite o acesso
            return f(*args, **kwargs)
        return decorated_function
    return decorator
# --- **** FIM DA MUDANÇA **** ---


# FILTRO DE TELEFONE
def format_telefone(value):
    if not value or not value.isdigit():
        return value
    length = len(value)
    if length == 10:
        return f"({value[0:2]}) {value[2:6]}-{value[6:10]}"
    elif length == 11:
        return f"({value[0:2]}) {value[2:7]}-{value[7:11]}"
    else:
        return value
app.jinja_env.filters['format_telefone'] = format_telefone


# 12. **** ROTAS DE LOGIN/LOGOUT (ATUALIZADAS) ****
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ola_mundo')) 
    
    if request.method == 'POST':
        username = request.form['username'].upper()
        password = request.form['password']
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            if user.status != 'Ativo':
                flash('Este usuário não está Ativo. Contate o administrador.', 'error')
                return redirect(url_for('login'))
                
            login_user(user) 
            
            if user.precisa_trocar_senha:
                flash('Este é o seu primeiro login. Por favor, cadastre uma nova senha.', 'success')
                return redirect(url_for('trocar_senha'))
            
            return redirect(url_for('ola_mundo'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
            
    return render_template('login.html') 

@app.route('/trocar-senha', methods=['GET', 'POST'])
@login_required
def trocar_senha():
    if request.method == 'POST':
        senha_antiga = request.form['senha_antiga']
        senha_nova = request.form['senha_nova']
        confirma_senha = request.form['confirma_senha']

        if not current_user.check_password(senha_antiga):
            flash('A "Senha Antiga" está incorreta.', 'error')
            return redirect(url_for('trocar_senha'))
        
        if (len(senha_nova) < 10 or 
            not re.search(r"[a-z]", senha_nova) or 
            not re.search(r"[A-Z]", senha_nova) or 
            not re.search(r"\d", senha_nova) or 
            not re.search(r"[\W_]", senha_nova)): 
            flash('Senha nova inválida. Deve ter 10+ caracteres, minúscula, maiúscula, número e caractere especial.', 'error')
            return redirect(url_for('trocar_senha'))

        if senha_nova != confirma_senha:
            flash('A "Senha Nova" e a "Confirmação" não coincidem.', 'error')
            return redirect(url_for('trocar_senha'))

        current_user.set_password(senha_nova)
        current_user.precisa_trocar_senha = False 
        db.session.commit()
        
        flash('Senha atualizada com sucesso!', 'success')
        return redirect(url_for('ola_mundo'))

    return render_template('trocar_senha.html')


@app.route('/logout')
@login_required 
def logout():
    logout_user() 
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


# --- **** MUDANÇA (FASE 4): NOVAS ROTAS DE RECUPERAÇÃO **** ---

def enviar_email_reset(usuario, token):
    """ Função específica para enviar o e-mail de RESET """
    try:
        # url_for(_external=True) gera o link completo (com https://...)
        link_de_reset = url_for('resetar_com_token', token=token, _external=True)
        
        msg = Message(
            subject="Recuperação de Senha - GestorOS",
            recipients=[usuario.email] 
        )
        msg.html = f"""
        <p>Olá, {usuario.username}!</p>
        <p>Recebemos uma solicitação para redefinir sua senha no GestorOS.</p>
        <p>Clique no link abaixo para criar uma nova senha:</p>
        <p><a href="{link_de_reset}">{link_de_reset}</a></p>
        <p>Este link é válido por 1 hora. Se você não solicitou isso, ignore este e-mail.</p>
        <br>
        <p><em>(Esta é uma mensagem automática, não responda.)</em></p>
        """
        mail.send(msg)
        return True
    except Exception as e:
        print(f"ERRO AO ENVIAR E-MAIL DE RESET: {str(e)}")
        logging.error(f"Falha ao enviar e-mail de reset para {usuario.email}: {str(e)}")
        return False

@app.route('/recuperar', methods=['GET', 'POST'])
def recuperar_senha():
    """ Página 'Esqueceu a Senha' - (Não precisa de login) """
    if current_user.is_authenticated:
        return redirect(url_for('ola_mundo'))
        
    if request.method == 'POST':
        email_digitado = request.form.get('email')
        usuario = Usuario.query.filter_by(email=email_digitado).first()
        
        if usuario:
            # 1. Gera o Token
            token = usuario.get_reset_token()
            # 2. Envia o E-mail
            email_enviado = enviar_email_reset(usuario, token)
            
            if email_enviado:
                flash(f'Um e-mail de recuperação foi enviado para {email_digitado}. Verifique sua caixa de entrada (e spam).', 'success')
            else:
                flash('O usuário foi encontrado, mas houve um erro ao enviar o e-mail. Contate o administrador.', 'error')
            
            return redirect(url_for('login'))
        else:
            # (Não informamos se o e-mail não existe, por segurança)
            flash('Se este e-mail estiver cadastrado, um link de recuperação será enviado.', 'success')
            return redirect(url_for('login'))
            
    return render_template('recuperar_senha.html')


@app.route('/resetar/<token>', methods=['GET', 'POST'])
def resetar_com_token(token):
    """ Página onde o usuário (vindo do e-mail) define a nova senha """
    if current_user.is_authenticated:
        return redirect(url_for('ola_mundo'))

    # 1. Verifica se o token é válido e quem é o dono
    user_id = Usuario.verify_reset_token(token)
    if not user_id:
        flash('O link de recuperação é inválido ou expirou. Tente novamente.', 'error')
        return redirect(url_for('recuperar_senha'))
        
    usuario = Usuario.query.get(user_id)
    if not usuario:
        flash('Usuário não encontrado. O link pode estar corrompido.', 'error')
        return redirect(url_for('recuperar_senha'))

    # 2. Se o token for válido, mostra o formulário (POST)
    if request.method == 'POST':
        senha_nova = request.form['senha_nova']
        confirma_senha = request.form['confirma_senha']
        
        # 3. Validação da senha nova (igual à da rota 'trocar_senha')
        if (len(senha_nova) < 10 or 
            not re.search(r"[a-z]", senha_nova) or 
            not re.search(r"[A-Z]", senha_nova) or 
            not re.search(r"\d", senha_nova) or 
            not re.search(r"[\W_]", senha_nova)): 
            flash('Senha nova inválida. Deve ter 10+ caracteres, minúscula, maiúscula, número e caractere especial.', 'error')
            return render_template('resetar_com_token.html', token=token)
            
        if senha_nova != confirma_senha:
            flash('As senhas não coincidem.', 'error')
            return render_template('resetar_com_token.html', token=token)

        # 4. Salva a nova senha
        usuario.set_password(senha_nova)
        usuario.precisa_trocar_senha = False # O usuário acabou de definir
        db.session.commit()
        
        flash('Sua senha foi redefinida com sucesso! Você já pode fazer o login.', 'success')
        return redirect(url_for('login'))

    # (Método GET)
    return render_template('resetar_com_token.html', token=token)

# --- **** FIM DAS NOVAS ROTAS **** ---


# 13. Rota (página) principal (PROTEGIDA)
@app.route('/')
@login_required 
def ola_mundo():
    return render_template('index.html')


# 14. Rotas de Parceiro de Negócio (PN)
@app.route('/parceiro/inativar/<int:parceiro_id>', methods=['GET', 'POST'])
@login_required 
@permissao_necessaria('Gerente')
def inativar_parceiro(parceiro_id):
    parceiro_para_inativar = ParceiroNegocio.query.get_or_404(parceiro_id)
    # ... (resto do código igual) ...
    estados_finais = ['Concluído', 'Finalizado (Desistência)']
    os_abertas = OrdemServico.query.filter_by(parceiro_id=parceiro_id)\
                                  .filter(OrdemServico.estado.notin_(estados_finais))\
                                  .count()
    if os_abertas > 0:
        flash(f"ERRO: Parceiro não pode ser inativado. Existem {os_abertas} OS que não estão finalizadas.", 'error')
        if 'parceiros' in request.referrer:
             return redirect(url_for('parceiros'))
        return redirect(url_for('ola_mundo'))
    if request.method == 'POST':
        motivo = request.form['motivo']
        if len(motivo) < 20:
            flash('Motivo muito curto. Descreva melhor (mínimo 20 caracteres).', 'error')
            return render_template('inativar_parceiro.html', parceiro=parceiro_para_inativar)
        parceiro_para_inativar.ativo = False
        parceiro_para_inativar.motivo_inativacao = motivo
        db.session.commit()
        flash('Parceiro inativado com sucesso.', 'success')
        if 'parceiros' in request.referrer:
             return redirect(url_for('parceiros'))
        return redirect(url_for('ola_mundo'))
    else:
        return render_template('inativar_parceiro.html', parceiro=parceiro_para_inativar)

@app.route('/parceiro/reativar/<int:parceiro_id>')
@login_required 
@permissao_necessaria('Gerente')
def reativar_parceiro(parceiro_id):
    parceiro_para_reativar = ParceiroNegocio.query.get_or_404(parceiro_id)
    # ... (resto do código igual) ...
    parceiro_para_reativar.ativo = True
    parceiro_para_reativar.motivo_inativacao = None
    db.session.commit()
    flash('Parceiro reativado com sucesso.', 'success')
    if 'parceiros' in request.referrer:
         return redirect(url_for('parceiros'))
    return redirect(url_for('ola_mundo'))

@app.route('/parceiros', methods=['GET', 'POST'])
@login_required 
@permissao_necessaria('Gerente')
def parceiros():
    if request.method == 'POST':
        # ... (resto do código de validação igual) ...
        nome = request.form['nome']
        telefone_raw = re.sub(r'\D', '', request.form.get('telefone', '')) 
        cpf_cnpj_raw = re.sub(r'\D', '', request.form.get('cpf_cnpj', '')) 
        endereco = request.form.get('endereco', '')
        eh_cliente = 'eh_cliente' in request.form
        eh_fornecedor = 'eh_fornecedor' in request.form
        erros = []
        if not nome:
            erros.append('O campo "Nome" é obrigatório.')
        if not telefone_raw:
            erros.append('O campo "Telefone" é obrigatório.')
        if not cpf_cnpj_raw:
            erros.append('O campo "CPF/CNPJ" é obrigatório.')
        if not endereco:
            erros.append('O campo "Endereço" é obrigatório.')
        if not eh_cliente and not eh_fornecedor:
            erros.append('Você deve selecionar pelo menos uma função (Cliente ou Fornecedor).')
        cpf_cnpj = cpf_cnpj_raw if cpf_cnpj_raw else None
        if cpf_cnpj:
            existente = ParceiroNegocio.query.filter_by(cpf_cnpj=cpf_cnpj).first()
            if existente:
                erros.append(f'O CPF/CNPJ "{cpf_cnpj}" já está cadastrado para o parceiro "{existente.nome}".')
        if erros:
            for erro in erros:
                flash(f'ERRO: {erro}', 'error')
            return render_template('parceiros.html', form_data=request.form)
        novo_pn = ParceiroNegocio(
            nome=nome,
            telefone=telefone_raw, 
            cpf_cnpj=cpf_cnpj,
            endereco=endereco,
            eh_cliente=eh_cliente,
            eh_fornecedor=eh_fornecedor
        )
        try:
            db.session.add(novo_pn)
            db.session.commit()
            flash(f'Parceiro "{nome}" cadastrado com sucesso!', 'success')
            return redirect(url_for('parceiros'))
        except Exception as e:
            db.session.rollback()
            flash(f'ERRO ao salvar no banco: {str(e)}', 'error')
            return render_template('parceiros.html', form_data=request.form)
    else: 
        return render_template('parceiros.html', form_data={})

@app.route('/parceiros/search')
@login_required 
@permissao_necessaria('Gerente')
def search_parceiros():
    # ... (resto do código igual) ...
    termo = request.args.get('termo', '')
    parceiros = ParceiroNegocio.query.filter(
        ParceiroNegocio.nome.ilike(f'%{termo}%')
    ).all()
    resultados = []
    for pn in parceiros:
        funcoes = ""
        if pn.eh_cliente: funcoes += "[Cliente] "
        if pn.eh_fornecedor: funcoes += "[Fornecedor] "
        if pn.ativo:
            status = '<span style="color: green;">Ativo</span>'
            link_acao = f'<a href="{url_for("inativar_parceiro", parceiro_id=pn.id)}">[Inativar]</a>'
        else:
            status = '<span style="color: red;">Inativo</span>'
            link_acao = f'<a href="{url_for("reativar_parceiro", parceiro_id=pn.id)}">[Reativar]</a>'
        link_editar = f'<a href="{url_for("editar_parceiro", pn_id=pn.id)}">[Editar]</a>'
        resultados.append({
            'nome': pn.nome,
            'funcoes': funcoes.strip(),
            'status': status,
            'link_acao': link_acao,
            'link_editar': link_editar 
        })
    return jsonify(resultados)

@app.route('/parceiros/editar/<int:pn_id>', methods=['GET', 'POST'])
@login_required 
@permissao_necessaria('Gerente')
def editar_parceiro(pn_id):
    # ... (resto do código igual) ...
    pn_para_editar = ParceiroNegocio.query.get_or_404(pn_id)
    if request.method == 'POST':
        pn_para_editar.nome = request.form['nome']
        telefone_raw = re.sub(r'\D', '', request.form.get('telefone', '')) 
        cpf_cnpj_raw = re.sub(r'\D', '', request.form.get('cpf_cnpj', '')) 
        pn_para_editar.endereco = request.form.get('endereco', '')
        pn_para_editar.eh_cliente = 'eh_cliente' in request.form
        pn_para_editar.eh_fornecedor = 'eh_fornecedor' in request.form
        erros = []
        if not pn_para_editar.nome:
            erros.append('O campo "Nome" é obrigatório.')
        cpf_cnpj = cpf_cnpj_raw if cpf_cnpj_raw else None
        if cpf_cnpj:
            existente = ParceiroNegocio.query.filter(
                ParceiroNegocio.cpf_cnpj == cpf_cnpj,
                ParceiroNegocio.id != pn_id 
            ).first()
            if existente:
                erros.append(f'O CPF/CNPJ "{cpf_cnpj}" já está cadastrado para o parceiro "{existente.nome}".')
        if erros:
            for erro in erros:
                flash(f'ERRO: {erro}', 'error')
            return render_template('editar_parceiro.html', pn=pn_para_editar)
        pn_para_editar.telefone = telefone_raw
        pn_para_editar.cpf_cnpj = cpf_cnpj
        db.session.commit()
        flash(f'Parceiro "{pn_para_editar.nome}" atualizado com sucesso!', 'success')
        return redirect(url_for('parceiros'))
    else: 
        return render_template('editar_parceiro.html', pn=pn_para_editar)


# 15. **** ROTAS DE CADASTRO (Menu Principal e Sub-menus) ****

@app.route('/cadastros')
@login_required
@permissao_necessaria('Gerente')
def cadastros():
    # Esta rota apenas mostra o "menu" de cadastros
    return render_template('cadastros.html')

@app.route('/carreiras', methods=['GET', 'POST'])
@login_required
@permissao_necessaria('Gerente')
def carreiras():
    form_data = {} # Inicializa o form_data
    if request.method == 'POST':
        nome_cargo = request.form['nome_cargo']
        competencias = request.form['competencias']
        form_data = request.form # Salva o que o usuário digitou
        
        if not nome_cargo:
            flash('O campo "Nome do Cargo" é obrigatório.', 'error')
        else:
            nova_carreira = Carreira(nome_cargo=nome_cargo, competencias=competencias)
            db.session.add(nova_carreira)
            db.session.commit()
            flash('Cargo cadastrado com sucesso!', 'success')
            return redirect(url_for('carreiras'))

    return render_template('carreiras.html', form_data=form_data)

@app.route('/carreiras/search')
@login_required
@permissao_necessaria('Gerente')
def search_carreiras():
    termo = request.args.get('termo', '')
    
    # Busca no banco Carreiras cujo NOME contenha o termo
    carreiras = Carreira.query.filter(
        Carreira.nome_cargo.ilike(f'%{termo}%')
    ).all()
    
    # Formata os resultados para o JavaScript
    resultados = []
    for cargo in carreiras:
        # Prepara o texto do Status
        if cargo.ativo:
            status = '<span style="color: green;">Ativo</span>'
            link_acao = f'<a href="{url_for("inativar_carreira", cargo_id=cargo.id)}" style="color: #dc3545;">[Inativar]</a>'
        else:
            status = '<span style="color: red;">Inativo</span>'
            link_acao = f'<a href="{url_for("reativar_carreira", cargo_id=cargo.id)}">[Reativar]</a>'
        
        link_editar = f'<a href="{url_for("editar_carreira", cargo_id=cargo.id)}">[Editar]</a>'

        resultados.append({
            'nome_cargo': cargo.nome_cargo,
            'competencias': cargo.competencias or '', # Garante que não seja 'None'
            'status': status,
            'link_acao': link_acao,
            'link_editar': link_editar
        })
        
    return jsonify(resultados)

@app.route('/carreiras/editar/<int:cargo_id>', methods=['GET', 'POST'])
@login_required
@permissao_necessaria('Gerente')
def editar_carreira(cargo_id):
    cargo = Carreira.query.get_or_404(cargo_id)
    if request.method == 'POST':
        cargo.nome_cargo = request.form['nome_cargo']
        cargo.competencias = request.form['competencias']
        db.session.commit()
        flash('Cargo atualizado com sucesso!', 'success')
        return redirect(url_for('carreiras'))
    
    return render_template('editar_carreira.html', cargo=cargo)

@app.route('/carreiras/inativar/<int:cargo_id>')
@login_required
@permissao_necessaria('Gerente')
def inativar_carreira(cargo_id):
    cargo = Carreira.query.get_or_404(cargo_id)
    # "Sabedoria": Verifica se algum funcionário está usando este cargo
    funcionarios_no_cargo = Funcionario.query.filter_by(cargo_id=cargo_id).count()
    if funcionarios_no_cargo > 0:
        flash(f'ERRO: Não é possível inativar o cargo "{cargo.nome_cargo}", pois {funcionarios_no_cargo} funcionário(s) estão associados a ele.', 'error')
    else:
        cargo.ativo = False
        db.session.commit()
        flash(f'Cargo "{cargo.nome_cargo}" inativado.', 'success')
    return redirect(url_for('carreiras'))

@app.route('/carreiras/reativar/<int:cargo_id>')
@login_required
@permissao_necessaria('Gerente')
def reativar_carreira(cargo_id):
    cargo = Carreira.query.get_or_404(cargo_id)
    cargo.ativo = True
    db.session.commit()
    flash(f'Cargo "{cargo.nome_cargo}" reativado.', 'success')
    return redirect(url_for('carreiras'))

@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required 
@permissao_necessaria('Gerente')
def funcionarios():
    if request.method == 'POST':
        nome = request.form['nome']
        cargo_id = request.form['cargo_id']
        
        if not nome or not cargo_id:
            flash('Todos os campos são obrigatórios.', 'error')
        else:
            novo_funcionario = Funcionario(nome=nome, cargo_id=cargo_id)
            db.session.add(novo_funcionario)
            db.session.commit()
            flash('Funcionário cadastrado com sucesso!', 'success')
            return redirect(url_for('funcionarios'))
    
    # Busca para os dropdowns e listas
    lista_de_funcionarios = Funcionario.query.all()
    lista_de_carreiras = Carreira.query.filter_by(ativo=True).all()
    
    return render_template('funcionarios.html', 
                           funcionarios=lista_de_funcionarios, 
                           carreiras=lista_de_carreiras)

@app.route('/funcionario/apagar/<int:funcionario_id>')
@login_required 
@permissao_necessaria('Gerente')
def apagar_funcionario(funcionario_id):
    funcionario_para_apagar = Funcionario.query.get_or_404(funcionario_id)
    try:
        db.session.delete(funcionario_para_apagar)
        db.session.commit()
        flash('Funcionário apagado com sucesso.', 'success')
    except Exception as e:
        db.session.rollback()
        flash(f"Não foi possível apagar o funcionário. Verifique se ele possui OS associadas.", "error")
        
    return redirect(url_for('funcionarios'))

# --- **** ROTA DE USUÁRIOS (ETAPA 4) **** ---
@app.route('/usuarios', methods=['GET', 'POST'])
@login_required
@permissao_necessaria('Gerente') # <-- "TRANCA"
def cadastro_usuarios():
    
    if request.method == 'POST':
        funcionario_id = request.form.get('funcionario_id')
        username = request.form.get('username').upper() 
        email = request.form.get('email')
        status = request.form.get('status')
        observacoes = request.form.get('observacoes')
        perfil_id = request.form.get('perfil_id') 
        
        # Validação
        erros = []
        if not funcionario_id or funcionario_id == '0':
            erros.append('O campo "Funcionário" é obrigatório.')
        if not perfil_id or perfil_id == '0': 
            erros.append('O campo "Perfil" é obrigatório.') 
        if not username:
            erros.append('O campo "Username" é obrigatório.')
        if not email:
            erros.append('O campo "E-mail" é obrigatório.')
        
        # Verifica se o 'username' ou 'email' ou 'funcionario' já estão em uso
        if Usuario.query.filter_by(username=username).first():
            erros.append(f'O Username "{username}" já está em uso.')
        if Usuario.query.filter_by(email=email).first():
            erros.append(f'O E-mail "{email}" já está em uso.')
        if Usuario.query.filter_by(funcionario_id=funcionario_id).first():
            erros.append('Este funcionário já possui um usuário. Edite-o em vez de criar um novo.')
            
        if erros:
            for erro in erros:
                flash(erro, 'error')
            # Busca funcionários que AINDA NÃO têm um usuário
            funcionarios_sem_usuario = Funcionario.query.filter(Funcionario.usuario == None).all()
            todos_perfis = Perfil.query.all() 
            return render_template('cadastro_usuarios.html', 
                                   form_data=request.form, 
                                   funcionarios=funcionarios_sem_usuario,
                                   perfis=todos_perfis) 

        # Se passou nas validações
        senha_aleatoria = gerar_senha_aleatoria()
        
        novo_usuario = Usuario(
            username=username,
            email=email,
            status=status,
            observacoes=observacoes,
            funcionario_id=funcionario_id,
            perfil_id=perfil_id, 
            precisa_trocar_senha=True 
        )
        novo_usuario.set_password(senha_aleatoria)
        
        db.session.add(novo_usuario)
        
        # ---- **** LÓGICA DE E-MAIL (ETAPA 4) **** ----
        try:
            db.session.commit()
            
            # Tenta enviar o e-mail (agora passando o 'tipo')
            email_enviado = enviar_email_senha(
                novo_usuario.email, 
                novo_usuario.username, 
                senha_aleatoria, 
                tipo="criacao" # <-- Informa que é uma "criação"
            )
            
            if email_enviado:
                flash(f'Usuário "{username}" criado com sucesso! A senha temporária foi enviada para {novo_usuario.email}.', 'success')
            else:
                # Se o e-mail falhar, avisa o admin (você)
                flash(f'Usuário "{username}" criado, MAS O E-MAIL FALHOU. Verifique as configurações.', 'error')
                flash(f'Atenção: A senha temporária (que falhou) é: {senha_aleatoria}', 'success')

        except Exception as e:
            # Se o DB falhar
            db.session.rollback()
            flash(f'ERRO ao salvar no banco: {str(e)}', 'error')
        # ---- **** FIM DA MUDANÇA **** ----
            
        return redirect(url_for('cadastro_usuarios'))

    else: # (Método GET)
        funcionarios_sem_usuario = Funcionario.query.filter(Funcionario.usuario == None).all()
        todos_usuarios = Usuario.query.all()
        todos_perfis = Perfil.query.all() 
        
        return render_template('cadastro_usuarios.html', 
                               form_data={}, 
                               funcionarios=funcionarios_sem_usuario,
                               usuarios=todos_usuarios,
                               perfis=todos_perfis) 

# --- **** ROTA DE RESETAR SENHA (ETAPA 4) **** ---
@app.route('/usuario/resetar/<int:user_id>')
@login_required
@permissao_necessaria('Gerente') # <-- "TRANCA"
def resetar_senha(user_id):
    user = Usuario.query.get_or_404(user_id)
    
    nova_senha = gerar_senha_aleatoria() 
    user.set_password(nova_senha)
    user.precisa_trocar_senha = True 
    
    # Tenta enviar o e-mail (agora passando o 'tipo')
    email_enviado = enviar_email_senha(
        user.email, 
        user.username, 
        nova_senha, 
        tipo="reset" # <-- Informa que é um "reset"
    )
    
    db.session.commit()
    
    if email_enviado:
        flash(f'Senha resetada para "{user.username}". A nova senha foi enviada para {user.email}.', 'success')
    else:
        # Se o e-mail falhar, avisa o admin (você)
        flash(f'Senha resetada para "{user.username}", MAS O E-MAIL FALHOU.', 'error')
        flash(f'Atenção: A nova senha (que falhou) é: {nova_senha}', 'success')
        
    return redirect(url_for('cadastro_usuarios'))
# --- **** FIM DA ROTA **** ---


# --- **** ROTA DE EDITAR USUÁRIO (ETAPA 3) **** ---
@app.route('/usuario/editar/<int:user_id>', methods=['GET', 'POST'])
@login_required
@permissao_necessaria('Gerente') # <-- "TRANCA"
def editar_usuario(user_id):
    user = Usuario.query.get_or_404(user_id)
    
    if request.method == 'POST':
        novo_email = request.form.get('email')
        novo_status = request.form.get('status')
        novas_observacoes = request.form.get('observacoes')
        
        # Validação (Sabedoria)
        if novo_email != user.email:
            email_existente = Usuario.query.filter(
                Usuario.email == novo_email, 
                Usuario.id != user_id
            ).first()
            if email_existente:
                flash(f'ERRO: O e-mail "{novo_email}" já está em uso pelo usuário "{email_existente.username}".', 'error')
                return render_template('editar_usuario.html', usuario=user)
        
        user.email = novo_email
        user.status = novo_status
        user.observacoes = novas_observacoes
        
        db.session.commit()
        
        flash(f'Usuário "{user.username}" atualizado com sucesso!', 'success')
        return redirect(url_for('cadastro_usuarios'))

    else: # (Método GET)
        return render_template('editar_usuario.html', usuario=user)
# --- **** FIM DA ROTA **** ---


# 16. Rotas de Ordem de Serviço (OS)
# (Estas rotas NÃO SÃO DE GERENTE, são de Técnico/Padrão)

# --- (Rota /abrir_os) ---
@app.route('/abrir_os', methods=['GET', 'POST'])
@login_required 
def abrir_os():
    if request.method == 'POST':
        id_do_parceiro = request.form['parceiro_id']
        
        parceiro_selecionado = ParceiroNegocio.query.get(id_do_parceiro)
        
        if not parceiro_selecionado.eh_cliente or not parceiro_selecionado.ativo:
            flash(f"ERRO: O PN '{parceiro_selecionado.nome}' não é um cliente ativo. Verifique o cadastro.", 'error')
            
            clientes_ativos = ParceiroNegocio.query.filter_by(eh_cliente=True, ativo=True).all()
            todos_tecnicos = Funcionario.query.all()
            return render_template('abrir_os.html',
                                   clientes=clientes_ativos,
                                   tecnicos=todos_tecnicos,
                                   dados_form=request.form)

        # 1. Salva a OS (sem mídia) para obter um ID
        nova_os = OrdemServico(
            equipamento=request.form['equipamento'],
            defeito_reclamado=request.form['defeito'],
            acessorios=request.form.get('acessorios'),
            tecnico_id=request.form['tecnico_id'],
            parceiro_id=id_do_parceiro
        )
        db.session.add(nova_os)
        db.session.commit()
        
        # --- Lógica de Upload (após a OS ter um ID) ---
        files = request.files.getlist('midias[]')
        
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                
                folder_name = f"GestorOS/OS-{nova_os.id}"
                
                upload_result = cloudinary.uploader.upload(
                    file, 
                    folder=folder_name,
                    resource_type="auto" 
                )
                
                nova_midia = MidiaOS(
                    link_midia = upload_result.get('secure_url'),
                    tipo_midia = upload_result.get('resource_type'),
                    public_id = upload_result.get('public_id'),
                    os_id = nova_os.id 
                )
                db.session.add(nova_midia)

        db.session.commit() # Salva as mídias
        flash('Ordem de Serviço aberta com sucesso!', 'success')
        return redirect(url_for('ordens_servico')) 

    else:
        clientes_ativos = ParceiroNegocio.query.filter_by(eh_cliente=True, ativo=True).all()
        todos_tecnicos = Funcionario.query.all()

        return render_template('abrir_os.html',
                               clientes=clientes_ativos,
                               tecnicos=todos_tecnicos,
                               dados_form={})

# --- (Rota /ordens) ---
@app.route('/ordens')
@login_required 
def ordens_servico():
    filtro_estado = request.args.get('estado', 'Abertas') 
    filtro_tecnico_id = request.args.get('tecnico_id', 'todos') 
    
    query = OrdemServico.query
    estados_finais = ['Concluído', 'Finalizado (Desistência)']

    if filtro_estado == 'Abertas':
        query = query.filter(OrdemServico.estado.notin_(estados_finais))
    elif filtro_estado == 'Finalizadas':
        query = query.filter(OrdemServico.estado.in_(estados_finais))

    if filtro_tecnico_id != 'todos':
        query = query.filter_by(tecnico_id=int(filtro_tecnico_id))

    lista_de_os = query.order_by(OrdemServico.id.desc()).all()
    
    todos_tecnicos = Funcionario.query.all() 

    return render_template('ordens_servico.html',
                           ordens_servico=lista_de_os,
                           todos_tecnicos=todos_tecnicos,
                           filtro_estado=filtro_estado,
                           filtro_tecnico_id=filtro_tecnico_id)

# --- (Rota /os/editar) ---
@app.route('/os/editar/<int:os_id>', methods=['GET', 'POST'])
@login_required 
def editar_os(os_id):
    os_para_editar = OrdemServico.query.get_or_404(os_id)

    if request.method == 'POST':
        # 1. Atualiza os dados normais
        os_para_editar.parceiro_id = request.form['parceiro_id'] 
        os_para_editar.equipamento = request.form['equipamento']
        os_para_editar.defeito_reclamado = request.form['defeito']
        os_para_editar.acessorios = request.form.get('acessorios')
        os_para_editar.estado = request.form['estado']
        os_para_editar.tecnico_id = request.form['tecnico_id'] 
        
        # 2. Lógica de Upload (igual à de "abrir_os")
        files = request.files.getlist('midias[]')
        for file in files:
            if file and allowed_file(file.filename):
                filename = secure_filename(file.filename)
                folder_name = f"GestorOS/OS-{os_para_editar.id}" # Usa o ID da OS existente
                
                upload_result = cloudinary.uploader.upload(
                    file, 
                    folder=folder_name,
                    resource_type="auto"
                )
                
                nova_midia = MidiaOS(
                    link_midia = upload_result.get('secure_url'),
                    tipo_midia = upload_result.get('resource_type'),
                    public_id = upload_result.get('public_id'),
                    os_id = os_para_editar.id # "Ponte" para a OS
                )
                db.session.add(nova_midia)

        db.session.commit()
        flash('OS atualizada com sucesso!', 'success')
        return redirect(url_for('ordens_servico'))
    
    else: # (Método GET)
        lista_clientes = ParceiroNegocio.query.filter_by(eh_cliente=True).all()
        todos_tecnicos = Funcionario.query.all() 
        
        midias_existentes = MidiaOS.query.filter_by(os_id=os_id).all()
        
        return render_template('editar_os.html',
                               os=os_para_editar,
                               clientes=lista_clientes,
                               tecnicos=todos_tecnicos,
                               midias=midias_existentes) 

# --- (Rota /os/midias) ---
@app.route('/os/<int:os_id>/midias')
@login_required
def ver_midias(os_id):
    os = OrdemServico.query.get_or_404(os_id)
    midias = MidiaOS.query.filter_by(os_id=os_id).all()
    return render_template('ver_midias.html', os=os, midias=midias)

# --- (Rota /midia/apagar) ---
@app.route('/midia/apagar/<int:midia_id>', methods=['POST'])
@login_required
def apagar_midia(midia_id):
    midia = MidiaOS.query.get_or_404(midia_id)
    os_id = midia.os_id 
    
    if midia.public_id:
        cloudinary.uploader.destroy(midia.public_id, resource_type=midia.tipo_midia)
    
    db.session.delete(midia)
    db.session.commit()
    
    flash('Mídia apagada com sucesso.', 'success')
    return redirect(url_for('editar_os', os_id=os_id))

# --- (Rota /os/finalizar) ---
@app.route('/os/finalizar/<int:os_id>', methods=['GET', 'POST'])
@login_required 
def finalizar_os(os_id):
    os = OrdemServico.query.get_or_404(os_id)
    # ... (resto do código igual) ...
    estados_finais = ['Concluído', 'Finalizado (Desistência)']
    if os.estado in estados_finais:
        flash(f'ERRO: A OS Nº{os.id} já está finalizada.', 'error')
        return redirect(url_for('ola_mundo'))
    if request.method == 'POST':
        tipo = request.form['tipo_finalizacao']
        valor_str = request.form['valor_servico']
        obs = request.form['observacao_final']
        if tipo == 'reparado':
            if not valor_str:
                flash('ERRO: O campo "Valor do Serviço" é obrigatório para OS reparada.', 'error')
                return render_template('finalizar_os.html', os=os, dados_form=request.form)
            try:
                valor_float = float(valor_str)
                if valor_float < 0:
                    raise ValueError
            except ValueError:
                flash('ERRO: Valor inválido. Use apenas números (ex: 150.50).', 'error')
                return render_template('finalizar_os.html', os=os, dados_form=request.form)
            os.estado = 'Concluído'
            os.valor_servico = valor_float
            os.observacao_final = None
        else: 
            if not obs or len(obs) < 10:
                flash('ERRO: A "Observação Final" é obrigatória (mín. 10 caracteres) para OS sem reparo.', 'error')
                return render_template('finalizar_os.html', os=os, dados_form=request.form)
            os.estado = 'Finalizado (Desistência)'
            os.valor_servico = 0
            os.observacao_final = obs
        db.session.commit()
        flash(f'OS Nº{os.id} finalizada com sucesso!', 'success')
        return redirect(url_for('ordens_servico'))
    else:
        return render_template('finalizar_os.html', os=os, dados_form={})


# 17. Rodar o servidor
if __name__ == '__main__':
    app.run(debug=True)