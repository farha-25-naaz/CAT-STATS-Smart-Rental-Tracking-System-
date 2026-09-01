"""Reference data the frontend needs to render dropdowns / labels:

* ``GET /sites``      — every rental site with its geofence centroid + radius
* ``GET /operators``  — distinct operator ids currently assigned to assets
"""

from typing import List

from fastapi import APIRouter

from db import supabase
from models import Site

router = APIRouter(tags=["catalog"])


@router.get("/sites", response_model=List[Site])
def list_sites():
    rows = (
        supabase.table("sites")
        .select("*")
        .order("site_id", desc=False)
        .execute()
        .data
    ) or []
    return [Site(**{k: r.get(k) for k in Site.model_fields}) for r in rows]


@router.get("/operators")
def list_operators():
    rows = (
        supabase.table("assets")
        .select("current_operator_id")
        .execute()
        .data
    ) or []
    ids = sorted({r["current_operator_id"] for r in rows if r.get("current_operator_id")})
    return {"operator_ids": ids}
