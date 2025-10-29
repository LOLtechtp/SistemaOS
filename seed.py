# Importa as ferramentas necessárias do nosso app
from app import app, db, Cliente, Tecnico, OrdemServico

# Este bloco garante que o código só rode quando executamos 'python seed.py'
if __name__ == '__main__':
    # 'with app.app_context()' é necessário para que o Flask saiba
    # qual banco de dados usar (lembra da configuração inteligente?)
    with app.app_context():
        
        print("Limpando dados antigos (se houver)...")
        # Apaga todas as OS, depois Técnicos, depois Clientes (respeitando as 'pontes')
        OrdemServico.query.delete()
        Tecnico.query.delete()
        Cliente.query.delete()
        db.session.commit()
        print("Dados antigos limpos.")

        print("Criando dados de exemplo...")
        
        # --- Clientes de Exemplo ---
        cliente1 = Cliente(nome="João da Silva (Exemplo)", telefone="11999998888", ativo=True)
        cliente2 = Cliente(nome="Maria Pereira (Inativa Exemplo)", telefone="21888887777", ativo=False, motivo_inativacao="Cadastro de teste inativado pelo seed.")
        
        # --- Técnico de Exemplo ---
        tecnico1 = Tecnico(nome="Carlos (Técnico Exemplo)")
        
        # Adiciona clientes e técnico à "sessão" (área de preparação)
        db.session.add_all([cliente1, cliente2, tecnico1])
        # IMPORTANTE: Faça o commit AQUI para que cliente1 e tecnico1 tenham IDs
        db.session.commit() 
        print("Clientes e Técnicos criados.")

        # --- OS de Exemplo ---
        # Note que usamos cliente1 e tecnico1 que acabaram de ser salvos
        os1 = OrdemServico(
            cliente_id=cliente1.id, 
            equipamento="Notebook Positivo",
            defeito_reclamado="Não liga, tela preta.",
            acessorios="Fonte original",
            tecnico_id=tecnico1.id,
            estado='Aguardando Orçamento' # Estado padrão
        )
        os2 = OrdemServico(
            cliente_id=cliente1.id, # Outra OS para o João
            equipamento="Celular Samsung A10",
            defeito_reclamado="Tela trincada após queda.",
            acessorios=None, # Sem acessórios
            tecnico_id=tecnico1.id,
            estado='Fila de Execução' # Um estado diferente
        )
        
        # Adiciona as OS à sessão
        db.session.add_all([os1, os2])
        # Commit final para salvar as OS
        db.session.commit()
        print("Ordens de Serviço criadas.")

        print("Banco de dados semeado com sucesso!")