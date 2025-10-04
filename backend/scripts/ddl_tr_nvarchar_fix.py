# backend/scripts/ddl_tr_nvarchar_fix.py
from sqlalchemy import text
from sqlalchemy.orm import sessionmaker
from app.core.db import engine
from app.models import Machine, Part

SessionLocal = sessionmaker(bind=engine)

DDL_CMDS = [
    # Machine.Name -> NVARCHAR(255) NOT NULL
    """
    IF EXISTS (
      SELECT 1 FROM sys.columns
      WHERE object_id = OBJECT_ID('dbo.Machine')
        AND name = 'Name'
        AND system_type_id <> 231 -- 231 = NVARCHAR
    )
    BEGIN
      ALTER TABLE dbo.Machine ALTER COLUMN [Name] NVARCHAR(255) NOT NULL;
    END
    """,
    # Machine.Location -> NVARCHAR(255) NULL (varsa)
    """
    IF EXISTS (
      SELECT 1 FROM sys.columns
      WHERE object_id = OBJECT_ID('dbo.Machine')
        AND name = 'Location'
        AND system_type_id <> 231
    )
    BEGIN
      ALTER TABLE dbo.Machine ALTER COLUMN [Location] NVARCHAR(255) NULL;
    END
    """,
    # Part.PartName -> NVARCHAR(255) NOT NULL
    """
    IF EXISTS (
      SELECT 1 FROM sys.columns
      WHERE object_id = OBJECT_ID('dbo.Part')
        AND name = 'PartName'
        AND system_type_id <> 231
    )
    BEGIN
      ALTER TABLE dbo.Part ALTER COLUMN [PartName] NVARCHAR(255) NOT NULL;
    END
    """,
    # WarehouseTxn.Reason -> NVARCHAR(255) NULL (varsa)
    """
    IF EXISTS (
      SELECT 1 FROM sys.columns
      WHERE object_id = OBJECT_ID('dbo.WarehouseTxn')
        AND name = 'Reason'
        AND system_type_id <> 231
    )
    BEGIN
      ALTER TABLE dbo.WarehouseTxn ALTER COLUMN [Reason] NVARCHAR(255) NULL;
    END
    """,
    # WorkOrder.Notes -> NVARCHAR(MAX) NULL (varsa)
    """
    IF EXISTS (
      SELECT 1 FROM sys.columns
      WHERE object_id = OBJECT_ID('dbo.WorkOrder')
        AND name = 'Notes'
        AND system_type_id <> 231
    )
    BEGIN
      ALTER TABLE dbo.WorkOrder ALTER COLUMN [Notes] NVARCHAR(MAX) NULL;
    END
    """,
]

def run():
    with engine.begin() as conn:
        for sql in DDL_CMDS:
            conn.execute(text(sql))

    # Kodlara göre adları düzgün TR karakterlerle güncelle
    s = SessionLocal()
    try:
        code_to_name = {
            "PRES":   "Pres Hattı",
            "KESIM":  "Kesim Hattı",
            "MONTAJ": "Montaj Hattı",
        }
        for code, name in code_to_name.items():
            m = s.query(Machine).filter(Machine.Code == code).first()
            if m and m.Name != name:
                m.Name = name

        part_to_name = {
            "RUL":   "Rulman",
            "KAYIS": "Kayış",
            "CIV":   "Cıvata",
        }
        for pcode, pname in part_to_name.items():
            p = s.query(Part).filter(Part.PartCode == pcode).first()
            if p and p.PartName != pname:
                p.PartName = pname

        s.commit()
        print("NVARCHAR geçişi ve değer güncelleme tamam.")
    finally:
        s.close()

if __name__ == "__main__":
    run()
