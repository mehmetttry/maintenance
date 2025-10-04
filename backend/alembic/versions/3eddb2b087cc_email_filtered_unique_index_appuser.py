"""email filtered unique index (AppUser)

Revision ID: 3eddb2b087cc
Revises: cc9ab62e3375
Create Date: 2025-08-26 11:44:14.411994

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '3eddb2b087cc'
down_revision: Union[str, Sequence[str], None] = 'cc9ab62e3375'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None



def upgrade() -> None:
    # Varsayımsal eski unique'leri nazikçe kaldır (adı farklı olabilir)
    op.execute("""
    IF EXISTS (SELECT 1 FROM sys.key_constraints WHERE [name] = 'UQ__AppUser__Email')
        ALTER TABLE dbo.AppUser DROP CONSTRAINT UQ__AppUser__Email;
    """)
    op.execute("""
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE [name] = 'UQ_AppUser_Email' AND object_id = OBJECT_ID('dbo.AppUser'))
        DROP INDEX UQ_AppUser_Email ON dbo.AppUser;
    """)


    op.execute("""
    IF NOT EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE [name] = 'UX_AppUser_Email_NotNull'
          AND object_id = OBJECT_ID('dbo.AppUser')
    )
        CREATE UNIQUE INDEX UX_AppUser_Email_NotNull
        ON dbo.AppUser(Email)
        WHERE Email IS NOT NULL;
    """)

def downgrade() -> None:
    op.execute("""
    IF EXISTS (
        SELECT 1 FROM sys.indexes
        WHERE [name] = 'UX_AppUser_Email_NotNull'
          AND object_id = OBJECT_ID('dbo.AppUser')
    )
        DROP INDEX UX_AppUser_Email_NotNull ON dbo.AppUser;
    """)
