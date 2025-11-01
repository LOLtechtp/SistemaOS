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

# --- NOVO BLOCO: CONFIGURAÇÃO DE LOGS E AMBIENTE ---
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# --- BLOCO DE LOGGING COMENTADO (PARA NÃO DAR ERRO DE PERMISSÃO) ---
# ... (bloco de logging continua comentado) ...
# --- FIM DO BLOCO COMENTADO ---


# 2. Criar a aplicação
app = Flask(__name__)
app.config['SECRET_KEY'] = 'chave-secreta-para-dev' 

# ----- CONFIGURAÇÃO DO BANCO (COM CAMINHO ABSOLUTO PARA SQLITE) -----
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
# ----- FIM DA MUDANÇA -----


# 4. Iniciar o "tradutor" (SQLAlchemy)
db = SQLAlchemy(app)

# 5. INICIAR O "MESTRE DE OBRAS" (Migrate)
migrate = Migrate(app, db)


# 5.5 **** NOVO: CONFIGURAR O "SEGURANÇA" (Login Manager) ****
login_manager = LoginManager(app)
login_manager.login_view = 'login' 
login_manager.login_message = "Por favor, faça o login para acessar esta página."
login_manager.login_message_category = "error" 

# 6. **** "MOLDE" DE USUÁRIO ****
class Usuario(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False) 

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)

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
    # "Ponte" para os funcionários (Um Cargo tem muitos Funcionários)
    funcionarios = db.relationship('Funcionario', backref='cargo', lazy=True)


# 9. **** "MOLDE" REFORMADO: de Tecnico para Funcionario ****
class Funcionario(db.Model):
    __tablename__ = 'funcionario' # Novo nome da tabela
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    
    # "Ponte" para a Carreira (Um Funcionário tem um Cargo)
    cargo_id = db.Column(db.Integer, db.ForeignKey('carreira.id'), nullable=False)
    
    # "Ponte" para as OSs (Um Funcionário tem muitas OSs)
    ordens_servico_funcionario = db.relationship('OrdemServico', backref='funcionario', lazy=True)


# 10. **** "MOLDE" ATUALIZADO: ORDEM DE SERVIÇO ****
class OrdemServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipamento = db.Column(db.String(200), nullable=False)
    defeito_reclamado = db.Column(db.String(500), nullable=False)
    acessorios = db.Column(db.String(200), nullable=True)
    
    # "Ponte" atualizada para o Funcionário
    tecnico_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), nullable=False) 
    
    estado = db.Column(db.String(50), nullable=False, default='Aguardando Orçamento')
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiro_negocio.id'), nullable=False)
    valor_servico = db.Column(db.Float, nullable=True)
    observacao_final = db.Column(db.String(500), nullable=True)


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


# 11. **** ROTAS DE LOGIN/LOGOUT ****
@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('ola_mundo')) 
    
    if request.method == 'POST':
        username = request.form['username'].upper()
        password = request.form['password']
        
        user = Usuario.query.filter_by(username=username).first()
        
        if user and user.check_password(password):
            login_user(user) 
            return redirect(url_for('ola_mundo'))
        else:
            flash('Usuário ou senha inválidos.', 'error')
            
    return render_template('login.html') 

@app.route('/logout')
@login_required 
def logout():
    logout_user() 
    flash('Você foi desconectado com sucesso.', 'success')
    return redirect(url_for('login'))


# 12. Rota (página) principal (PROTEGIDA)
@app.route('/')
@login_required 
def ola_mundo():
    return render_template('index.html')


# 13. Rotas de Parceiro de Negócio (PN)
@app.route('/parceiro/inativar/<int:parceiro_id>', methods=['GET', 'POST'])
@login_required 
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


# 14. **** NOVAS ROTAS DE CADASTRO (Carreiras e Funcionários) ****

# **** MUDANÇA AQUI: Rota /cadastros ADICIONADA ****
@app.route('/cadastros')
@login_required
def cadastros():
    # Esta rota apenas mostra o "menu" de cadastros
    return render_template('cadastros.html')
# **** FIM DA MUDANÇA ****

@app.route('/carreiras', methods=['GET', 'POST'])
@login_required
def carreiras():
    if request.method == 'POST':
        nome_cargo = request.form['nome_cargo']
        competencias = request.form['competencias']
        
        if not nome_cargo:
            flash('O campo "Nome do Cargo" é obrigatório.', 'error')
        else:
            nova_carreira = Carreira(nome_cargo=nome_cargo, competencias=competencias)
            db.session.add(nova_carreira)
            db.session.commit()
            flash('Cargo cadastrado com sucesso!', 'success')
            return redirect(url_for('carreiras'))

    lista_de_carreiras = Carreira.query.all()
    return render_template('carreiras.html', carreiras=lista_de_carreiras)

@app.route('/funcionarios', methods=['GET', 'POST'])
@login_required 
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


# 15. Rotas de Ordem de Serviço (OS)
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
    
    # ATUALIZAÇÃO: Busca Funcionários, não Técnicos
    todos_tecnicos = Funcionario.query.all() 

    return render_template('ordens_servico.html',
                           ordens_servico=lista_de_os,
                           todos_tecnicos=todos_tecnicos,
                           filtro_estado=filtro_estado,
                           filtro_tecnico_id=filtro_tecnico_id)

@app.route('/os/editar/<int:os_id>', methods=['GET', 'POST'])
@login_required 
def editar_os(os_id):
    os_para_editar = OrdemServico.query.get_or_404(os_id)

    if request.method == 'POST':
        os_para_editar.parceiro_id = request.form['parceiro_id'] 
        os_para_editar.equipamento = request.form['equipamento']
        os_para_editar.defeito_reclamado = request.form['defeito']
        os_para_editar.acessorios = request.form['acessorios']
        os_para_editar.estado = request.form['estado']
        os_para_editar.tecnico_id = request.form['tecnico_id'] # O 'name' do HTML ainda é 'tecnico_id'

        db.session.commit()
        return redirect(url_for('ordens_servico'))
    else:
        lista_clientes = ParceiroNegocio.query.filter_by(eh_cliente=True).all()
        # ATUALIZAÇÃO: Busca Funcionários, não Técnicos
        todos_tecnicos = Funcionario.query.all() 
        return render_template('editar_os.html',
                               os=os_para_editar,
                               clientes=lista_clientes,
                               tecnicos=todos_tecnicos)

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


# 16. Rodar o servidor
if __name__ == '__main__':
    app.run(debug=True)