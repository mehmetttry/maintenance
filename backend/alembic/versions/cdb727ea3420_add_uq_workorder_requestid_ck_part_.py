"""add UQ WorkOrder.RequestID + CK Part.CurrentStock>=0

Revision ID: cdb727ea3420
Revises: d429807daded
Create Date: 2025-08-26 11:08:42.480203

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'cdb727ea3420'
down_revision: Union[str, Sequence[str], None] = 'd429807daded'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """Upgrade schema."""
    from alembic import op

    # Güvenlik: varsa negatif stokları sıfırla (CHECK'e takılmasın)
    op.execute("UPDATE dbo.Part SET CurrentStock = 0 WHERE CurrentStock < 0;")

    # WorkOrder.RequestID için UNIQUE kısıtı
    op.create_unique_constraint(
        "UQ_WorkOrder_RequestID", "WorkOrder", ["RequestID"]
    )

    # Part.CurrentStock için negatif değerleri engelle
    op.create_check_constraint(
        "CK_Part_CurrentStock_NonNegative", "Part", "CurrentStock >= 0"
    )


def downgrade() -> None:
    """Downgrade schema."""
    from alembic import op

    # CHECK ve UNIQUE kısıtlarını geri al
    op.drop_constraint(
        "CK_Part_CurrentStock_NonNegative", "Part", type_="check"
    )
    op.drop_constraint(
        "UQ_WorkOrder_RequestID", "WorkOrder", type_="unique"
    )