# app/forms.py
from flask_wtf import FlaskForm
from wtforms import StringField, PasswordField, SubmitField, BooleanField, SelectField
from wtforms.validators import DataRequired, Email, EqualTo, Length

# Formulário de cadastro de usuário
class UsuarioForm(FlaskForm):
    username = StringField('Usuário', validators=[DataRequired(), Length(min=3, max=50)])
    email = StringField('E-mail', validators=[Email()])
    senha = PasswordField('Senha', validators=[DataRequired(), Length(min=6)])
    confirmar = PasswordField('Confirmar Senha', validators=[DataRequired(), EqualTo('senha')])
    ativo = BooleanField('Ativo', default=True)
    submit = SubmitField('Salvar')

# Formulário de abertura de OS
class OrdemServicoForm(FlaskForm):
    cliente = StringField('Cliente', validators=[DataRequired()])
    descricao = StringField('Descrição', validators=[DataRequired(), Length(min=5, max=255)])
    tecnico = SelectField('Técnico Responsável', choices=[], validators=[DataRequired()])
    prioridade = SelectField('Prioridade', choices=[('baixa', 'Baixa'), ('media', 'Média'), ('alta', 'Alta')])
    submit = SubmitField('Abrir OS')
