# app/models/usuario.py
from flask_login import UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from app import db  # IMPORT CORRETO: importa o objeto db do pacote app


class Usuario(db.Model, UserMixin):
    __tablename__ = 'usuario'

    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(50), unique=True, nullable=False)
    password_hash = db.Column(db.String(128), nullable=False)
    email = db.Column(db.String(120))
    status = db.Column(db.String(20), default='Ativo')
    observacoes = db.Column(db.Text)
    precisa_trocar_senha = db.Column(db.Boolean, default=True)
    funcionario_id = db.Column(db.Integer, db.ForeignKey('funcionario.id'), unique=True, nullable=False)

    def set_password(self, password):
        self.password_hash = generate_password_hash(password)

    def check_password(self, password):
        return check_password_hash(self.password_hash, password)
