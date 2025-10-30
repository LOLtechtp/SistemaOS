# 1. Importar as ferramentas
from flask import Flask, render_template, request, redirect, url_for, flash
from flask_sqlalchemy import SQLAlchemy
import re
import os 
from flask_migrate import Migrate
import logging 
from dotenv import load_dotenv 

# --- NOVO BLOCO: CONFIGURAÇÃO DE LOGS E AMBIENTE ---
basedir = os.path.abspath(os.path.dirname(__file__))
load_dotenv(os.path.join(basedir, '.env'))

# --- BLOCO DE LOGGING COMENTADO (PARA NÃO DAR ERRO DE PERMISSÃO) ---
# ... (Todo o bloco de logging de antes, continua comentado) ...
# ... (Linhas 16 a 27 do arquivo anterior) ...
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


# 6. CRIAR O "MOLDE" DO PARCEIRO DE NEGÓCIO (NOVO!)
class ParceiroNegocio(db.Model):
    __tablename__ = 'parceiro_negocio' # Nome da tabela no banco
    id = db.Column(db.Integer, primary_key=True)
    
    # --- Campos Principais ---
    nome = db.Column(db.String(100), nullable=False)
    telefone = db.Column(db.String(20), nullable=True) # Pode ser nulo
    cpf_cnpj = db.Column(db.String(18), nullable=True, unique=True) # CPF (11) ou CNPJ (14) + formatacao
    endereco = db.Column(db.String(200), nullable=True)
    
    # --- Campos de "Função" (Roles) ---
    eh_cliente = db.Column(db.Boolean, default=False, nullable=False)
    eh_fornecedor = db.Column(db.Boolean, default=False, nullable=False)

    # --- Campos de Controle ---
    ativo = db.Column(db.Boolean, default=True, nullable=False)
    motivo_inativacao = db.Column(db.String(200), nullable=True)
    
    # --- Relação com a OS ---
    # Este parceiro (se for cliente) tem várias ordens de serviço
    ordens_servico = db.relationship('OrdemServico', backref='parceiro', lazy=True)


# 7. CRIAR O "MOLDE" DO TECNICO (Sem mudanças)
class Tecnico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(100), nullable=False)
    ordens_servico_tecnico = db.relationship('OrdemServico', backref='tecnico', lazy=True)


# 8. CRIAR O "MOLDE" DA ORDEM DE SERVIÇO (ATUALIZADO!)
class OrdemServico(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    equipamento = db.Column(db.String(200), nullable=False)
    defeito_reclamado = db.Column(db.String(500), nullable=False)
    acessorios = db.Column(db.String(200), nullable=True)
    tecnico_id = db.Column(db.Integer, db.ForeignKey('tecnico.id'), nullable=False)
    estado = db.Column(db.String(50), nullable=False, default='Aguardando Orçamento')
    
    # --- MUDANÇA AQUI ---
    # A OS agora pertence a um 'parceiro_negocio.id'
    parceiro_id = db.Column(db.Integer, db.ForeignKey('parceiro_negocio.id'), nullable=False)
    # --- FIM DA MUDANÇA ---
    
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


# 9. Rota (página) principal (ATUALIZADA PARA PN)
@app.route('/', methods=['GET', 'POST'])
def ola_mundo():

    if request.method == 'POST':
        # --- ATUALIZADO PARA PN ---
        nome_do_parceiro = request.form['nome']
        telefone_do_parceiro = request.form['telefone']
        telefone_limpo = re.sub(r'\D', '', telefone_do_parceiro)

        if not (10 <= len(telefone_limpo) <= 11):
            flash('Telefone inválido. Digite 10 ou 11 números (com DDD).', 'error')
            return redirect(url_for('ola_mundo'))

        # Por enquanto, todo PN cadastrado na home será um Cliente
        novo_parceiro = ParceiroNegocio(
            nome=nome_do_parceiro, 
            telefone=telefone_limpo,
            eh_cliente=True # Define a "função" (role)
        )
        db.session.add(novo_parceiro)
        db.session.commit()
        # --- FIM DA MUDANÇA ---

        flash('Cliente registrado com sucesso!', 'success')
        return redirect(url_for('ola_mundo'))

    else:
        estados_finais = ['Concluído', 'Finalizado (Desistência)']

        # --- ATUALIZADO PARA PN ---
        # Busca apenas PNs que são marcados como clientes
        lista_de_parceiros = ParceiroNegocio.query.filter_by(eh_cliente=True).all()
        lista_de_os = OrdemServico.query.filter(OrdemServico.estado.notin_(estados_finais)).all()

        return render_template('index.html', parceiros=lista_de_parceiros, ordens_servico=lista_de_os)
        # --- FIM DA MUDANÇA ---


# 10. Rota para Inativar Parceiro (ATUALIZADA)
@app.route('/parceiro/inativar/<int:parceiro_id>', methods=['GET', 'POST'])
def inativar_parceiro(parceiro_id):

    parceiro_para_inativar = ParceiroNegocio.query.get_or_404(parceiro_id)

    estados_finais = ['Concluído', 'Finalizado (Desistência)']
    # Verifica se o Parceiro (como cliente) tem OS abertas
    os_abertas = OrdemServico.query.filter_by(parceiro_id=parceiro_id)\
                                  .filter(OrdemServico.estado.notin_(estados_finais))\
                                  .count()
    if os_abertas > 0:
        flash(f"ERRO: Parceiro não pode ser inativado. Existem {os_abertas} OS que não estão finalizadas.", 'error')
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
        return redirect(url_for('ola_mundo'))

    else:
        return render_template('inativar_parceiro.html', parceiro=parceiro_para_inativar)

# 11. Rota para Reativar Parceiro (ATUALIZADA)
@app.route('/parceiro/reativar/<int:parceiro_id>')
def reativar_parceiro(parceiro_id):

    parceiro_para_reativar = ParceiroNegocio.query.get_or_404(parceiro_id)

    parceiro_para_reativar.ativo = True
    parceiro_para_reativar.motivo_inativacao = None
    db.session.commit()

    flash('Parceiro reativado com sucesso.', 'success')
    return redirect(url_for('ola_mundo'))


# 12. Rota para Abrir OS (ATUALIZADA)
@app.route('/abrir_os', methods=['GET', 'POST'])
def abrir_os():

    if request.method == 'POST':
        id_do_parceiro = request.form['parceiro_id']

        parceiro_selecionado = ParceiroNegocio.query.get(id_do_parceiro)
        
        # Validação dupla: precisa ser cliente E estar ativo
        if not parceiro_selecionado.eh_cliente or not parceiro_selecionado.ativo:
            flash(f"ERRO: O PN '{parceiro_selecionado.nome}' não é um cliente ativo. Verifique o cadastro.", 'error')
            
            # Recarrega os dados para o formulário
            clientes_ativos = ParceiroNegocio.query.filter_by(eh_cliente=True, ativo=True).all()
            todos_tecnicos = Tecnico.query.all()
            return render_template('abrir_os.html',
                                   clientes=clientes_ativos,
                                   tecnicos=todos_tecnicos,
                                   dados_form=request.form)

        equip = request.form['equipamento']
        defeito = request.form['defeito']
        acessorios = request.form['acessorios']
        id_do_tecnico = request.form['tecnico_id']

        nova_os = OrdemServico(
            equipamento=equip,
            defeito_reclamado=defeito,
            acessorios=acessorios,
            tecnico_id=id_do_tecnico,
            parceiro_id=id_do_parceiro # <-- MUDANÇA AQUI
        )

        db.session.add(nova_os)
        db.session.commit()

        flash('Ordem de Serviço aberta com sucesso!', 'success')
        return redirect(url_for('ola_mundo'))

    else:
        # Busca apenas PNs que são clientes E estão ativos
        clientes_ativos = ParceiroNegocio.query.filter_by(eh_cliente=True, ativo=True).all()
        todos_tecnicos = Tecnico.query.all()

        return render_template('abrir_os.html',
                               clientes=clientes_ativos,
                               tecnicos=todos_tecnicos,
                               dados_form={})


# 13. Rota para Gerenciar Técnicos (Sem mudanças)
@app.route('/tecnicos', methods=['GET', 'POST'])
def tecnicos():
    if request.method == 'POST':
        nome_tecnico = request.form['nome']
        novo_tecnico = Tecnico(nome=nome_tecnico)
        db.session.add(novo_tecnico)
        db.session.commit()
        return redirect(url_for('tecnicos'))
    else:
        lista_de_tecnicos = Tecnico.query.all()
        return render_template('tecnicos.html', tecnicos=lista_de_tecnicos)

# 14. Rota para Apagar Técnico (Sem mudanças)
@app.route('/tecnico/apagar/<int:tecnico_id>')
def apagar_tecnico(tecnico_id):

    tecnico_para_apagar = Tecnico.query.get_or_404(tecnico_id)

    try:
        db.session.delete(tecnico_para_apagar)
        db.session.commit()
        return redirect(url_for('tecnicos'))
    except Exception as e:
        flash(f"Não foi possível apagar o técnico. Verifique se ele possui OS associadas.", "error")
        db.session.rollback()
        return redirect(url_for('tecnicos'))


# 15. Rota para Editar OS (ATUALIZADA)
@app.route('/os/editar/<int:os_id>', methods=['GET', 'POST'])
def editar_os(os_id):

    os_para_editar = OrdemServico.query.get_or_404(os_id)

    if request.method == 'POST':
        os_para_editar.parceiro_id = request.form['parceiro_id'] # <-- MUDANÇA AQUI
        os_para_editar.equipamento = request.form['equipamento']
        os_para_editar.defeito_reclamado = request.form['defeito']
        os_para_editar.acessorios = request.form['acessorios']
        os_para_editar.estado = request.form['estado']
        os_para_editar.tecnico_id = request.form['tecnico_id']

        db.session.commit()
        return redirect(url_for('ola_mundo'))

    else:
        # Busca todos os PNs que são clientes (ativos ou inativos)
        lista_clientes = ParceiroNegocio.query.filter_by(eh_cliente=True).all()
        todos_tecnicos = Tecnico.query.all()

        return render_template('editar_os.html',
                               os=os_para_editar,
                               clientes=lista_clientes,
                               tecnicos=todos_tecnicos)


# 16. Rota para Finalizar OS (Sem mudanças)
@app.route('/os/finalizar/<int:os_id>', methods=['GET', 'POST'])
def finalizar_os(os_id):

    os = OrdemServico.query.get_or_404(os_id)

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

        else: # (tipo == 'sem_reparo')
            if not obs or len(obs) < 10:
                flash('ERRO: A "Observação Final" é obrigatória (mín. 10 caracteres) para OS sem reparo.', 'error')
                return render_template('finalizar_os.html', os=os, dados_form=request.form)

            os.estado = 'Finalizado (Desistência)'
            os.valor_servico = 0
            os.observacao_final = obs

        db.session.commit()
        flash(f'OS Nº{os.id} finalizada com sucesso!', 'success')
        return redirect(url_for('ola_mundo'))

    else:
        return render_template('finalizar_os.html', os=os, dados_form={})


# 17. Rodar o servidor
if __name__ == '__main__':
    app.run(debug=True)