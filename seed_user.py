# seed_user.py
from app import create_app, db
from app.models.usuario import Usuario
from app.models.funcionario import Funcionario

# Cria o app e o contexto
app = create_app()

with app.app_context():
    # Verifica se o usuário já existe
    existente = Usuario.query.filter_by(username="VINCY").first()

    if existente:
        print("⚠️ Usuário 'VINCY' já existe. Nenhuma alteração feita.")
    else:
        # Cria um funcionário padrão
        func = Funcionario(nome="Vincy Admin", cargo="Administrador", ativo=True)
        db.session.add(func)
        db.session.commit()

        # Cria o usuário vinculado
        user = Usuario(
            username="VINCY",
            email="admin@gestoros.com",
            funcionario_id=func.id,
            precisa_trocar_senha=False
        )
        user.set_password("Gestor123!")
        db.session.add(user)
        db.session.commit()

        print("✅ Usuário 'VINCY' criado com sucesso! Senha: Gestor123!")
