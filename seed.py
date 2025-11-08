# Importa as ferramentas necessárias do nosso app
# **** MUDANÇA AQUI: Removemos 'Perfil' ****
from app import app, db, Usuario, ParceiroNegocio, Funcionario, Carreira, OrdemServico, MidiaOS

# Este bloco garante que o código só rode quando executamos 'python seed.py'
if __name__ == '__main__':
    with app.app_context():
        
        print("Limpando dados antigos (se houver)...")
        # Apaga na ordem correta para não quebrar as "pontes" (Foreign Keys)
        MidiaOS.query.delete()
        OrdemServico.query.delete()
        Usuario.query.delete()     
        Funcionario.query.delete() 
        Carreira.query.delete()    
        ParceiroNegocio.query.delete() 
        # Perfil.query.delete() # <-- **** MUDANÇA (REMOVIDO) ****
        db.session.commit()
        print("Dados antigos limpos.")

        print("Criando dados de exemplo...")

        # --- **** MUDANÇA: Ordem de criação **** ---
        
        # 1. Crie os PERFIS (REMOVIDO)
        # perfil_gerente = Perfil(nome="Gerente") ...
        # print("Perfis 'Gerente' e 'Técnico' criados.") # <-- REMOVIDO

        # 1. Crie a Carreira (Cargo)
        cargo_gerente = Carreira(
            nome_cargo="Gerente (Admin)",
            competencias="Acesso total ao sistema."
        )
        db.session.add(cargo_gerente)
        db.session.commit() # Salva o cargo para obter um ID
        print("Carreira de Gerente criada.")

        # 2. Crie o Funcionário LIGADO à Carreira
        func_vincy = Funcionario(
            nome="Vincy", # (O nome do seu funcionário)
            cargo_id=cargo_gerente.id 
        )
        db.session.add(func_vincy)
        db.session.commit() # Salva o funcionário para obter um ID
        print("Funcionário 'Vincy' criado.")

        # 3. Crie o Usuário LIGADO ao Funcionário (SEM PERFIL)
        admin_user = Usuario(
            username="VINCY",
            email="loltechtp@gmail.com", 
            status="Ativo",
            precisa_trocar_senha=False, 
            funcionario_id=func_vincy.id
            # perfil_id=perfil_gerente.id # <-- **** MUDANÇA (REMOVIDO) ****
        )
        admin_user.set_password("G^b45") # Define a sua senha
        
        db.session.add(admin_user)
        print("Usuário 'VINCY' criado.")
        
        
        # --- Parceiros de Exemplo ---
        pn1 = ParceiroNegocio(
            nome="João da Silva (Cliente Exemplo)", 
            telefone="11999998888", 
            ativo=True,
            eh_cliente=True, 
            eh_fornecedor=False,
            cpf_cnpj="11122233301",
            endereco="Rua Teste, 1"
        )
        
        # --- Técnico (Funcionário) de Exemplo ---
        cargo_tecnico = Carreira(nome_cargo="Técnico de Reparo")
        db.session.add(cargo_tecnico)
        db.session.commit()
        
        func_carlos = Funcionario(nome="Carlos (Técnico Exemplo)", cargo_id=cargo_tecnico.id)
        
        db.session.add_all([pn1, func_carlos])
        db.session.commit() 
        print("Dados de exemplo (Parceiro, Técnico) criados.")

        # --- OS de Exemplo ---
        os1 = OrdemServico(
            parceiro_id=pn1.id, 
            equipamento="Notebook Positivo",
            defeito_reclamado="Não liga, tela preta.",
            acessorios="Fonte original",
            tecnico_id=func_carlos.id, 
            estado='Aguardando Orçamento' 
        )
        
        db.session.add(os1)
        db.session.commit()
        print("OS de exemplo criada.")

        print("Banco de dados semeado com sucesso!")