"""normalize datetime defaults & IsActive default

Revision ID: b86dd912615f
Revises: fa1332d3b12a
Create Date: 2025-08-22 13:26:30.518572

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = 'b86dd912615f'
down_revision: Union[str, Sequence[str], None] = 'fa1332d3b12a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Var olan DEFAULT constraint'i düşür + yeni DEFAULT ekle (MSSQL)
    def drop_default(table: str, column: str):
        op.execute(sa.text(f"""
DECLARE @df sysname;
SELECT @df = df.name
FROM sys.default_constraints AS df
JOIN sys.columns AS c
  ON c.object_id = df.parent_object_id
 AND c.column_id = df.parent_column_id
WHERE df.parent_object_id = OBJECT_ID(N'dbo.{table}')
  AND c.name = N'{column}';
IF @df IS NOT NULL
    EXEC(N'ALTER TABLE dbo.{table} DROP CONSTRAINT [' + @df + N']');
"""))

    # MaintenanceRequest.OpenedAt -> SYSDATETIME()
    drop_default('MaintenanceRequest', 'OpenedAt')
    op.execute(sa.text("ALTER TABLE dbo.MaintenanceRequest ADD DEFAULT SYSDATETIME() FOR [OpenedAt]"))

    # PurchaseOrder.PODate -> CAST(SYSDATETIME() AS DATE)
    drop_default('PurchaseOrder', 'PODate')
    op.execute(sa.text("ALTER TABLE dbo.PurchaseOrder ADD DEFAULT CAST(SYSDATETIME() AS DATE) FOR [PODate]"))

    # WarehouseTxn.TxnDate -> SYSDATETIME()
    drop_default('WarehouseTxn', 'TxnDate')
    op.execute(sa.text("ALTER TABLE dbo.WarehouseTxn ADD DEFAULT SYSDATETIME() FOR [TxnDate]"))

    # WorkOrder.OpenedAt -> SYSDATETIME()
    drop_default('WorkOrder', 'OpenedAt')
    op.execute(sa.text("ALTER TABLE dbo.WorkOrder ADD DEFAULT SYSDATETIME() FOR [OpenedAt]"))

    # Machine.IsActive -> 1
    drop_default('Machine', 'IsActive')
    op.execute(sa.text("ALTER TABLE dbo.Machine ADD DEFAULT 1 FOR [IsActive]"))


def downgrade() -> None:
    # DEFAULT constraint'i düşür + önceki ifadeye döndür (MSSQL)
    def drop_default(table: str, column: str):
        op.execute(sa.text(f"""
DECLARE @df sysname;
SELECT @df = df.name
FROM sys.default_constraints AS df
JOIN sys.columns AS c
  ON c.object_id = df.parent_object_id
 AND c.column_id = df.parent_column_id
WHERE df.parent_object_id = OBJECT_ID(N'dbo.{table}')
  AND c.name = N'{column}';
IF @df IS NOT NULL
    EXEC(N'ALTER TABLE dbo.{table} DROP CONSTRAINT [' + @df + N']');
"""))

    # Machine.IsActive -> (önceki davranış yine 1)
    drop_default('Machine', 'IsActive')
    op.execute(sa.text("ALTER TABLE dbo.Machine ADD DEFAULT 1 FOR [IsActive]"))

    # WorkOrder.OpenedAt -> önceki SYSDATETIME()
    drop_default('WorkOrder', 'OpenedAt')
    op.execute(sa.text("ALTER TABLE dbo.WorkOrder ADD DEFAULT SYSDATETIME() FOR [OpenedAt]"))

    # WarehouseTxn.TxnDate -> önceki GETDATE()
    drop_default('WarehouseTxn', 'TxnDate')
    op.execute(sa.text("ALTER TABLE dbo.WarehouseTxn ADD DEFAULT GETDATE() FOR [TxnDate]"))

    # PurchaseOrder.PODate -> önceki CAST(GETDATE() AS DATE)
    drop_default('PurchaseOrder', 'PODate')
    op.execute(sa.text("ALTER TABLE dbo.PurchaseOrder ADD DEFAULT CAST(GETDATE() AS DATE) FOR [PODate]"))

    # MaintenanceRequest.OpenedAt -> önceki SYSDATETIME()
    drop_default('MaintenanceRequest', 'OpenedAt')
    op.execute(sa.text("ALTER TABLE dbo.MaintenanceRequest ADD DEFAULT SYSDATETIME() FOR [OpenedAt]"))
