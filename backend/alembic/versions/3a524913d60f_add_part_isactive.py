from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mssql

# revision identifiers, used by Alembic.
revision = '3a524913d60f'
down_revision = '839174f96b92'
branch_labels = None
depends_on = None

def upgrade():
    # güvenli ekleme: nullable + default -> veri doldur -> not null
    op.add_column('Part', sa.Column('IsActive', sa.Boolean(), nullable=True, server_default=sa.text('1')))
    op.execute("UPDATE Part SET IsActive = 1 WHERE IsActive IS NULL")
    op.alter_column('Part', 'IsActive', existing_type=mssql.BIT, nullable=False)

def downgrade():
    op.drop_column('Part', 'IsActive')
