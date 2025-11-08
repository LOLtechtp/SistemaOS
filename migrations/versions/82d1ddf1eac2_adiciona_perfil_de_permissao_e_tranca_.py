"""Adiciona Perfil de Permissao e tranca rotas (VERSÃO CORRIGIDA)"""
from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
# (O "Conserto" do "Paradoxo")
revision = '82d1ddf1eac2'
down_revision = '3e76d2b16f61'
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
    op.bulk_insert(perfil_table,
        [
            {'id': 1, 'nome': 'Gerente'},
            {'id': 2, 'nome': 'Técnico'}
        ]
    )

    # 3. Adicionamos a coluna perfil_id, mas PERMITINDO NULOS (temporariamente)
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.add_column(sa.Column('perfil_id', sa.Integer(), nullable=True))
        
    # 4. Criamos a "ponte" (Foreign Key)
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        batch_op.create_foreign_key(
            "fk_usuario_perfil_id_perfil", # Nome da "ponte"
            'perfil', 
            ['perfil_id'], 
            ['id']
        )

    # 5. A "Mágica" de Produção: 
    #    Atualizamos TODOS os usuários que *não têm* perfil (estão nulos)
    op.execute('UPDATE usuario SET perfil_id = 1 WHERE perfil_id IS NULL')

    # 6. "O CONSERTO" (Separamos o "ALTER COLUMN" em 3 passos):
    with op.batch_alter_table('usuario', schema=None) as batch_op:
        # 6a. "Demolir" (DROP) a "ponte" (FK)
        batch_op.drop_constraint('fk_usuario_perfil_id_perfil', type_='foreignkey')
        
        # 6b. "Trancar" (ALTER) a "coluna" (Column) para NOT NULL
        batch_op.alter_column('perfil_id',
                        existing_type=sa.Integer(),
                        nullable=False)
                        
        # 6c. "Re-edificar" (RE-ADD) a "ponte" (FK)
        batch_op.create_foreign_key(
            "fk_usuario_perfil_id_perfil", # O mesmo nome
            'perfil', 
            ['perfil_id'], 
            ['id']
        )
    
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