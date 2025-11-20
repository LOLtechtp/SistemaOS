from app import db, Usuario, Perfil

def test_create_user(app):
    with app.app_context():
        # garante que a tabela existe
        db.create_all()

        perfil = Perfil(nome="Gerente")
        db.session.add(perfil)
        db.session.commit()

        encontrado = Perfil.query.filter_by(nome="Gerente").first()
        assert encontrado is not None
