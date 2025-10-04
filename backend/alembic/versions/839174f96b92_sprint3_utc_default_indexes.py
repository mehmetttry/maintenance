"""Sprint3: UTC default & indexes

Revision ID: 839174f96b92
Revises: cf902dfa60d1
Create Date: 2025-08-26 14:52:31.927218

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '839174f96b92'
down_revision: Union[str, Sequence[str], None] = 'cf902dfa60d1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    """UTC default & indexler (dbo.WorkOrder, OpenedAt/StartedAt)."""
    op.execute("""
    DECLARE @col sysname;

    -- Tarih sütununu seç: önce OpenedAt, yoksa StartedAt
    IF COL_LENGTH('dbo.WorkOrder','OpenedAt') IS NOT NULL
        SET @col = N'OpenedAt';
    ELSE IF COL_LENGTH('dbo.WorkOrder','StartedAt') IS NOT NULL
        SET @col = N'StartedAt';
    ELSE
        THROW 50002, 'WorkOrder tablosunda OpenedAt/StartedAt yok.', 1;

    -- Mevcut default constraint'i düşür
    DECLARE @df sysname;
    SELECT @df = dc.name
    FROM sys.default_constraints dc
    JOIN sys.columns c ON c.default_object_id = dc.object_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.WorkOrder')
      AND c.name = @col;

    IF @df IS NOT NULL
        EXEC('ALTER TABLE dbo.WorkOrder DROP CONSTRAINT [' + @df + ']');

    -- UTC default ekle (varsa tekrar ekleme)
    IF NOT EXISTS (
        SELECT 1 FROM sys.default_constraints
        WHERE parent_object_id = OBJECT_ID('dbo.WorkOrder')
          AND name = 'DF_WorkOrder_OpenedAt_UTC'
    )
        EXEC('ALTER TABLE dbo.WorkOrder ' +
             'ADD CONSTRAINT DF_WorkOrder_OpenedAt_UTC ' +
             'DEFAULT SYSUTCDATETIME() FOR [' + @col + ']');

    -- İndeksler
    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Active_ByTech' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        EXEC('CREATE INDEX IX_WorkOrder_Active_ByTech ON dbo.WorkOrder ' +
             '(TechnicianID, [' + @col + '] DESC) ' +
             'INCLUDE (RequestID, Status_s) ' +
             'WHERE Status_s IN (''Open'',''InProgress'')');

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Active_ByStatus' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        EXEC('CREATE INDEX IX_WorkOrder_Active_ByStatus ON dbo.WorkOrder ' +
             '(Status_s, [' + @col + '] DESC) ' +
             'INCLUDE (RequestID, TechnicianID) ' +
             'WHERE Status_s IN (''Open'',''InProgress'')');

    IF NOT EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Tech_History' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        EXEC('CREATE INDEX IX_WorkOrder_Tech_History ON dbo.WorkOrder ' +
             '(TechnicianID, [' + @col + '] DESC) ' +
             'INCLUDE (RequestID, Status_s)');
    """)




def downgrade() -> None:
    """Indexleri düşür & default'u SYSDATETIME'a çevir (dbo.WorkOrder)."""
    op.execute("""
    DECLARE @col sysname;

    IF COL_LENGTH('dbo.WorkOrder','OpenedAt') IS NOT NULL
        SET @col = N'OpenedAt';
    ELSE IF COL_LENGTH('dbo.WorkOrder','StartedAt') IS NOT NULL
        SET @col = N'StartedAt';
    ELSE
        THROW 50012, 'WorkOrder tablosunda OpenedAt/StartedAt yok.', 1;

    -- İndeksleri düşür
    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Active_ByTech' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        DROP INDEX IX_WorkOrder_Active_ByTech ON dbo.WorkOrder;

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Active_ByStatus' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        DROP INDEX IX_WorkOrder_Active_ByStatus ON dbo.WorkOrder;

    IF EXISTS (SELECT 1 FROM sys.indexes WHERE name='IX_WorkOrder_Tech_History' AND object_id=OBJECT_ID('dbo.WorkOrder'))
        DROP INDEX IX_WorkOrder_Tech_History ON dbo.WorkOrder;

    -- Mevcut default constraint'i düşür
    DECLARE @df sysname;
    SELECT @df = dc.name
    FROM sys.default_constraints dc
    JOIN sys.columns c ON c.default_object_id = dc.object_id
    WHERE dc.parent_object_id = OBJECT_ID('dbo.WorkOrder')
      AND c.name = @col;

    IF @df IS NOT NULL
        EXEC('ALTER TABLE dbo.WorkOrder DROP CONSTRAINT [' + @df + ']');

    -- Yerel saat default'u geri ekle
    IF NOT EXISTS (
        SELECT 1 FROM sys.default_constraints
        WHERE parent_object_id = OBJECT_ID('dbo.WorkOrder')
          AND name = 'DF_WorkOrder_OpenedAt_Local'
    )
        EXEC('ALTER TABLE dbo.WorkOrder ' +
             'ADD CONSTRAINT DF_WorkOrder_OpenedAt_Local ' +
             'DEFAULT SYSDATETIME() FOR [' + @col + ']');
    """)


