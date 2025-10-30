# Importa as ferramentas necessárias do nosso app
# ATENÇÃO: Importamos 'ParceiroNegocio' no lugar de 'Cliente'
from app import app, db, ParceiroNegocio, Tecnico, OrdemServico

# Este bloco garante que o código só rode quando executamos 'python seed.py'
if __name__ == '__main__':
    # 'with app.app_context()' é necessário para que o Flask saiba
    # qual banco de dados usar (lembra da configuração inteligente?)
    with app.app_context():
        
        print("Limpando dados antigos (se houver)...")
        # Apaga todas as OS, depois Técnicos, depois Parceiros (respeitando as 'pontes')
        OrdemServico.query.delete()
        Tecnico.query.delete()
        ParceiroNegocio.query.delete() # <-- MUDANÇA AQUI
        db.session.commit()
        print("Dados antigos limpos.")

        print("Criando dados de exemplo...")
        
        # --- Parceiros de Exemplo (NOVO) ---
        pn1 = ParceiroNegocio(
            nome="João da Silva (Cliente Exemplo)", 
            telefone="11999998888", 
            ativo=True,
            eh_cliente=True, # <-- Define a "Função" (Role)
            eh_fornecedor=False
        )
        pn2 = ParceiroNegocio(
            nome="Maria Pereira (Inativa Exemplo)", 
            telefone="21888887777", 
            ativo=False, 
            motivo_inativacao="Cadastro de teste inativado pelo seed.",
            eh_cliente=True, # <-- Define a "Função" (Role)
            eh_fornecedor=False
        )
        pn3 = ParceiroNegocio(
            nome="Fornecedor de Peças XYZ (Fornecedor Exemplo)", 
            telefone="41777776666", 
            ativo=True,
            eh_cliente=False,
            eh_fornecedor=True # <-- Define a "Função" (Role)
        )
        
        # --- Técnico de Exemplo (Sem mudança) ---
        tecnico1 = Tecnico(nome="Carlos (Técnico Exemplo)")
        
        # Adiciona PNs e técnico à "sessão" (área de preparação)
        db.session.add_all([pn1, pn2, pn3, tecnico1])
        # IMPORTANTE: Faça o commit AQUI para que pn1 e tecnico1 tenham IDs
        db.session.commit() 
        print("Parceiros e Técnicos criados.")

        # --- OS de Exemplo (ATUALIZADO) ---
        # Note que usamos pn1 (o cliente) e tecnico1
        os1 = OrdemServico(
            parceiro_id=pn1.id, # <-- MUDANÇA AQUI
            equipamento="Notebook Positivo",
            defeito_reclamado="Não liga, tela preta.",
            acessorios="Fonte original",
            tecnico_id=tecnico1.id,
            estado='Aguardando Orçamento' # Estado padrão
        )
        os2 = OrdemServico(
            parceiro_id=pn1.id, # <-- MUDANÇA AQUI (Outra OS para o João)
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