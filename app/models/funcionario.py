# app/models/funcionario.py
from app import db


class Funcionario(db.Model):
    __tablename__ = 'funcionario'

    id = db.Column(db.Integer, primary_key=True)
    nome = db.Column(db.String(120), nullable=False)
    cargo = db.Column(db.String(100))
    ativo = db.Column(db.Boolean, default=True)

    # relacionamento 1-para-1 com Usuario
    usuario = db.relationship('Usuario', backref='funcionario', uselist=False)

    def __repr__(self):
        return f"<Funcionario {self.nome}>"
