# backend/app/core/api.py
from __future__ import annotations
from typing import Any, Dict, Optional, Sequence
from fastapi.responses import JSONResponse, RedirectResponse

# Tüm JSON cevaplarda UTF-8 charset
class UTF8JSONResponse(JSONResponse):
    media_type = "application/json; charset=utf-8"

def list_meta(items: Optional[Sequence[Any]] = None, extra: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
    meta: Dict[str, Any] = {}
    if items is not None:
        try:
            meta["count"] = len(items)
        except Exception:
            pass
    if extra:
        meta.update(extra)
    return meta

def ok(data: Any = True, meta: Optional[Dict[str, Any]] = None, status_code: int = 200):
    payload: Dict[str, Any] = {"ok": True, "data": data}
    if meta:
        payload["meta"] = meta
    return UTF8JSONResponse(content=payload, status_code=status_code)

def fail(error: str, status_code: int = 400, meta: Optional[Dict[str, Any]] = None):
    payload: Dict[str, Any] = {"ok": False, "error": error}
    if meta:
        payload["meta"] = meta
    return UTF8JSONResponse(content=payload, status_code=status_code)

def redirect_permanent(url: str):
    return RedirectResponse(url=url, status_code=308)
