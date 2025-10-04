"""ensure CK Part.CurrentStock>=0 (manual)

Revision ID: cc9ab62e3375
Revises: 18152ba27da7
Create Date: 2025-08-26 11:20:37.586501

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cc9ab62e3375'
down_revision: Union[str, Sequence[str], None] = '18152ba27da7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


from alembic import op

def upgrade() -> None:
    # CHECK yoksa ekle (önce negatifleri düzelt)
    op.execute("""
IF NOT EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Part_CurrentStock_NonNegative'
)
BEGIN
    UPDATE dbo.Part SET CurrentStock = 0 WHERE CurrentStock < 0;
    ALTER TABLE dbo.Part WITH CHECK
    ADD CONSTRAINT CK_Part_CurrentStock_NonNegative CHECK (CurrentStock >= 0);
END
""")

def downgrade() -> None:
    op.execute("""
IF EXISTS (
    SELECT 1 FROM sys.check_constraints WHERE name = 'CK_Part_CurrentStock_NonNegative'
)
BEGIN
    ALTER TABLE dbo.Part DROP CONSTRAINT CK_Part_CurrentStock_NonNegative;
END
""")