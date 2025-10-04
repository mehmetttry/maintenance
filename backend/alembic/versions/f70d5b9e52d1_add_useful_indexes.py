"""add useful indexes

Revision ID: f70d5b9e52d1
Revises: 184bbb34e7a7
Create Date: 2025-09-03 14:24:23.795233

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'f70d5b9e52d1'
down_revision: Union[str, Sequence[str], None] = '184bbb34e7a7'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade():
    from alembic import op

    # PurchaseOrder indeksleri
    op.create_index("IX_PurchaseOrder_Status",      "PurchaseOrder", ["Status_s"], unique=False)
    op.create_index("IX_PurchaseOrder_SupplierID",  "PurchaseOrder", ["SupplierID"], unique=False)
    op.create_index("IX_PurchaseOrder_PartID",      "PurchaseOrder", ["PartID"], unique=False)
    op.create_index("IX_PurchaseOrder_PODate",      "PurchaseOrder", ["PODate"], unique=False)
    op.create_index("IX_PurchaseOrder_Status_PODate","PurchaseOrder", ["Status_s", "PODate"], unique=False)

    # WarehouseTxn indeksleri
    op.create_index("IX_WarehouseTxn_PartID",       "WarehouseTxn", ["PartID"], unique=False)


def downgrade():
    from alembic import op

    # WarehouseTxn indekslerini kaldır
    op.drop_index("IX_WarehouseTxn_PartID", table_name="WarehouseTxn")

    # PurchaseOrder indekslerini kaldır
    op.drop_index("IX_PurchaseOrder_Status_PODate", table_name="PurchaseOrder")
    op.drop_index("IX_PurchaseOrder_PODate",        table_name="PurchaseOrder")
    op.drop_index("IX_PurchaseOrder_PartID",        table_name="PurchaseOrder")
    op.drop_index("IX_PurchaseOrder_SupplierID",    table_name="PurchaseOrder")
    op.drop_index("IX_PurchaseOrder_Status",        table_name="PurchaseOrder")
