# Importa as ferramentas necessárias do nosso app
# **** MUDANÇA AQUI: Importamos 'Usuario', 'Funcionario' e 'Carreira' ****
from app import app, db, Usuario, ParceiroNegocio, Funcionario, Carreira, OrdemServico

# Este bloco garante que o código só rode quando executamos 'python seed.py'
if __name__ == '__main__':
    with app.app_context():
        
        print("Limpando dados antigos (se houver)...")
        # Apaga na ordem correta para não quebrar as "pontes" (Foreign Keys)
        OrdemServico.query.delete()
        Funcionario.query.delete() # <-- MUDANÇA
        Carreira.query.delete()    # <-- MUDANÇA
        ParceiroNegocio.query.delete() 
        Usuario.query.delete() 
        db.session.commit()
        print("Dados antigos limpos.")

        print("Criando dados de exemplo...")

        # --- Criando Usuário Admin ---
        admin_user = Usuario(username="VINCY")
        admin_user.set_password("G^b5")
        db.session.add(admin_user)
        print("Usuário Admin criado (VINCY / G^b5).")
        
        # --- **** NOVO: Criando Carreiras (Cargos) **** ---
        cargo1_tecnico = Carreira(
            nome_cargo="Técnico de Reparo",
            competencias="Reparo de notebooks, celulares, solda."
        )
        cargo2_gerente = Carreira(
            nome_cargo="Gerente de Oficina",
            competencias="Gestão de equipe, atendimento ao cliente, finanças."
        )
        db.session.add_all([cargo1_tecnico, cargo2_gerente])
        db.session.commit() # Salva as carreiras para podermos usá-las
        print("Carreiras criadas.")

        # --- **** MUDANÇA: Criando Funcionários **** ---
        func1 = Funcionario(
            nome="Carlos (Técnico Exemplo)",
            cargo_id=cargo1_tecnico.id # "Ligando" o Carlos ao cargo de Técnico
        )
        db.session.add(func1)
        print("Funcionários criados.")
        
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
        pn2 = ParceiroNegocio(
            nome="Maria Pereira (Inativa Exemplo)", 
            telefone="21888887777", 
            ativo=False, 
            motivo_inativacao="Cadastro de teste inativado pelo seed.",
            eh_cliente=True, 
            eh_fornecedor=False,
            cpf_cnpj="11122233302",
            endereco="Rua Teste, 2"
        )
        db.session.add_all([pn1, pn2])
        db.session.commit() 
        print("Parceiros criados.")

        # --- OS de Exemplo (ATUALIZADO) ---
        os1 = OrdemServico(
            parceiro_id=pn1.id, 
            equipamento="Notebook Positivo",
            defeito_reclamado="Não liga, tela preta.",
            acessorios="Fonte original",
            tecnico_id=func1.id, # <-- MUDANÇA (Agora usa o ID do func1)
            estado='Aguardando Orçamento' 
        )
        os2 = OrdemServico(
            parceiro_id=pn1.id, 
            equipamento="Celular Samsung A10",
            defeito_reclamado="Tela trincada após queda.",
            acessorios=None, 
            tecnico_id=func1.id, # <-- MUDANÇA
            estado='Fila de Execução' 
        )
        
        db.session.add_all([os1, os2])
        db.session.commit()
        print("Ordens de Serviço criadas.")

        print("Banco de dados semeado com sucesso!")