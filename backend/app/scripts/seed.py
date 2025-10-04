from app.core.db import SessionLocal
from app.models.machine import Machine
from app.models.technician import Technician
from app.models.part import Part
from app.models.supplier import Supplier
from app.models.maintenance_request import MaintenanceRequest
from app.models.workorder import WorkOrder
from app.models.warehouse_txn import WarehouseTxn
from app.models.purchase_order import PurchaseOrder

from sqlalchemy import select
from contextlib import contextmanager

# ---------- küçük yardımcılar ----------

@contextmanager
def session_scope():
    """Tek seferlik session aç/kapat (hata olursa rollback)."""
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def get_one(db, model, **by):
    """Tekil alanlara göre satır getir (yoksa None)."""
    return db.execute(select(model).filter_by(**by)).scalars().first()

def get_or_create(db, model, unique_by: dict, defaults: dict | None = None):
    """unique_by ile ara, yoksa oluştur (idempotent)."""
    inst = get_one(db, model, **unique_by)
    if inst:
        return inst, False
    data = {**unique_by, **(defaults or {})}
    inst = model(**data)
    db.add(inst)
    # çağıran commit edeceği için burada commit yok
    return inst, True

# ---------- tohum veriler (idempotent) ----------

MACHINES = [
    {"Code": "M-001", "Name": "Pres Hattı", "Location": "A-1"},
    {"Code": "M-002", "Name": "Kesim",      "Location": "B-2"},
]

TECHNICIANS = [
    {"FullName": "Ali Usta",    "SkillLevel": 8, "Phone": "05xx"},
    {"FullName": "Zeynep Usta", "SkillLevel": 9, "Phone": "05yy"},
]

PARTS = [
    {"PartCode": "P-100", "PartName": "Rulman", "Unit": "adet", "MinStock": 5, "CurrentStock": 20},
    {"PartCode": "P-200", "PartName": "Kayış",  "Unit": "adet", "MinStock": 3, "CurrentStock": 10},
]

SUPPLIERS = [
    {"Name": "Tedarik AŞ", "Phone": "0212...", "Email": "satis@tedarik.com"},
]

def run():
    with session_scope() as db:
        # 1) temel tablolar
        print(">> Seeding: Machine / Technician / Part / Supplier")

        for m in MACHINES:
            get_or_create(db, Machine, {"Code": m["Code"]}, defaults=m)

        for t in TECHNICIANS:
            get_or_create(db, Technician, {"FullName": t["FullName"]}, defaults=t)

        for p in PARTS:
            get_or_create(db, Part, {"PartCode": p["PartCode"]}, defaults=p)

        for s in SUPPLIERS:
            get_or_create(db, Supplier, {"Name": s["Name"]}, defaults=s)

    # 2) ilişkili kayıtlar (ayrı transaction bloklarında göstermek için)
    with session_scope() as db:
        print(">> Seeding: MaintenanceRequest + WorkOrder + WarehouseTxn + PurchaseOrder")

        m1 = get_one(db, Machine, Code="M-001")
        tech = get_one(db, Technician, FullName="Ali Usta")
        part = get_one(db, Part, PartCode="P-100")
        supp = get_one(db, Supplier, Name="Tedarik AŞ")

        # Bir tane örnek ticket yoksa oluştur
        mr = db.execute(select(MaintenanceRequest).filter_by(Description_s="Yağ sızıntısı")).scalars().first()
        if not mr and m1:
            mr = MaintenanceRequest(
                MachineID=m1.MachineID,
                OpenedBy="Operator1",
                Priority_s=3,
                Description_s="Yağ sızıntısı",
                Status_s="Open",
            )
            db.add(mr)
            db.flush()  # RequestID almak için

        # WorkOrder (MR varsa ve aynı notla yoksa)
        if mr and not db.execute(select(WorkOrder).filter_by(RequestID=mr.RequestID, Notes="Keçe değişimi")).scalars().first():
            wo = WorkOrder(
                RequestID=mr.RequestID,
                TechnicianID=tech.TechnicianID if tech else None,
                Notes="Keçe değişimi",
                Status_s="Open",
            )
            db.add(wo)
            db.flush()  # WorkOrderID almak için

            # Stoktan çıkış (OUT)
            if part:
                txn = WarehouseTxn(
                    PartID=part.PartID,
                    TxnType="OUT",
                    Quantity=2,
                    Reason="WO",
                    WorkOrderID=wo.WorkOrderID,
                )
                db.add(txn)

            # Min stok tetikledi varsayımıyla bir PO
            if part and supp:
                if not db.execute(
                        select(PurchaseOrder).filter_by(PartID=part.PartID, SupplierID=supp.SupplierID, Qty=10)
                ).scalars().first():
                    po = PurchaseOrder(
                        SupplierID=supp.SupplierID,
                        PartID=part.PartID,
                        Qty=10,
                        UnitPrice=120,
                        Status_s="Created",  # <-- EKLENDİ
                    )
                    db.add(po)

    print("Seed tamam.")

if __name__ == "__main__":
    run()
