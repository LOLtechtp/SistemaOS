"""Adiciona Perfil de Permissao e tranca rotas (VERSÃO CORRIGIDA)"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision = '82d1ddf1eac2'
down_revision = 'c4456cbb6058' # <-- O "CONSERTO" ESTÁ AQUI
branch_labels = None
depends_on = None


def upgrade():
    # ### Início do "Plano" Corrigido ###
    
    # 1. Criamos a tabela Perfil
    perfil_table = op.create_table('perfil',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('nome', sa.String(length=50), nullable=False),
        sa.PrimaryKeyConstraint('id', name=op.f('pk_perfil')), # Demos um nome à chave
        sa.UniqueConstraint('nome', name=op.f('uq_perfil_nome')) # Demos um nome à restrição
    )
    
    # 2. "Mobiliamos" os perfis que precisamos (Gerente e Técnico)
    #    Isso é crucial para a Etapa 4 (para o MySQL em produção)
    op.bulk_insert(perfil_table,
        [
            {'id': 1, 'nome': 'Gerente'},
            {'id': 2, 'nome': 'Técnico'}
        ]
    )

    # 3. Adicionamos a coluna perfil_id, mas PERMITINDO NULOS (temporariamente)
    #    Este é o "segredo" para a migração em produção (MySQL)
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('perfil_id', sa.Integer(), nullable=True))
        
        # 4. Criamos a "ponte" (Foreign Key) COM NOME (consertando o ValueError)
        batch_op.create_foreign_key(
            "fk_usuario_perfil_id_perfil", # Nome da "ponte"
            'perfil', 
            ['perfil_id'], 
            ['id']
        )

    # 5. A "Mágica" de Produção: 
    #    Atualizamos TODOS os usuários que *não têm* perfil (estão nulos)
    #    e damos a eles o perfil 'Gerente' (ID 1) como padrão.
    #    (No seu caso, isso afeta o "VINCY" em produção)
    op.execute('UPDATE usuario SET perfil_id = 1 WHERE perfil_id IS NULL')

    # 6. Agora que NENHUM usuário está nulo, podemos "trancar" a coluna
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.alter_column('perfil_id',
                        existing_type=sa.Integer(),
                        nullable=False) # <-- Agora é obrigatório
    
    # ### Fim do "Plano" Corrigido ###


def downgrade():
    # ### Versão de Downgrade Corrigida ###
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        # 1. Remove a "ponte" usando o nome que demos a ela
        batch_op.drop_constraint('fk_usuario_perfil_id_perfil', type_='foreignkey')
        # 2. Remove a coluna
        batch_op.drop_column('perfil_id')

    # 3. Remove a tabela Perfil
    op.drop_table('perfil')
    # ### Fim do Downgrade ###