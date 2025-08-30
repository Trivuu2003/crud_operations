from __future__ import annotations

from fastapi import APIRouter, Depends

from .schemas import Invoice
from .security import get_current_user


router = APIRouter(prefix="/billing", tags=["billing"])


@router.get("/invoices", response_model=list[Invoice])
def list_invoices(_: str = Depends(get_current_user)):
    # Mock invoices
    return [
        {
            "id": "inv_1001",
            "date": "2024-01-15",
            "amount": 29.0,
            "status": "paid",
            "pdf_url": "https://example.com/invoices/inv_1001.pdf",
        },
        {
            "id": "inv_1002",
            "date": "2024-02-15",
            "amount": 29.0,
            "status": "paid",
            "pdf_url": "https://example.com/invoices/inv_1002.pdf",
        },
        {
            "id": "inv_1003",
            "date": "2024-03-15",
            "amount": 29.0,
            "status": "due",
            "pdf_url": "https://example.com/invoices/inv_1003.pdf",
        },
    ]


