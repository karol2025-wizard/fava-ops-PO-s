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

tab_list, tab_picking, tab_incidents = st.tabs([
    "1. Lista CO pendientes",
    "2. Picking",
    "3. Incidentes operativos",
])

def _parse_delivery_date(s: str) -> str:
    """Convierte MM/DD/YYYY a YYYY-MM-DD."""
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
            return s[:10]

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


def _sync_pending_from_mrpeasy() -> tuple:
    """
    Trae Customer Orders desde MRPeasy y crea/actualiza las que estén:
    - Status = Confirmed
    - Invoice status = Not invoiced
    Devuelve (creadas, ya_existian, errores).
    """
    created, existed, errors = 0, 0, []
    try:
        api = APIManager()
    except Exception as e:
        return 0, 0, [f"No se pudo inicializar APIManager (MRPeasy): {e}"]
    try:
        raw = api.fetch_customer_orders()
    except Exception as e:
        return 0, 0, [f"Error consultando customer-orders en MRPeasy: {e}"]
    if not raw:
        return 0, 0, ["MRPeasy no devolvió customer orders (o la lista está vacía)."]

    for o in raw:
        status = (str(o.get("status_text") or o.get("status") or "")).strip()
        vendor_text = str(
            o.get("drop_ship_vendor")
            or o.get("drop_ship_vendor_name")
            or o.get("dropship_vendor")
            or o.get("Dropship Vendor")
            or ""
        ).strip()

        # Solo CO cuyo DropShip Vendor sea Fava (lo que ves en MRPeasy)
        if "fava" not in vendor_text.lower():
            continue
        # Opcionalmente, mantener solo Confirmed para evitar entregadas/canceladas
        if status and status != "Confirmed":
            continue

        co_number = (o.get("number") or o.get("code") or "").strip()
        if not co_number:
            continue

        if get_customer_order(co_number):
            existed += 1
            continue

        customer_name = (o.get("customer_name") or o.get("customer") or "").strip()
        delivery_date = str(o.get("delivery_date") or o.get("delivery_time") or "")[:10]
        address = (o.get("address") or o.get("shipping_address") or "").strip()

        try:
            add_customer_order(
                co_number=co_number,
                customer_name=customer_name or "Sin nombre",
                delivery_date=_parse_delivery_date(delivery_date) or datetime.now().strftime("%Y-%m-%d"),
                shipping_address=address,
                items=[],
            )
            created += 1
        except ValueError as e:
            if "ya existe" in str(e).lower():
                existed += 1
            else:
                errors.append(f"{co_number}: {e}")

    return created, existed, errors


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
with tab_list:
    st.markdown("### Pantalla 1 – Lista de CO")
    st.caption("Filtros, agrupación por cliente. Rojo: No iniciada | Amarillo: En preparación | Verde: Cerrada.")

    # Importar desde CSV o PDF
    with st.expander("📥 Importar CO desde CSV o PDF"):
        st.caption("**CSV:** columnas Number, Customer name, Delivery date, Address (CO sin líneas). **PDF (MRPeasy):** sube el PDF de la CO (ej. CO02780.pdf); se importan cabecera y todos los productos con cantidad solicitada, listos en Picking para escanear LOT e ingresar cantidades.")
        uploaded = st.file_uploader("Archivo CSV o PDF", type=["csv", "pdf"], key="delivery_csv_upload")
        if uploaded:
            is_pdf = (uploaded.name or "").lower().endswith(".pdf")
            if st.button("Importar"):
                if is_pdf:
                    imp, sk, errs = _import_customer_orders_pdf(uploaded)
                else:
                    imp, sk, errs = _import_customer_orders_csv(uploaded)
                if imp or sk:
                    st.success(f"Importadas: {imp} | Omitidas (ya existían): {sk}.")
                if errs:
                    for e in errs[:15]:
                        st.error(e)
                    if len(errs) > 15:
                        st.error(f"... y {len(errs)-15} más.")
                if imp or sk or errs:
                    st.rerun()

    st.markdown("#### CO pendientes desde MRPeasy (DropShip Vendor = Fava)")
    if st.button("🔄 Sincronizar con MRPeasy"):
        created, existed, errs = _sync_pending_from_mrpeasy()
        if created or existed:
            st.success(f"Sincronización completada. Nuevas CO: {created} | Ya existentes: {existed}.")
        if errs:
            for e in errs[:10]:
                st.error(e)
            if len(errs) > 10:
                st.error(f"... y {len(errs)-10} errores más.")
        if created or existed or errs:
            st.rerun()

    col_f1, col_f2, col_f3 = st.columns(3)
    with col_f1:
        date_from = st.date_input("Fecha desde", value=None, key="filter_date_from")
        date_to = st.date_input("Fecha hasta", value=None, key="filter_date_to")
    with col_f2:
        filter_customer = st.text_input("Cliente (filtrar)", key="filter_customer", placeholder="Nombre cliente")
    with col_f3:
        filter_status = st.selectbox(
            "Estado",
            ["Todos", CO_STATUS_PENDING, CO_STATUS_IN_PREPARATION, CO_STATUS_CLOSED],
            key="filter_status",
        )

    date_from_str = date_from.strftime("%Y-%m-%d") if date_from else None
    date_to_str = date_to.strftime("%Y-%m-%d") if date_to else None
    status_filter = None if filter_status == "Todos" else filter_status

    orders = list_customer_orders(
        date_from=date_from_str,
        date_to=date_to_str,
        customer=filter_customer.strip() or None,
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
            st.markdown(f"**{customer_name}**")
            for co in co_list:
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
                st.markdown(f'<span class="{status_class}">{label}</span>', unsafe_allow_html=True)
                c1, c2, c3 = st.columns([2, 2, 2])
                with c1:
                    st.text(f"CO: {co.get('id')}")
                with c2:
                    st.text(f"Fecha delivery: {co.get('delivery_date')}")
                with c3:
                    if status in (CO_STATUS_PENDING, CO_STATUS_IN_PREPARATION):
                        if st.button("Seleccionar", key=f"sel_{co.get('id')}"):
                            st.session_state.selected_co_id = co.get("id")
                            set_order_in_preparation(co.get("id"))
                            st.rerun()
                st.divider()
    else:
        st.info("No hay órdenes con los filtros aplicados.")

    st.markdown("---")
    st.markdown("**Nueva CO** (entrada manual en MVP)")
    if "new_co_lines" not in st.session_state:
        st.session_state.new_co_lines = []
    with st.expander("Crear nueva Customer Order"):
        st.markdown("Líneas añadidas:")
        if st.session_state.new_co_lines:
            for i, line in enumerate(st.session_state.new_co_lines):
                st.text(f"  {line.get('product_code')} | {line.get('product_name')} | {line.get('product_group')} | {line.get('requested_qty')}")
        else:
            st.caption("Aún no hay líneas. Usa el formulario «Añadir línea» abajo.")
        with st.form("add_line_co_form"):
            add_code = st.text_input("Código producto", key="new_line_code")
            add_name = st.text_input("Nombre producto", key="new_line_name")
            add_group = st.text_input("Grupo (ej. Dips, Sauces)", key="new_line_group")
            add_qty = st.number_input("Cantidad solicitada", min_value=0, value=0, key="new_line_qty")
            if st.form_submit_button("Añadir línea a la CO"):
                if add_code and add_name and add_qty >= 0:
                    st.session_state.new_co_lines.append({
                        "product_code": add_code,
                        "product_name": add_name,
                        "product_group": add_group,
                        "requested_qty": add_qty,
                    })
                    st.rerun()
                else:
                    st.error("Código, nombre y cantidad obligatorios.")
        with st.form("create_co_form"):
            new_id = st.text_input("Número CO", placeholder="CO-2025-001")
            new_customer = st.text_input("Cliente")
            new_delivery = st.date_input("Fecha delivery")
            new_address = st.text_input("Dirección envío (opcional)")
            if st.form_submit_button("Crear CO"):
                if not (new_id and new_customer and new_delivery):
                    st.error("Número CO, Cliente y Fecha delivery obligatorios.")
                elif not st.session_state.new_co_lines:
                    st.error("Añade al menos una línea con «Añadir línea a la CO».")
                else:
                    try:
                        add_customer_order(
                            co_number=new_id.strip(),
                            customer_name=new_customer.strip(),
                            delivery_date=new_delivery.strftime("%Y-%m-%d"),
                            shipping_address=new_address or "",
                            items=st.session_state.new_co_lines,
                        )
                        st.session_state.new_co_lines = []
                        st.success(f"CO {new_id} creada.")
                        st.rerun()
                    except Exception as e:
                        st.error(str(e))

# --- Pantalla 2: Picking ---
with tab_picking:
    st.markdown("### Pantalla 2 – Picking")
    co_id = st.session_state.selected_co_id
    if not co_id:
        st.info("Selecciona una CO en la pestaña **1. Lista CO pendientes** (botón «Seleccionar»).")
    else:
        co = get_customer_order(co_id)
        if not co:
            st.warning("CO no encontrada.")
            st.session_state.selected_co_id = None
        else:
            # Encabezado fijo
            st.markdown("**Encabezado**")
            h1, h2, h3, h4 = st.columns(4)
            h1.metric("CO", co.get("id"))
            h2.metric("Cliente", co.get("customer_name"))
            h3.metric("Fecha delivery", co.get("delivery_date"))
            status = co.get("status") or CO_STATUS_PENDING
            status_label = "No iniciada" if status == CO_STATUS_PENDING else "En preparación" if status == CO_STATUS_IN_PREPARATION else "Cerrada"
            h4.metric("Estado", status_label)

            if status == CO_STATUS_CLOSED:
                st.success("Esta orden ya está cerrada.")
                if st.button("Limpiar selección"):
                    st.session_state.selected_co_id = None
                    st.rerun()
            else:
                # Formulario de picking por línea
                st.markdown("**Líneas** (Cantidad tomada obligatoria; Origen; LOT obligatorio si grupo = Dips o Sauces)")
                items = co.get("items") or []
                if not items:
                    st.warning("Esta CO no tiene líneas (p. ej. fue importada desde CSV). Añade las líneas del pedido abajo.")
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
                else:
                    # Guardar en session_state los valores actuales para validar Cerrar
                    if "picking_values" not in st.session_state or st.session_state.get("picking_co_id") != co_id:
                        st.session_state.picking_co_id = co_id
                        st.session_state.picking_values = {
                            str(it.get("id")): {
                                "picked_qty": it.get("picked_qty"),
                                "origin": it.get("origin"),
                                "lot_number": it.get("lot_number") or "",
                                "difference_reason": it.get("difference_reason"),
                            }
                            for it in items
                        }

                    updated_items = []
                    for it in items:
                        iid = str(it.get("id"))
                        vals = st.session_state.picking_values.get(iid, {})
                        with st.container():
                            st.markdown(f"**{it.get('product_name') or it.get('product_code')}** ({it.get('product_group')})")
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                requested = float(it.get("requested_qty") or 0)
                                st.text_input("Cant. solicitada (read-only)", value=str(requested), key=f"ro_{iid}", disabled=True)
                            with col_b:
                                new_picked = st.number_input(
                                    "Cant. tomada (obligatorio)",
                                    min_value=0.0,
                                    value=float(vals.get("picked_qty")) if vals.get("picked_qty") is not None else requested,
                                    key=f"picked_{iid}",
                                    step=0.5,
                                )
                            with col_c:
                                new_origin = st.selectbox(
                                    "Origen",
                                    options=[""] + list(ORIGINS),
                                    index=([""] + list(ORIGINS)).index(vals.get("origin") or ""),
                                    key=f"origin_{iid}",
                                )
                            lot_required = requires_lot_by_group(it.get("product_group") or "")
                            new_lot = st.text_input(
                                "LOT number" + (" (obligatorio Dips/Sauces)" if lot_required else ""),
                                value=vals.get("lot_number") or "",
                                key=f"lot_{iid}",
                            )
                            # Control de diferencias
                            has_diff = new_picked is not None and requested is not None and new_picked != requested
                            if has_diff:
                                st.markdown('<div class="diff-block">⚠ Diferencia detectada – Motivo obligatorio</div>', unsafe_allow_html=True)
                                new_reason = st.radio(
                                    "Motivo",
                                    options=["Sin stock", "Producción no lista"],
                                    key=f"reason_{iid}",
                                    horizontal=True,
                                )
                                diff_reason = "SinStock" if new_reason == "Sin stock" else "ProduccionNoLista"
                            else:
                                diff_reason = None

                            # Persistir en session_state para el botón Cerrar
                            st.session_state.picking_values[iid] = {
                                "picked_qty": new_picked,
                                "origin": new_origin or None,
                                "lot_number": (new_lot or "").strip() or None,
                                "difference_reason": diff_reason,
                            }
                            updated_items.append({
                                "id": iid,
                                "picked_qty": new_picked,
                                "origin": new_origin or None,
                                "lot_number": (new_lot or "").strip() or None,
                                "difference_reason": diff_reason,
                            })

                    # Construir CO "virtual" para validar
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
                            # Build items for update_order_picking (need item id from co)
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
                            updated_co = update_order_picking(co_id, update_payload, closed_by=closed_by.strip())
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

# --- Pantalla 3: Incidentes operativos ---
with tab_incidents:
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
