"""checks: Part>=0, PO>0

Revision ID: 184bbb34e7a7
Revises: 3a524913d60f
Create Date: 2025-09-02 13:21:13.292729
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "184bbb34e7a7"
down_revision: Union[str, Sequence[str], None] = "3a524913d60f"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def _check_exists(name: str) -> bool:
    """
    pyodbc 'qmark' paramstyle kullandığı için exec_driver_sql("... :n", {...})
    HY000 hatası veriyor. Bu yüzden SA text() ile named bind kullanıyoruz.
    """
    bind = op.get_bind()
    dialect = bind.dialect.name

    if dialect == "mssql":
        row = bind.execute(
            sa.text("SELECT 1 FROM sys.check_constraints WHERE name = :n"),
            {"n": name},
        ).first()
        return bool(row)

    elif dialect in ("postgresql", "postgres"):
        row = bind.execute(
            sa.text("SELECT 1 FROM pg_constraint WHERE conname = :n"),
            {"n": name},
        ).first()
        return bool(row)

    else:
        # Diğer veritabanlarında 'var' kabul et; yoksa False döndür.
        try:
            row = bind.execute(
                sa.text(
                    "SELECT 1 FROM information_schema.check_constraints WHERE constraint_name = :n"
                ),
                {"n": name},
            ).first()
            return bool(row)
        except Exception:
            return False


def _ensure_check(table: str, name: str, condition: str) -> None:
    if not _check_exists(name):
        op.execute(sa.text(f"ALTER TABLE [{table}] ADD CONSTRAINT [{name}] CHECK ({condition})"))


def _drop_if_exists(table: str, name: str) -> None:
    if _check_exists(name):
        op.execute(sa.text(f"ALTER TABLE [{table}] DROP CONSTRAINT [{name}]"))


def upgrade() -> None:
    _ensure_check("Part", "CK_Part_MinStock_NonNeg", "MinStock >= 0")
    _ensure_check("Part", "CK_Part_CurrentStock_NonNeg", "CurrentStock >= 0")
    _ensure_check("PurchaseOrder", "CK_PO_Qty_Positive", "Qty > 0")
    _ensure_check("PurchaseOrder", "CK_PO_UnitPrice_Positive", "UnitPrice > 0")


def downgrade() -> None:
    _drop_if_exists("PurchaseOrder", "CK_PO_UnitPrice_Positive")
    _drop_if_exists("PurchaseOrder", "CK_PO_Qty_Positive")
    _drop_if_exists("Part", "CK_Part_CurrentStock_NonNeg")
    _drop_if_exists("Part", "CK_Part_MinStock_NonNeg")
