# backend/app/domain/constants.py

"""
Uygulama genelinde depo işlem "reason" metinlerinin tek kaynağı.
"""

from typing import Final

# Satın alma emri receive işlemi için standart reason
REASON_PO_RECEIVE: Final[str] = "PO Receive #{}"
