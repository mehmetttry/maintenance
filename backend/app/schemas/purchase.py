# app/schemas/purchase.py
from datetime import date
from typing import Optional, Literal
from decimal import Decimal, ROUND_HALF_UP, InvalidOperation

from pydantic import BaseModel, ConfigDict, field_serializer, field_validator

MONEY_PLACES = Decimal("0.01")  # 2 hane

class POCreate(BaseModel):
    SupplierID: int
    PartID: int
    Qty: int
    UnitPrice: Decimal  # <- float yerine Decimal
    ETA: Optional[date] = None

    @field_validator("Qty")
    @classmethod
    def _qty_positive(cls, v: int) -> int:
        if v <= 0:
            raise ValueError("Qty must be > 0")
        return v

    @field_validator("UnitPrice")
    @classmethod
    def _price_decimal(cls, v: Decimal) -> Decimal:
        # Sayıyı 2 haneye ROUND_HALF_UP yuvarla, > 0 doğrula
        try:
            v = (Decimal(v) if not isinstance(v, Decimal) else v).quantize(MONEY_PLACES, rounding=ROUND_HALF_UP)
        except (InvalidOperation, TypeError):
            raise ValueError("UnitPrice must be a valid decimal")
        if v <= 0:
            raise ValueError("UnitPrice must be > 0")
        return v

class PORead(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    POID: int
    SupplierID: int
    PartID: int
    Qty: int
    UnitPrice: Decimal
    PODate: date
    ETA: Optional[date] = None
    Status_s: Literal['Created', 'Ordered', 'Received', 'Canceled']

    # İstemci basit görsün diye JSON’da float döndürüyoruz (istersen string yapabiliriz)
    @field_serializer('UnitPrice')
    def _ser_price(self, v: Decimal):
        return float(v)
