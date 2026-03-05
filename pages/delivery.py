"""
Sistema de Control de Deliveries – Flujo según especificación.
Pantalla 1: Lista CO pendientes (filtros, agrupación, estados visuales).
Pantalla 2: Picking (encabezado, cantidad tomada, origen, LOT, motivo si diferencia, Cerrar Orden).
Pantalla 3: Incidentes operativos (filtros, asignado, estado).
"""

import streamlit as st
import sys
import os
import csv
import io
import re
import pandas as pd
from datetime import datetime
from typing import Optional

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.delivery_storage import (
    list_customer_orders,
    get_customer_order,
    add_customer_order,
    add_items_to_order,
    set_order_in_preparation,
    update_order_picking,
    can_close_order,
    create_incidents_from_closed_order,
    list_incidents,
    update_incident_status,
    requires_lot_by_group,
    CO_STATUS_PENDING,
    CO_STATUS_IN_PREPARATION,
    CO_STATUS_CLOSED,
    DIFFERENCE_REASONS,
    INCIDENT_STATUS_PENDING,
    INCIDENT_STATUS_IN_PROGRESS,
    INCIDENT_STATUS_RESOLVED,
    ORIGINS,
)
from shared.delivery_email import send_co_difference_alert, send_delivery_alert, is_email_configured
from shared.api_manager import APIManager


def _location_from_item_detail(detail: Optional[dict]) -> str:
    """Extrae la ubicación desde la respuesta de get_item_details (MRPeasy)."""
    if not detail or not isinstance(detail, dict):
        return ""
    loc = (
        detail.get("default_storage_location")
        or detail.get("storage_location")
        or detail.get("default_storage_location_name")
        or detail.get("storage_location_name")
        or detail.get("location")
        or detail.get("warehouse")
        or ""
    )
    if isinstance(loc, dict):
        loc = loc.get("name") or loc.get("title") or loc.get("code") or ""
    return (str(loc).strip() or "") if loc else ""


try:
    from config import secrets
except Exception:
    secrets = {}

st.set_page_config(
    page_title="Sistema de Control de Deliveries",
    page_icon="🚚",
    layout="wide",
)

# CSS: estados visuales Rojo / Amarillo / Verde
st.markdown("""
<style>
.main { background-color: #f5f7f9; }
.delivery-header { padding: 16px 0; margin-bottom: 24px; border-bottom: 2px solid #1E3A8A; }
.delivery-header h1 { color: #1E3A8A; font-size: 28px; font-weight: 700; }
.delivery-header p { color: #4B5563; font-size: 14px; }
.status-pending { background-color: #FEE2E2; color: #B91C1C; padding: 4px 8px; border-radius: 4px; }
.status-preparation { background-color: #FEF3C7; color: #B45309; padding: 4px 8px; border-radius: 4px; }
.status-closed { background-color: #D1FAE5; color: #047858; padding: 4px 8px; border-radius: 4px; }
.diff-block { background-color: #FEF3C7; border-left: 4px solid #B45309; padding: 10px; margin: 8px 0; border-radius: 4px; }
/* Botón CO grande (el que sigue a .co-card en el flujo) */
.co-card + div .stButton > button,
.co-card ~ div .stButton > button { font-size: 1.25rem; font-weight: 600; padding: 14px 28px; border-radius: 8px; width: 100%; min-height: 52px; }
.co-button-fake { font-size: 1.25rem; font-weight: 600; padding: 14px 28px; border-radius: 8px; background: #E5E7EB; color: #6B7280; text-align: center; margin: 8px 0; }
</style>
""", unsafe_allow_html=True)

st.markdown('<div class="delivery-header">', unsafe_allow_html=True)
st.markdown("# 🚚 Sistema de Control de Deliveries")
st.markdown("Flujo: Visualizar CO pendientes → Seleccionar CO → Picking (cantidad, origen, LOT) → Cerrar orden. Diferencias generan incidentes y email.")
st.markdown('</div>', unsafe_allow_html=True)

with st.expander("📋 Por qué este sistema / Alcance MVP", expanded=False):
    st.markdown("""
    **Problemas del proceso manual:** Pérdida de control de cantidades, faltantes sin explicación,
    falta de trazabilidad LOT, desconexión delivery/producción/inventario, imposibilidad de medir errores.

    **MVP incluye:** Vista CO pendientes, pantalla picking con validaciones, control diferencias con motivo obligatorio
    (Solo: Sin stock | Producción no lista), LOT obligatorio Dips/Sauces, incidentes automáticos, email, gestión incidentes.

    **No incluye (fase futura):** Integración bidireccional MRPeasy, escaneo códigos de barras,
    automatización creación CO, dashboard analítico.
    """)

# Estado
if "selected_co_id" not in st.session_state:
    st.session_state.selected_co_id = None
if "delivery_tab_radio" not in st.session_state:
    st.session_state.delivery_tab_radio = "1. Lista CO pendientes"
# Si el usuario pulsó "Seleccionar" en una CO, pasar a Picking en el próximo run (antes de crear el radio)
if st.session_state.pop("goto_picking", None):
    st.session_state.delivery_tab_radio = "2. Picking"
# Si el usuario pulsó "Volver" en Picking, regresar a la lista de CO
if st.session_state.pop("goto_list", None):
    st.session_state.delivery_tab_radio = "1. Lista CO pendientes"

DELIVERY_TABS = ["1. Lista CO pendientes", "2. Picking", "3. Incidentes operativos"]
tab_choice = st.radio("", DELIVERY_TABS, key="delivery_tab_radio", horizontal=True, label_visibility="collapsed")

def _parse_delivery_date(s: str) -> str:
    """Convierte MM/DD/YYYY o YYYY-MM-DD a YYYY-MM-DD."""
    if not s or not str(s).strip():
        return ""
    s = str(s).strip().strip('"')
    try:
        dt = datetime.strptime(s, "%m/%d/%Y")
        return dt.strftime("%Y-%m-%d")
    except ValueError:
        try:
            dt = datetime.strptime(s, "%Y-%m-%d")
            return dt.strftime("%Y-%m-%d")
        except ValueError:
            return s[:10] if len(s) >= 10 else s


def _normalize_delivery_date(value) -> str:
    """
    Convierte fecha de la API o almacenada a YYYY-MM-DD.
    Acepta: Unix timestamp (int/float), string numérico (timestamp), YYYY-MM-DD o MM/DD/YYYY.
    """
    if value is None:
        return ""
    if isinstance(value, (int, float)):
        try:
            if 1e9 <= value <= 2e9:
                return datetime.fromtimestamp(int(value)).strftime("%Y-%m-%d")
            if value > 2e9:
                return datetime.fromtimestamp(int(value) / 1000).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            pass
        return ""
    s = str(value).strip()
    if s.isdigit():
        try:
            ts = int(s)
            if 1e9 <= ts <= 2e9:
                return datetime.fromtimestamp(ts).strftime("%Y-%m-%d")
            if ts > 2e9:
                return datetime.fromtimestamp(ts / 1000).strftime("%Y-%m-%d")
        except (OSError, ValueError):
            pass
    return _parse_delivery_date(s)

def _import_customer_orders_csv(uploaded_file) -> tuple:
    """Importa CO desde CSV (columnas: Number, Customer name, Delivery date, Address). Devuelve (importadas, omitidas, errores)."""
    imported, skipped, errors = 0, 0, []
    try:
        content = uploaded_file.read()
        if isinstance(content, bytes):
            content = content.decode("utf-8", errors="replace")
        reader = csv.DictReader(io.StringIO(content))
        rows = list(reader)
    except Exception as e:
        return 0, 0, [str(e)]
    if not rows:
        return 0, 0, ["El archivo no tiene filas de datos."]
    for i, row in enumerate(rows):
        # Aceptar columnas con o sin comillas en el nombre
        number = (row.get("Number") or row.get("number") or "").strip().strip('"')
        customer = (row.get("Customer name") or row.get("customer_name") or "").strip().strip('"')
        delivery = (row.get("Delivery date") or row.get("delivery_date") or "").strip().strip('"')
        address = (row.get("Address") or row.get("address") or "").strip().strip('"')
        if "\n" in address:
            address = " ".join(l.strip() for l in address.splitlines())
        if not number:
            errors.append(f"Fila {i+2}: falta número de CO.")
            continue
        delivery_ymd = _parse_delivery_date(delivery)
        if not delivery_ymd and delivery:
            errors.append(f"Fila {i+2} ({number}): fecha no válida '{delivery}'.")
        try:
            add_customer_order(
                co_number=number,
                customer_name=customer or "Sin nombre",
                delivery_date=delivery_ymd or datetime.now().strftime("%Y-%m-%d"),
                shipping_address=address,
                items=[],
            )
            imported += 1
        except ValueError as e:
            if "ya existe" in str(e).lower():
                skipped += 1
            else:
                errors.append(f"Fila {i+2} ({number}): {e}")
    return imported, skipped, errors


def _resolve_fava_vendor_id(api: "APIManager") -> Optional[int]:
    """Obtiene el vendor_id de 'Fava' desde MRPeasy (para filtrar DropShip Vendor)."""
    try:
        vendors = api.fetch_vendors() or []
        for v in vendors:
            name = (v.get("name") or v.get("title") or "").strip()
            code = (v.get("code") or "").strip()
            vid = v.get("vendor_id") or v.get("id")
            if vid is not None and ("fava" in name.lower() or "fava" in code.lower()):
                return int(vid)
    except Exception:
        pass
    return None


def _order_is_dropship_fava(o: dict, fava_vendor_id: Optional[int]) -> bool:
    """True si la CO tiene DropShip Vendor = Fava. Revisa vendor/dropship y también custom_* (MRPeasy a veces usa custom fields)."""
    def value_matches_fava(val) -> bool:
        if val is None:
            return False
        if isinstance(val, (int, float)):
            return fava_vendor_id is not None and int(val) == fava_vendor_id
        if isinstance(val, dict):
            vid = val.get("vendor_id") or val.get("id")
            if vid is not None and fava_vendor_id is not None and int(vid) == fava_vendor_id:
                return True
            for k, v in val.items():
                if isinstance(v, str) and "fava" in v.lower():
                    return True
            return False
        s = str(val).strip().lower()
        if not s:
            return False
        if "fava" in s:
            return True
        if fava_vendor_id is not None and s == str(fava_vendor_id):
            return True
        return False

    for key, value in o.items():
        k = str(key).lower()
        # Campos explícitos de vendor/dropship
        if "vendor" in k or "dropship" in k or "ship_vendor" in k or "ship" in k and "drop" in k:
            if value_matches_fava(value):
                return True
            continue
        # MRPeasy suele usar custom_12345 para campos como "DropShip Vendor"
        if k.startswith("custom_") and value is not None:
            if value_matches_fava(value):
                return True
            # Valor string que sea exactamente "Fava" o empiece por "Fava"
            s = str(value).strip().lower()
            if s == "fava" or (len(s) < 60 and s.startswith("fava")):
                return True

    # Último recurso: buscar en todo el objeto cualquier string "Fava" en campos que parezcan etiquetas
    for key, value in o.items():
        if not isinstance(value, str) or len(value) > 80:
            continue
        k = str(key).lower()
        if "vendor" in k or "dropship" in k or "custom" in k or "ship" in k or "drop" in k:
            if "fava" in value.lower():
                return True
    return False


def _order_is_product_status_not_booked(o: dict) -> bool:
    """True si la CO tiene Product status = Not booked (part_status 10 en MRPeasy)."""
    raw = (
        o.get("part_status")
        or o.get("product_status")
        or o.get("product_status_id")
        or o.get("item_status")
    )
    if raw is None:
        return False
    if raw in (10, "10"):
        return True
    if isinstance(raw, str) and "not booked" in raw.lower():
        return True
    return False


def _sync_pending_from_mrpeasy():
    """
    Trae Customer Orders desde MRPeasy: Status = Confirmed, DropShip Vendor = Fava,
    Product status = Not booked, y fecha delivery ≥ marzo.
    Devuelve (creadas, ya_existian, errores, total_api, total_filtradas, primer_co_dict).
    """
    created, existed, errors = 0, 0, []
    total_api, total_filtradas = 0, 0
    first_order = None
    try:
        api = APIManager()
    except Exception as e:
        return 0, 0, [f"No se pudo inicializar APIManager (MRPeasy): {e}"], 0, 0, None
    try:
        raw = api.fetch_customer_orders()
    except Exception as e:
        return 0, 0, [f"Error consultando customer-orders en MRPeasy: {e}"], 0, 0, None
    if not raw:
        return 0, 0, ["MRPeasy no devolvió customer orders (o la lista está vacía)."], 0, 0, None

    total_api = len(raw)
    first_order = raw[0] if raw else None

    fava_vendor_id = _resolve_fava_vendor_id(api)

    # Solo órdenes con fecha de entrega desde marzo (inclusive) del año actual
    march_start = f"{datetime.now().year}-03-01"

    # MRPeasy customer order status: 20 = Waiting for confirmation, 30 = Confirmed
    CONFIRMED_STATUS_CODES = {30, "30"}

    for o in raw:
        status_raw = (
            o.get("status")
            or o.get("status_id")
            or o.get("status_text")
            or o.get("state")
            or o.get("order_status")
        )
        is_confirmed = False
        if status_raw is not None:
            if status_raw in CONFIRMED_STATUS_CODES or (isinstance(status_raw, int) and status_raw == 30):
                is_confirmed = True
            elif isinstance(status_raw, str) and "confirm" in status_raw.lower() and "waiting" not in status_raw.lower():
                is_confirmed = True
        if not is_confirmed:
            continue

        if not _order_is_dropship_fava(o, fava_vendor_id):
            continue

        if not _order_is_product_status_not_booked(o):
            continue

        co_number = (o.get("number") or o.get("code") or "").strip()
        if not co_number:
            continue

        raw_delivery = o.get("delivery_date") or o.get("delivery_time") or o.get("created")
        delivery_ymd = _normalize_delivery_date(raw_delivery) or datetime.now().strftime("%Y-%m-%d")
        if delivery_ymd < march_start:
            continue

        total_filtradas += 1

        if get_customer_order(co_number):
            existed += 1
            continue

        customer_name = o.get("customer_name") or o.get("customer") or ""
        if isinstance(customer_name, dict):
            customer_name = customer_name.get("name") or customer_name.get("customer_name") or ""
        customer_name = str(customer_name).strip()

        address = o.get("address") or o.get("shipping_address") or ""
        if isinstance(address, dict):
            address = ", ".join(str(v).strip() for v in address.values() if v)
        else:
            address = str(address).strip()

        # Extraer líneas/productos de la CO si la API los devuelve
        raw_lines = o.get("products") or o.get("order_lines") or o.get("items") or o.get("lines") or []
        items_for_co = []
        for line in raw_lines if isinstance(raw_lines, list) else []:
            if not isinstance(line, dict):
                continue
            code = (line.get("product_code") or line.get("item_code") or line.get("code") or "").strip()
            name = (line.get("product_name") or line.get("title") or line.get("name") or "").strip()
            qty = line.get("quantity") or line.get("requested_quantity") or line.get("qty") or line.get("ordered_quantity") or 0
            try:
                qty = float(qty)
            except (TypeError, ValueError):
                qty = 0
            group = (line.get("product_group") or line.get("group") or line.get("group_name") or "").strip()
            if code or name:
                items_for_co.append({"product_code": code or name[:20], "product_name": name or code, "product_group": group, "requested_qty": qty})

        try:
            add_customer_order(
                co_number=co_number,
                customer_name=customer_name or "Sin nombre",
                delivery_date=delivery_ymd,
                shipping_address=address,
                items=items_for_co,
            )
            created += 1
        except ValueError as e:
            if "ya existe" in str(e).lower():
                existed += 1
            else:
                errors.append(f"{co_number}: {e}")

    return created, existed, errors, total_api, total_filtradas, first_order


def _parse_mrpeasy_co_pdf(text: str) -> Optional[dict]:
    """
    Parsea un PDF de Customer Order de MRPeasy (ej. CO02780.pdf).
    Estructura: "Customer Order CO02780", "Customer: ...", "Created: MM/DD/YYYY",
    "Shipping address: ...", luego tabla con líneas: "1 A1543", nombre, ">>>>>> 10 bag ... <<<<<<".
    Devuelve { co_number, customer_name, delivery_date, shipping_address, items: [{ product_code, product_name, requested_qty, product_group }] }
    o None si no se detecta CO.
    """
    co_number = None
    m = re.search(r"Customer\s+Order\s+(CO\s*\d+)", text, re.IGNORECASE)
    if m:
        co_number = m.group(1).replace(" ", "")
    if not co_number:
        return None

    customer_name = "Sin nombre"
    m = re.search(r"Customer:\s*(.+?)(?=\n[A-Z]|\n\n|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        customer_name = re.sub(r"\s+", " ", m.group(1).strip()).strip()
        if customer_name.upper().startswith("CU"):
            parts = customer_name.split(None, 1)
            if len(parts) > 1:
                customer_name = parts[1]

    delivery_date = ""
    for pat in [r"Delivery date:\s*(\d{1,2}/\d{1,2}/\d{4})", r"Created:\s*(\d{1,2}/\d{1,2}/\d{4})"]:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            delivery_date = m.group(1)
            break

    shipping_address = ""
    m = re.search(r"Shipping address:\s*(.+?)(?=Internal notes:|Product\s+Quantity|$)", text, re.IGNORECASE | re.DOTALL)
    if m:
        shipping_address = " ".join(l.strip() for l in m.group(1).splitlines() if l.strip()).strip()[:500]

    items = []
    lines = text.splitlines()
    i = 0
    line_item_re = re.compile(r"^(\d+)\s+(A\d+)\s*(.*)$")
    qty_block_re = re.compile(r">>>>>>\s*(\d+)\s*")

    while i < len(lines):
        line = lines[i]
        line_stripped = line.strip()
        match = line_item_re.match(line_stripped)
        if match:
            item_num, product_code, name_start = match.group(1), match.group(2), match.group(3).strip()
            name_parts = [name_start] if name_start else []
            i += 1
            while i < len(lines):
                next_ln = lines[i].strip()
                if ">>>>>>" in next_ln:
                    qty_m = qty_block_re.search(next_ln)
                    requested_qty = int(qty_m.group(1)) if qty_m else 0
                    product_name = " ".join(name_parts).strip() or product_code
                    product_group = ""
                    if any(s in product_name.lower() for s in ("sauce", "salsa", "mayo", "dip")):
                        product_group = "Sauces"
                    items.append({
                        "product_code": product_code,
                        "product_name": product_name[:200],
                        "product_group": product_group,
                        "requested_qty": requested_qty,
                    })
                    i += 1
                    break
                if next_ln and ">>>>>>" not in next_ln and not re.match(r"^\d+\s+A\d+", next_ln):
                    name_parts.append(next_ln)
                i += 1
            continue
        i += 1

    return {
        "co_number": co_number,
        "customer_name": customer_name or "Sin nombre",
        "delivery_date": delivery_date,
        "shipping_address": shipping_address,
        "items": items,
    }


def _import_customer_orders_pdf(uploaded_file) -> tuple:
    """
    Importa CO desde PDF tipo MRPeasy (Customer Order COxxxx).
    Extrae cabecera + todos los productos (código, nombre, cantidad) para que aparezcan en Picking
    listos para escanear LOT e ingresar cantidades.
    """
    try:
        from PyPDF2 import PdfReader
    except ImportError:
        return 0, 0, ["Falta instalar PyPDF2: pip install PyPDF2"]

    imported, skipped, errors = 0, 0, []
    try:
        pdf_bytes = uploaded_file.read()
        reader = PdfReader(io.BytesIO(pdf_bytes))
        text = ""
        for page in reader.pages:
            text += (page.extract_text() or "") + "\n"
    except Exception as e:
        return 0, 0, [f"Error leyendo PDF: {e}"]

    if not text.strip():
        return 0, 0, ["El PDF no contiene texto extraíble (puede ser solo imágenes)."]

    parsed = _parse_mrpeasy_co_pdf(text)
    if not parsed:
        return 0, 0, ["No se detectó una Customer Order en formato MRPeasy (buscar 'Customer Order CO...')."]

    co_number = parsed["co_number"]
    try:
        add_customer_order(
            co_number=co_number,
            customer_name=parsed["customer_name"],
            delivery_date=_parse_delivery_date(parsed["delivery_date"]) or datetime.now().strftime("%Y-%m-%d"),
            shipping_address=parsed["shipping_address"],
            items=parsed["items"],
        )
        imported = 1
        if not parsed["items"]:
            errors.append("Se importó la CO pero no se detectaron líneas de producto; añádelas en Picking.")
    except ValueError as e:
        if "ya existe" in str(e).lower():
            skipped = 1
        else:
            errors.append(f"{co_number}: {e}")

    return imported, skipped, errors


# --- Pantalla 1: Lista CO pendientes ---
if tab_choice == "1. Lista CO pendientes":
    st.markdown("### Pantalla 1 – Lista de CO")

    st.markdown("#### CO pendientes desde MRPeasy (Confirmed + DropShip Fava + Not booked, delivery ≥ marzo)")
    if st.button("🔄 Sincronizar con MRPeasy"):
        with st.spinner("Consultando MRPeasy..."):
            created, existed, errs, total_api, total_filtradas, first_order = _sync_pending_from_mrpeasy()
        st.caption(f"MRPeasy devolvió {total_api} órdenes. Con Confirmed + Fava + Not booked: {total_filtradas}. Nuevas: {created}. Ya existían: {existed}.")
        if created or existed:
            st.success(f"Sincronización completada. Nuevas CO: {created} | Ya existentes: {existed}.")
        if total_api == 0:
            st.warning("La API no devolvió ninguna orden. Revisa MRPEASY_API_KEY y MRPEASY_API_SECRET en secrets.")
        elif total_filtradas == 0 and total_api > 0:
            st.warning("Ninguna orden pasó el filtro (Confirmed + DropShip Fava + Product status Not booked). Revisa abajo los campos de la primera CO.")
            if first_order is not None:
                all_keys = sorted(first_order.keys())
                st.info("**Todos los campos de la primera CO (nombres exactos de la API):** " + ", ".join(f"`{k}`" for k in all_keys))
                status_fields = {k: first_order.get(k) for k in ("status", "status_text", "state", "order_status", "status_id") if k in first_order}
                dropship_fields = {k: first_order.get(k) for k in ("dropship_vendor_id", "dropship_vendor", "vendor_id", "vendor", "ship_vendor_id") if k in first_order}
                custom_keys = [k for k in all_keys if str(k).lower().startswith("custom_")]
                if custom_keys:
                    custom_fields = {k: first_order.get(k) for k in custom_keys}
                    st.info("**Campos custom_* (aquí suele ir DropShip Vendor en MRPeasy):** " + " | ".join(f"`{k}` = {repr(v)}" for k, v in custom_fields.items()))
                if status_fields:
                    st.info("**Status:** " + " | ".join(f"`{k}` = {repr(v)}" for k, v in status_fields.items()))
                if dropship_fields:
                    st.info("**DropShip/Vendor:** " + " | ".join(f"`{k}` = {repr(v)}" for k, v in dropship_fields.items()))
                product_status_fields = {k: first_order.get(k) for k in ("part_status", "product_status", "product_status_id", "item_status") if k in first_order}
                if product_status_fields:
                    st.info("**Product status:** " + " | ".join(f"`{k}` = {repr(v)}" for k, v in product_status_fields.items()))
                with st.expander("🔍 Ver estructura completa de la primera CO (para ajustar filtro)"):
                    st.json(first_order)
        if errs:
            for e in errs[:10]:
                st.error(e)
            if len(errs) > 10:
                st.error(f"... y {len(errs)-10} errores más.")
        if created:
            st.rerun()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        # Por defecto solo marzo en adelante (alineado con la sincronización MRPeasy)
        default_from = datetime.now().replace(month=3, day=1).date()
        date_from = st.date_input("Fecha desde", value=default_from, key="filter_date_from")
    with col_f2:
        CUSTOMER_OPTIONS = [
            "Todos",
            "Damas",
            "folfol - Chabanel",
            "folfol - Van Horne",
            "Mahrouse - Acadie",
            "Mahrouse - Downtown",
        ]
        filter_customer = st.selectbox("Cliente (filtrar)", CUSTOMER_OPTIONS, key="filter_customer")
    with col_f3:
        filter_status = st.selectbox(
            "Estado",
            ["Todos", CO_STATUS_PENDING, CO_STATUS_IN_PREPARATION, CO_STATUS_CLOSED],
            key="filter_status",
        )

    date_from_str = date_from.strftime("%Y-%m-%d") if date_from else None
    status_filter = None if filter_status == "Todos" else filter_status

    customer_filter = None if filter_customer == "Todos" else filter_customer
    orders = list_customer_orders(
        date_from=date_from_str,
        date_to=None,
        customer=customer_filter,
        status=status_filter,
    )

    # Agrupación por cliente
    by_customer = {}
    for o in orders:
        c = o.get("customer_name") or "Sin cliente"
        if c not in by_customer:
            by_customer[c] = []
        by_customer[c].append(o)

    if orders:
        for customer_name, co_list in sorted(by_customer.items()):
            for co in co_list:
                co_id = co.get("id") or ""
                delivery_str = _normalize_delivery_date(co.get("delivery_date")) or co.get("delivery_date") or "—"
                status = co.get("status") or CO_STATUS_PENDING
                if status == CO_STATUS_PENDING:
                    status_class = "status-pending"
                    label = "No iniciada"
                elif status == CO_STATUS_IN_PREPARATION:
                    status_class = "status-preparation"
                    label = "En preparación"
                else:
                    status_class = "status-closed"
                    label = "Cerrada"
                st.markdown(f"**{customer_name}**")
                st.markdown(f'<span class="{status_class}">{label}</span>', unsafe_allow_html=True)
                st.markdown('<div class="co-card">', unsafe_allow_html=True)
                if status in (CO_STATUS_PENDING, CO_STATUS_IN_PREPARATION):
                    if st.button(co_id, key=f"sel_{co_id}"):
                        st.session_state.selected_co_id = co_id
                        st.session_state.goto_picking = True
                        set_order_in_preparation(co_id)
                        st.rerun()
                else:
                    st.markdown(f'<div class="co-button-fake">{co_id}</div>', unsafe_allow_html=True)
                st.markdown("</div>", unsafe_allow_html=True)
                st.caption(f"Fecha delivery: {delivery_str}")
                st.divider()
    else:
        st.info("No hay órdenes con los filtros aplicados.")

# --- Pantalla 2: Picking ---
elif tab_choice == "2. Picking":
    st.markdown("### Pantalla 2 – Picking")
    if st.button("← Volver a lista de CO", key="back_to_list"):
        st.session_state.goto_list = True
        st.rerun()
    st.markdown("")  # pequeño espacio
    co_id = st.session_state.selected_co_id
    if not co_id:
        st.info("Selecciona una CO en la pestaña **1. Lista CO pendientes** (haz clic en el número de la CO).")
    else:
        co = get_customer_order(co_id)
        if not co:
            st.warning("CO no encontrada.")
            st.session_state.selected_co_id = None
        else:
            # Encabezado tipo Picking List: Date, Customer order, Customer
            delivery_date_str = _normalize_delivery_date(co.get("delivery_date")) or co.get("delivery_date") or "—"
            today_str = datetime.now().strftime("%d/%m/%Y")
            st.markdown("### Picking List " + (co.get("id") or ""))
            st.markdown(f"**Date:** {today_str} · **Customer order:** {co.get('id')} · **Customer:** {co.get('customer_name') or '—'}")
            st.markdown("")
            status = co.get("status") or CO_STATUS_PENDING
            status_label = "No iniciada" if status == CO_STATUS_PENDING else "En preparación" if status == CO_STATUS_IN_PREPARATION else "Cerrada"
            st.caption(f"Estado: {status_label}")

            if status == CO_STATUS_CLOSED:
                st.success("Esta orden ya está cerrada.")
                if st.button("Limpiar selección"):
                    st.session_state.selected_co_id = None
                    st.rerun()
            else:
                items = co.get("items") or []
                if items:
                    # Una sola tabla Picking List con controles en cada fila
                    if "item_names_cache" not in st.session_state:
                        st.session_state.item_names_cache = {}
                    if "item_locations_cache" not in st.session_state:
                        st.session_state.item_locations_cache = {}
                    cache = st.session_state.item_names_cache
                    location_cache = st.session_state.item_locations_cache
                    if "picking_values" not in st.session_state or st.session_state.get("picking_co_id") != co_id:
                        st.session_state.picking_co_id = co_id
                        st.session_state.picking_values = {
                            str(it.get("id")): {
                                "picked_qty": it.get("picked_qty"),
                                "origin": it.get("origin"),
                                "lot_number": it.get("lot_number") or "",
                                "difference_reason": it.get("difference_reason"),
                                "scanned_code": it.get("scanned_code") or "",
                            }
                            for it in items
                        }
                    api = None
                    st.markdown("**Picking List** (completa cada fila: ✓ Tomó, Cant. tomada, Origen, LOT, Código escaneado)")
                    # Fila de encabezados
                    h1, h2, h3, h4, h5, h6, h7 = st.columns([2, 0.7, 0.6, 0.9, 1, 1, 1.2])
                    h1.caption("**Stock item**")
                    h2.caption("**Solicitada**")
                    h3.caption("**✓ Tomó**")
                    h4.caption("**Cant. tomada**")
                    h5.caption("**Origen**")
                    h6.caption("**LOT**")
                    h7.caption("**Código escaneado**")
                    updated_items = []
                    for it in items:
                        iid = str(it.get("id"))
                        vals = st.session_state.picking_values.get(iid, {})
                        code = (it.get("product_code") or "").strip() or "—"
                        name_raw = (it.get("product_name") or "").strip()
                        if name_raw and name_raw != code:
                            display_name = name_raw
                        elif code and code != "—":
                            if code in cache:
                                display_name = cache[code] or code
                            else:
                                try:
                                    if api is None:
                                        api = APIManager()
                                    detail = api.get_item_details(code)
                                    display_name = (detail.get("title") or detail.get("name") or code) if detail else code
                                    cache[code] = display_name
                                    if detail:
                                        loc = _location_from_item_detail(detail)
                                        if loc:
                                            location_cache[code] = loc
                                except Exception:
                                    display_name = code
                                    cache[code] = code
                        else:
                            display_name = "—"
                        item_label = f"{code} {display_name}" if (code != "—" and display_name != "—") else (display_name or code)
                        requested = float(it.get("requested_qty") or 0)
                        c1, c2, c3, c4, c5, c6, c7 = st.columns([2, 0.7, 0.6, 0.9, 1.2, 1, 1.2])
                        with c1:
                            st.text(item_label[:50] + ("…" if len(item_label) > 50 else ""))
                        with c2:
                            st.text(str(int(requested)) if requested == int(requested) else str(requested))
                        with c3:
                            took = st.checkbox(
                                "Sí",
                                value=vals.get("picked_qty") is None or float(vals.get("picked_qty") or 0) == requested,
                                key=f"took_{iid}",
                                label_visibility="collapsed",
                            )
                        with c4:
                            if took:
                                st.session_state[f"picked_{iid}"] = requested
                                new_picked = st.number_input(
                                    "qty", value=requested, min_value=0.0, step=0.5, key=f"picked_{iid}", disabled=True, label_visibility="collapsed",
                                )
                            else:
                                new_picked = st.number_input(
                                    "qty",
                                    value=float(vals.get("picked_qty")) if vals.get("picked_qty") is not None else requested,
                                    min_value=0.0, step=0.5, key=f"picked_{iid}", label_visibility="collapsed",
                                )
                        with c5:
                            origin_display = (vals.get("origin") or it.get("origin") or "").strip() or ""
                            if not origin_display and code and code != "—":
                                if code in location_cache:
                                    origin_display = location_cache[code] or ""
                                else:
                                    try:
                                        if api is None:
                                            api = APIManager()
                                        detail = api.get_item_details(code)
                                        loc = _location_from_item_detail(detail) if detail else ""
                                        if loc:
                                            location_cache[code] = loc
                                            origin_display = loc
                                    except Exception:
                                        pass
                            st.caption("Origen")
                            st.text(origin_display or "—")
                            new_origin = (origin_display or None) if origin_display else None
                        with c6:
                            new_lot = st.text_input(
                                "LOT", value=vals.get("lot_number") or "", key=f"lot_{iid}", placeholder="L36080", label_visibility="collapsed",
                            )
                        with c7:
                            scanned = st.text_input(
                                "Scan", value=vals.get("scanned_code") or "", key=f"scan_{iid}", placeholder="Escanear o escribir", label_visibility="collapsed",
                            )
                        # Solo consideramos diferencia relevante si se tomó MENOS de lo solicitado
                        has_diff = (
                            new_picked is not None
                            and requested is not None
                            and float(new_picked) + 0.001 < float(requested)
                        )
                        if has_diff:
                            st.caption("⚠ Motivo de diferencia:")
                            diff_sel = st.radio(
                                "Motivo", options=["Sin stock", "Producción no lista"], key=f"reason_{iid}", horizontal=True,
                            )
                            diff_reason = "SinStock" if diff_sel == "Sin stock" else "ProduccionNoLista"
                        else:
                            diff_reason = None
                        st.session_state.picking_values[iid] = {
                            "picked_qty": new_picked,
                            "origin": new_origin or None,
                            "lot_number": (new_lot or "").strip() or None,
                            "difference_reason": diff_reason,
                            "scanned_code": (scanned or "").strip() or None,
                        }
                        updated_items.append({
                            "id": iid,
                            "picked_qty": new_picked,
                            "origin": new_origin or None,
                            "lot_number": (new_lot or "").strip() or None,
                            "difference_reason": diff_reason,
                        })
                        st.divider()
                    # Validación y botón Cerrar Orden (se mantiene igual)
                    co_virtual = {
                        "id": co_id,
                        "items": [
                            {
                                "id": it.get("id"),
                                "product_name": it.get("product_name"),
                                "product_code": it.get("product_code"),
                                "requested_qty": it.get("requested_qty"),
                                "picked_qty": st.session_state.picking_values.get(str(it.get("id")), {}).get("picked_qty"),
                                "origin": st.session_state.picking_values.get(str(it.get("id")), {}).get("origin"),
                                "lot_number": st.session_state.picking_values.get(str(it.get("id")), {}).get("lot_number"),
                                "requires_lot": requires_lot_by_group(it.get("product_group") or ""),
                                "difference_reason": st.session_state.picking_values.get(str(it.get("id")), {}).get("difference_reason"),
                                "difference_qty": None,
                            }
                            for it in items
                        ],
                    }
                    for it in co_virtual["items"]:
                        r = float(it.get("requested_qty") or 0)
                        p = it.get("picked_qty")
                        if p is not None:
                            try:
                                p = float(p)
                            except (TypeError, ValueError):
                                p = None
                        it["picked_qty"] = p
                        if r is not None and p is not None:
                            it["difference_qty"] = round(r - p, 4)
                    can_close, errors = can_close_order(co_virtual)
                    if errors:
                        st.markdown("**Validación para cerrar:**")
                        for e in errors:
                            st.error(e)
                    closed_by = st.text_input("Cerrado por (nombre)", key="closed_by", placeholder="Tu nombre")
                    if st.button("Cerrar Orden", disabled=not can_close, type="primary"):
                        if not (closed_by and closed_by.strip()):
                            st.error("Indica quién cierra la orden.")
                        else:
                            update_payload = []
                            for it in co.get("items", []):
                                iid = str(it.get("id"))
                                v = st.session_state.picking_values.get(iid, {})
                                update_payload.append({
                                    "id": it.get("id"),
                                    "picked_qty": v.get("picked_qty"),
                                    "origin": v.get("origin"),
                                    "lot_number": v.get("lot_number"),
                                    "difference_reason": v.get("difference_reason"),
                                })
                            try:
                                updated_co = update_order_picking(co_id, update_payload, closed_by=closed_by.strip())
                                if updated_co.get("status") == CO_STATUS_CLOSED:
                                    created = create_incidents_from_closed_order(updated_co)
                                    items_with_diff = [it for it in updated_co.get("items", []) if (it.get("difference_qty") or 0) != 0]
                                    if items_with_diff and is_email_configured():
                                        send_co_difference_alert(
                                            co_number=updated_co.get("id", ""),
                                            customer_name=updated_co.get("customer_name", ""),
                                            delivery_date=updated_co.get("delivery_date", ""),
                                            closed_by=closed_by.strip(),
                                            items_with_difference=items_with_diff,
                                        )
                                    st.success("Orden cerrada. Se generaron incidentes por cada línea con diferencia.")
                                    if created:
                                        st.info(f"{len(created)} incidente(s) creado(s). Email enviado si está configurado.")
                                    st.session_state.selected_co_id = None
                                    st.session_state.picking_values = {}
                                    st.rerun()
                            except ValueError as e:
                                st.error(str(e))
                if not items:
                    st.warning("Esta CO no tiene líneas (p. ej. fue importada desde CSV). Carga desde MRPeasy o añade las líneas abajo.")
                    if st.button("📥 Cargar ítems desde MRPeasy", key="load_items_mrpeasy"):
                        with st.spinner("Buscando CO en MRPeasy y cargando ítems..."):
                            try:
                                api = APIManager()
                                raw_list = api.fetch_customer_orders()
                                if not raw_list:
                                    st.error("No se pudo obtener la lista de CO de MRPeasy.")
                                else:
                                    co_id_norm = str(co_id).strip()
                                    found = None
                                    for o in raw_list:
                                        num = str(o.get("number") or o.get("code") or "").strip()
                                        if num == co_id_norm:
                                            found = o
                                            break
                                    if not found:
                                        st.error(f"No se encontró la CO {co_id} en MRPeasy.")
                                    else:
                                        mrpeasy_id = (
                                            found.get("id")
                                            or found.get("customer_order_id")
                                            or found.get("order_id")
                                            or found.get("co_id")
                                            or found.get("customer_order_no")
                                        )
                                        if mrpeasy_id is None:
                                            for k, v in found.items():
                                                if isinstance(v, (int, float)) and ("id" in k.lower() or k == "no"):
                                                    mrpeasy_id = v
                                                    break
                                        if mrpeasy_id is None:
                                            st.error("La API no devolvió el ID de la CO. Campos recibidos: " + ", ".join(f"`{k}`" for k in sorted(found.keys())))
                                        else:
                                            detail = api.get_customer_order_details(int(mrpeasy_id))
                                            if not detail:
                                                st.error("No se pudo obtener el detalle de la CO desde MRPeasy.")
                                            else:
                                                raw_lines = detail.get("products") or detail.get("order_lines") or detail.get("items") or detail.get("lines") or []
                                                items_for_co = []
                                                for line in raw_lines if isinstance(raw_lines, list) else []:
                                                    if not isinstance(line, dict):
                                                        continue
                                                    code = (line.get("product_code") or line.get("item_code") or line.get("code") or "").strip()
                                                    name = (line.get("product_name") or line.get("title") or line.get("name") or "").strip()
                                                    qty = line.get("quantity") or line.get("requested_quantity") or line.get("qty") or line.get("ordered_quantity") or 0
                                                    try:
                                                        qty = float(qty)
                                                    except (TypeError, ValueError):
                                                        qty = 0
                                                    group = (line.get("product_group") or line.get("group") or line.get("group_name") or "").strip()
                                                    loc = (
                                                        line.get("location")
                                                        or line.get("warehouse")
                                                        or line.get("storage")
                                                        or line.get("default_location")
                                                        or line.get("origin")
                                                        or line.get("default_storage_location")
                                                        or line.get("storage_location")
                                                        or line.get("default_storage_location_name")
                                                        or line.get("storage_location_name")
                                                        or ""
                                                    )
                                                    if isinstance(loc, dict):
                                                        loc = loc.get("name") or loc.get("title") or loc.get("code") or ""
                                                    loc = str(loc).strip() if loc else None
                                                    if not loc and (code or name):
                                                        try:
                                                            item_detail = api.get_item_details(code or name[:20] if name else "")
                                                            loc = _location_from_item_detail(item_detail) or None
                                                        except Exception:
                                                            pass
                                                    if code or name:
                                                        items_for_co.append({"product_code": code or name[:20], "product_name": name or code, "product_group": group, "requested_qty": qty, "origin": loc})
                                                if not items_for_co:
                                                    st.warning("La CO en MRPeasy no tiene productos/líneas en la respuesta, o el formato es distinto.")
                                                else:
                                                    add_items_to_order(co_id, items_for_co)
                                                    st.success(f"Se cargaron {len(items_for_co)} ítem(s) desde MRPeasy.")
                                                    st.rerun()
                            except Exception as e:
                                st.error(f"Error: {e}")
                    if "co_new_lines" not in st.session_state:
                        st.session_state.co_new_lines = {}
                    key = f"co_lines_{co_id}"
                    if key not in st.session_state.co_new_lines:
                        st.session_state.co_new_lines[key] = []
                    lines_buf = st.session_state.co_new_lines[key]
                    with st.form("add_lines_to_co_form"):
                        acode = st.text_input("Código producto", key="al_code")
                        aname = st.text_input("Nombre producto", key="al_name")
                        agroup = st.text_input("Grupo (Dips, Sauces…)", key="al_group")
                        aqty = st.number_input("Cantidad solicitada", min_value=0, value=0, key="al_qty")
                        if st.form_submit_button("Añadir línea"):
                            if acode and aname:
                                lines_buf.append({"product_code": acode, "product_name": aname, "product_group": agroup, "requested_qty": aqty})
                                st.rerun()
                    if lines_buf:
                        st.markdown("Líneas a guardar:")
                        for L in lines_buf:
                            st.text(f"  {L.get('product_code')} | {L.get('product_name')} | {L.get('product_group')} | {L.get('requested_qty')}")
                        if st.button("Guardar líneas en la CO"):
                            try:
                                add_items_to_order(co_id, lines_buf)
                                st.session_state.co_new_lines[key] = []
                                st.success("Líneas guardadas. Recarga la CO para hacer el picking.")
                                st.rerun()
                            except Exception as e:
                                st.error(str(e))

# --- Pantalla 3: Incidentes operativos ---
elif tab_choice == "3. Incidentes operativos":
    st.markdown("### Pantalla 3 – Incidentes operativos")
    st.caption("Filtros por tipo, estado, producto, fecha. Asignación: Sin stock → Inventory/Compras; Producción no lista → Producción.")

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        inc_reason = st.selectbox("Tipo (motivo)", ["Todos", "SinStock", "ProduccionNoLista"], key="inc_reason")
    with c2:
        inc_status = st.selectbox(
            "Estado",
            ["Todos", INCIDENT_STATUS_PENDING, INCIDENT_STATUS_IN_PROGRESS, INCIDENT_STATUS_RESOLVED],
            key="inc_status",
        )
    with c3:
        inc_product = st.text_input("Producto", key="inc_product", placeholder="Nombre o código")
    with c4:
        inc_date_from = st.date_input("Fecha desde (incidente)", key="inc_date_from", value=None)
        inc_date_to = st.date_input("Fecha hasta", key="inc_date_to", value=None)

    reason_f = None if inc_reason == "Todos" else inc_reason
    status_f = None if inc_status == "Todos" else inc_status
    product_f = inc_product.strip() or None
    date_from_f = inc_date_from.strftime("%Y-%m-%d") if inc_date_from else None
    date_to_f = inc_date_to.strftime("%Y-%m-%d") if inc_date_to else None

    incidents = list_incidents(reason=reason_f, status=status_f, product=product_f, date_from=date_from_f, date_to=date_to_f)

    if not incidents:
        st.info("No hay incidentes con los filtros aplicados.")
    else:
        for inc in incidents:
            with st.expander(
                f"CO {inc.get('co_id')} | {inc.get('product_name') or inc.get('product_code')} | "
                f"Faltante: {inc.get('difference_qty')} | {inc.get('status')}"
            ):
                st.write(f"**Motivo:** {inc.get('reason')} → Asignado a: **{inc.get('assigned_to_role')}**")
                st.write(f"Solicitado: {inc.get('requested_qty')} | Tomado: {inc.get('picked_qty')} | Faltante: {inc.get('difference_qty')}")
                st.caption(f"Creado: {inc.get('created_at')} | Resuelto: {inc.get('resolved_at') or '—'} por {inc.get('resolved_by') or '—'}")
                if inc.get("status") != INCIDENT_STATUS_RESOLVED:
                    new_status = st.selectbox(
                        "Cambiar estado",
                        [INCIDENT_STATUS_IN_PROGRESS, INCIDENT_STATUS_RESOLVED],
                        key=f"inc_status_{inc.get('id')}",
                    )
                    res_by = st.text_input("Resuelto por (si aplica)", key=f"inc_resolved_{inc.get('id')}", placeholder="Nombre")
                    if st.button("Actualizar estado", key=f"inc_btn_{inc.get('id')}"):
                        update_incident_status(
                            inc["id"],
                            new_status,
                            resolved_by=res_by if new_status == INCIDENT_STATUS_RESOLVED else "",
                        )
                        st.success("Estado actualizado.")
                        st.rerun()
