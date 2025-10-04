# backend/scripts/seed_demo.py
from datetime import datetime, timezone
from sqlalchemy.orm import sessionmaker
from sqlalchemy import text
from app.core.db import engine
from app.models import Machine, Part, MaintenanceRequest, WorkOrder, WarehouseTxn

SessionLocal = sessionmaker(bind=engine)

def get_or_create(session, model, defaults=None, **kwargs):
    inst = session.query(model).filter_by(**kwargs).first()
    if inst:
        return inst, False
    params = dict(kwargs)
    if defaults:
        params.update(defaults)
    inst = model(**params)
    session.add(inst)
    session.flush()
    return inst, True

def pick_technician_id(session) -> int:
    """dbo.Technician tablosundan mevcut bir TechnicianID al.
       KayÄ±t yoksa anlaÅŸÄ±lÄ±r bir hata vererek seed'i durdur."""
    tech_id = session.execute(
        text("SELECT TOP 1 TechnicianID FROM dbo.Technician ORDER BY TechnicianID ASC")
    ).scalar()
    if tech_id is None:
        raise RuntimeError(
            "Technician tablosunda kayÄ±t bulunamadÄ±. "
            "LÃ¼tfen Ã¶nce dbo.Technician'a en az bir teknisyen ekleyin (Ã¶r. TechnicianID=1), "
            "veya seed_demo.py iÃ§inde Technician ekleme mantÄ±ÄŸÄ±nÄ± ÅŸemanÄ±za gÃ¶re geniÅŸletin."
        )
    return int(tech_id)

def seed():
    session = SessionLocal()
    try:
        tech_id = pick_technician_id(session)

        # === Machines (Code zorunlu) ===
        m1, _ = get_or_create(session, Machine, defaults={"Name": "Pres HattÄ±"},   Code="PRES")
        m2, _ = get_or_create(session, Machine, defaults={"Name": "Kesim HattÄ±"},  Code="KESIM")
        m3, _ = get_or_create(session, Machine, defaults={"Name": "Montaj HattÄ±"}, Code="MONTAJ")

        # === Parts (PartCode & Unit ver) ===
        p1, _ = get_or_create(session, Part, PartCode="RUL",   defaults={"PartName": "Rulman", "Unit": "Adet"})
        p2, _ = get_or_create(session, Part, PartCode="KAYIS", defaults={"PartName": "KayÄ±ÅŸ",  "Unit": "Adet"})
        p3, _ = get_or_create(session, Part, PartCode="CIV",   defaults={"PartName": "CÄ±vata", "Unit": "Adet"})

        # === Maintenance Requests ===
        mr1 = get_or_create(session, MaintenanceRequest, MachineID=m1.MachineID, OpenedAt=datetime(2025, 2, 10, 9, tzinfo=timezone.utc))[0]
        mr2 = get_or_create(session, MaintenanceRequest, MachineID=m1.MachineID, OpenedAt=datetime(2025, 6, 5, 14, tzinfo=timezone.utc))[0]
        mr3 = get_or_create(session, MaintenanceRequest, MachineID=m1.MachineID, OpenedAt=datetime(2025, 8, 20, 8, tzinfo=timezone.utc))[0]
        mr4 = get_or_create(session, MaintenanceRequest, MachineID=m2.MachineID, OpenedAt=datetime(2025, 3, 15, 10, tzinfo=timezone.utc))[0]
        mr5 = get_or_create(session, MaintenanceRequest, MachineID=m3.MachineID, OpenedAt=datetime(2025, 5, 2, 11, tzinfo=timezone.utc))[0]
        session.flush()

        # === Work Orders (TechnicianID zorunlu) ===
        wo1 = get_or_create(session, WorkOrder, RequestID=mr1.RequestID,
                            defaults={"TechnicianID": tech_id, "OpenedAt": mr1.OpenedAt, "ClosedAt": datetime(2025, 2, 12, 17, tzinfo=timezone.utc)})[0]
        wo2 = get_or_create(session, WorkOrder, RequestID=mr2.RequestID,
                            defaults={"TechnicianID": tech_id, "OpenedAt": mr2.OpenedAt})[0]  # aÃ§Ä±k
        wo3 = get_or_create(session, WorkOrder, RequestID=mr3.RequestID,
                            defaults={"TechnicianID": tech_id, "OpenedAt": mr3.OpenedAt})[0]  # aÃ§Ä±k
        wo4 = get_or_create(session, WorkOrder, RequestID=mr4.RequestID,
                            defaults={"TechnicianID": tech_id, "OpenedAt": mr4.OpenedAt, "ClosedAt": datetime(2025, 3, 16, 16, tzinfo=timezone.utc)})[0]
        wo5 = get_or_create(session, WorkOrder, RequestID=mr5.RequestID,
                            defaults={"TechnicianID": tech_id, "OpenedAt": mr5.OpenedAt, "ClosedAt": datetime(2025, 5, 3, 15, tzinfo=timezone.utc)})[0]
        session.flush()

        # === Warehouse Transactions (IN/OUT) ===
        for t in [
            # IN
            dict(PartID=p1.PartID, TxnType="IN",  Quantity=10, Reason=REASON_PO_RECEIVE.format(100), TxnDate=datetime(2025, 1, 5, tzinfo=timezone.utc)),
            dict(PartID=p2.PartID, TxnType="IN",  Quantity=20, Reason=REASON_PO_RECEIVE.format(101), TxnDate=datetime(2025, 2, 1, tzinfo=timezone.utc)),
            dict(PartID=p3.PartID, TxnType="IN",  Quantity=50, Reason=REASON_PO_RECEIVE.format(102), TxnDate=datetime(2025, 2, 20, tzinfo=timezone.utc)),
            # OUT
            dict(PartID=p1.PartID, TxnType="OUT", Quantity=4,  Reason="WO use", WorkOrderID=wo1.WorkOrderID, TxnDate=datetime(2025, 2, 11, tzinfo=timezone.utc)),
            dict(PartID=p2.PartID, TxnType="OUT", Quantity=7,  Reason="WO use", WorkOrderID=wo2.WorkOrderID, TxnDate=datetime(2025, 6, 6, tzinfo=timezone.utc)),
            dict(PartID=p1.PartID, TxnType="OUT", Quantity=3,  Reason="WO use", WorkOrderID=wo3.WorkOrderID, TxnDate=datetime(2025, 8, 21, tzinfo=timezone.utc)),
            dict(PartID=p3.PartID, TxnType="OUT", Quantity=12, Reason="WO use", WorkOrderID=wo4.WorkOrderID, TxnDate=datetime(2025, 3, 16, tzinfo=timezone.utc)),
        ]:
            get_or_create(session, WarehouseTxn, **t)

        session.commit()
        print("Seed tamamlandÄ±. TechnicianID =", tech_id)
    except Exception as e:
        session.rollback()
        print("Seed hata:", e)
        raise
    finally:
        session.close()

if __name__ == "__main__":
    seed()


