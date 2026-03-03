"""
Almacenamiento Sistema de Control de Deliveries.
Modelo: CustomerOrder, CustomerOrderItem (inline), LotTracking (lot en ítem), OperationalIncident.
Datos en data/delivery/*.json.
"""

import json
import uuid
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple

# Grupos que requieren LOT obligatorio (Dips, Sauces/Salsas)
REQUIRES_LOT_GROUPS = ("dip", "dips", "salsa", "salsas", "sauce", "sauces")

# Motivos de diferencia (solo estos dos)
DIFFERENCE_REASONS = ("SinStock", "ProduccionNoLista")
# Asignación: Sin stock → Inventory, Producción no lista → Production
REASON_TO_ROLE = {"SinStock": "Inventory", "ProduccionNoLista": "Production"}

# Estados CO
CO_STATUS_PENDING = "Pending"
CO_STATUS_IN_PREPARATION = "InPreparation"
CO_STATUS_CLOSED = "Closed"

# Estados incidente
INCIDENT_STATUS_PENDING = "Pending"
INCIDENT_STATUS_IN_PROGRESS = "InProgress"
INCIDENT_STATUS_RESOLVED = "Resolved"

ORIGINS = ("Freezer", "Fridge", "Production")


def _delivery_dir() -> Path:
    d = Path(__file__).resolve().parent.parent / "data" / "delivery"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _read_json(path: Path, default: Any = None) -> Any:
    if not path.exists():
        return default if default is not None else []
    try:
        with open(path, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default if default is not None else []


def _write_json(path: Path, data: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False, default=str)


def _new_uuid() -> str:
    return str(uuid.uuid4())


def requires_lot_by_group(product_group: str) -> bool:
    """True si el grupo requiere LOT (Dips, Sauces)."""
    if not product_group:
        return False
    return product_group.strip().lower() in {g.lower() for g in REQUIRES_LOT_GROUPS}


# --- CustomerOrder ---

def list_customer_orders(
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
    customer: Optional[str] = None,
    status: Optional[str] = None,
) -> List[Dict[str, Any]]:
    """Lista CO con filtros opcionales. Fecha en YYYY-MM-DD."""
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if date_from and (r.get("delivery_date") or "") < date_from:
            continue
        if date_to and (r.get("delivery_date") or "") > date_to:
            continue
        if customer and (customer.strip().lower() not in (r.get("customer_name") or "").lower()):
            continue
        if status and r.get("status") != status:
            continue
        out.append(r)
    return sorted(out, key=lambda x: (x.get("delivery_date") or "", x.get("id") or ""))


def get_customer_order(co_id: str) -> Optional[Dict[str, Any]]:
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    for r in rows:
        if str(r.get("id", "")).strip() == str(co_id).strip():
            return r
    return None


def add_customer_order(
    co_number: str,
    customer_name: str,
    delivery_date: str,
    shipping_address: str = "",
    items: Optional[List[Dict[str, Any]]] = None,
) -> Dict[str, Any]:
    """Crea una CO con status Pending. items: [{ product_code, product_name, product_group, requested_qty }]."""
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    if not isinstance(rows, list):
        rows = []
    co_id = (co_number or "").strip()
    if not co_id:
        raise ValueError("CO number required")
    for r in rows:
        if str(r.get("id", "")).strip() == co_id:
            raise ValueError(f"CO {co_id} ya existe")
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    order_items = []
    for it in (items or []):
        order_items.append({
            "id": _new_uuid(),
            "product_code": (it.get("product_code") or "").strip(),
            "product_name": (it.get("product_name") or "").strip(),
            "product_group": (it.get("product_group") or "").strip(),
            "requested_qty": float(it.get("requested_qty") or 0),
            "picked_qty": None,
            "origin": None,
            "lot_number": None,
            "requires_lot": requires_lot_by_group(it.get("product_group") or ""),
            "difference_qty": None,
            "difference_reason": None,
            "status": "Pending",
        })
    co = {
        "id": co_id,
        "customer_name": (customer_name or "").strip(),
        "status": CO_STATUS_PENDING,
        "delivery_date": (delivery_date or "").strip()[:10],
        "shipping_address": (shipping_address or "").strip(),
        "created_at": now,
        "closed_at": None,
        "closed_by": None,
        "items": order_items,
    }
    rows.append(co)
    _write_json(path, rows)
    return co


def add_items_to_order(co_id: str, items: List[Dict[str, Any]]) -> Dict[str, Any]:
    """Añade líneas a una CO existente (p. ej. tras importar CSV sin ítems)."""
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    for r in rows:
        if str(r.get("id", "")).strip() == str(co_id).strip():
            existing = r.get("items") or []
            for it in items:
                existing.append({
                    "id": _new_uuid(),
                    "product_code": (it.get("product_code") or "").strip(),
                    "product_name": (it.get("product_name") or "").strip(),
                    "product_group": (it.get("product_group") or "").strip(),
                    "requested_qty": float(it.get("requested_qty") or 0),
                    "picked_qty": None,
                    "origin": None,
                    "lot_number": None,
                    "requires_lot": requires_lot_by_group(it.get("product_group") or ""),
                    "difference_qty": None,
                    "difference_reason": None,
                    "status": "Pending",
                })
            r["items"] = existing
            _write_json(path, rows)
            return r
    raise ValueError(f"CO {co_id} no encontrada")


def set_order_in_preparation(co_id: str) -> bool:
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    for r in rows:
        if str(r.get("id", "")).strip() == str(co_id).strip():
            if r.get("status") == CO_STATUS_PENDING:
                r["status"] = CO_STATUS_IN_PREPARATION
                _write_json(path, rows)
                return True
            return True
    return False


def update_order_picking(co_id: str, items: List[Dict[str, Any]], closed_by: str = "") -> Dict[str, Any]:
    """
    Actualiza ítems con picked_qty, origin, lot_number, difference_reason.
    Si closed=True, cierra la CO y genera incidentes. items debe tener id por ítem y los campos actualizados.
    """
    path = _delivery_dir() / "customer_orders.json"
    rows = _read_json(path, [])
    co = None
    for r in rows:
        if str(r.get("id", "")).strip() == str(co_id).strip():
            co = r
            break
    if not co:
        raise ValueError(f"CO {co_id} no encontrada")
    item_by_id = {str(it.get("id")): it for it in co.get("items", [])}
    for upd in items:
        iid = str(upd.get("id", ""))
        if iid not in item_by_id:
            continue
        it = item_by_id[iid]
        it["picked_qty"] = upd.get("picked_qty")
        it["origin"] = upd.get("origin") if upd.get("origin") in ORIGINS else None
        it["lot_number"] = (upd.get("lot_number") or "").strip() or None
        it["difference_reason"] = upd.get("difference_reason") if upd.get("difference_reason") in DIFFERENCE_REASONS else None
        req = float(it.get("requested_qty") or 0)
        picked = it["picked_qty"]
        if picked is not None:
            try:
                picked = float(picked)
            except (TypeError, ValueError):
                picked = None
        it["picked_qty"] = picked
        if req is not None and picked is not None:
            it["difference_qty"] = round(req - picked, 4)
        else:
            it["difference_qty"] = None
        it["status"] = "WithDifference" if (it.get("difference_qty") and it["difference_qty"] != 0) else "Completed"
    co["status"] = CO_STATUS_CLOSED
    co["closed_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    co["closed_by"] = (closed_by or "").strip()
    _write_json(path, rows)
    return co


def can_close_order(co: Dict[str, Any]) -> Tuple[bool, List[str]]:
    """Retorna (puede_cerrar, lista_errores)."""
    errors = []
    for it in co.get("items", []):
        if it.get("picked_qty") is None:
            errors.append(f"Falta cantidad tomada: {it.get('product_name') or it.get('product_code')}")
            continue
        try:
            float(it.get("picked_qty"))
        except (TypeError, ValueError):
            errors.append(f"Cantidad tomada inválida: {it.get('product_name') or it.get('product_code')}")
            continue
        if it.get("requires_lot") and not (it.get("lot_number") and str(it.get("lot_number", "")).strip()):
            errors.append(f"LOT obligatorio (Dips/Sauces): {it.get('product_name') or it.get('product_code')}")
        req = float(it.get("requested_qty") or 0)
        picked = float(it.get("picked_qty") or 0)
        if req != picked and it.get("difference_reason") not in DIFFERENCE_REASONS:
            errors.append(f"Motivo obligatorio (diferencia): {it.get('product_name') or it.get('product_code')}")
    return (len(errors) == 0, errors)


# --- OperationalIncident ---

def create_incidents_from_closed_order(co: Dict[str, Any]) -> List[Dict[str, Any]]:
    """Crea incidentes por cada ítem con diferencia. assigned_to_role según reason."""
    path = _delivery_dir() / "operational_incidents.json"
    incidents = _read_json(path, [])
    if not isinstance(incidents, list):
        incidents = []
    next_id = 1
    for inc in incidents:
        iid = inc.get("id")
        if isinstance(iid, (int, float)):
            next_id = max(next_id, int(iid) + 1)
    created = []
    co_id = co.get("id", "")
    for it in co.get("items", []):
        dq = it.get("difference_qty")
        if dq is None or dq == 0:
            continue
        reason = it.get("difference_reason") or "SinStock"
        assigned = REASON_TO_ROLE.get(reason, "Inventory")
        inc = {
            "id": next_id,
            "co_id": co_id,
            "product_code": it.get("product_code"),
            "product_name": it.get("product_name"),
            "requested_qty": it.get("requested_qty"),
            "picked_qty": it.get("picked_qty"),
            "difference_qty": dq,
            "reason": reason,
            "assigned_to_role": assigned,
            "status": INCIDENT_STATUS_PENDING,
            "created_at": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
            "resolved_at": None,
            "resolved_by": None,
        }
        incidents.append(inc)
        created.append(inc)
        next_id += 1
    if created:
        _write_json(path, incidents)
    return created


def list_incidents(
    reason: Optional[str] = None,
    status: Optional[str] = None,
    product: Optional[str] = None,
    date_from: Optional[str] = None,
    date_to: Optional[str] = None,
) -> List[Dict[str, Any]]:
    path = _delivery_dir() / "operational_incidents.json"
    rows = _read_json(path, [])
    if not isinstance(rows, list):
        return []
    out = []
    for r in rows:
        if reason and r.get("reason") != reason:
            continue
        if status and r.get("status") != status:
            continue
        if product:
            p = (product or "").strip().lower()
            if p not in (r.get("product_name") or "").lower() and p not in (r.get("product_code") or "").lower():
                continue
        created = (r.get("created_at") or "")[:10]
        if date_from and created < date_from:
            continue
        if date_to and created > date_to:
            continue
        out.append(r)
    return sorted(out, key=lambda x: (x.get("created_at") or ""), reverse=True)


def update_incident_status(
    incident_id: int,
    status: str,
    resolved_by: str = "",
) -> bool:
    path = _delivery_dir() / "operational_incidents.json"
    rows = _read_json(path, [])
    for r in rows:
        if r.get("id") == incident_id:
            r["status"] = status
            if status == INCIDENT_STATUS_RESOLVED:
                r["resolved_at"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                r["resolved_by"] = (resolved_by or "").strip()
            _write_json(path, rows)
            return True
    return False


# Compatibilidad con código que esperaba list_pending_co como lista simple
def list_pending_co() -> List[Dict[str, Any]]:
    """CO con status Pending (no iniciadas)."""
    return list_customer_orders(status=CO_STATUS_PENDING)


def is_sensitive_product(product_name: str, category: str = "") -> bool:
    """True si requiere LOT (Dips, Sauces)."""
    text = f"{product_name} {category}".lower()
    return any(s in text for s in REQUIRES_LOT_GROUPS)
