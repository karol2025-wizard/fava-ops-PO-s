"""
MO Record Insert - Registro de cantidad del sticker (mismo flujo que MORecordInsert.exe)

Flujo (igual que el .exe):
1. Producción imprime el sticker con la cantidad real (ej: "13 bag (40 pcs)").
2. Registras aquí el LOT y la cantidad (o escaneas con barcode).
3. Se guarda en la base de datos → aparece en **ERP Close MO**.
4. En ERP Close MO seleccionas y cierras los MO en lote.

Al registrar se guarda en la base, se actualiza la cantidad en MRPEasy y se cierra el MO (estado Done)
usando el mismo servicio que ERP Close MO; la fila queda marcada como procesada (processed_at).
"""

import streamlit as st
import sys
import os
import requests
from datetime import datetime

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.weightlabelprinter_helper import insert_production_quantity, get_label_printer_quantity
from shared.production_workflow import ProductionWorkflow
from shared.database_manager import DatabaseManager
from shared.api_manager import APIManager
from shared.mo_lookup import MOLookup

try:
    from config import secrets
except Exception:
    secrets = {}

st.set_page_config(
    page_title="MO Record Insert - Lot y cantidad del sticker",
    page_icon="📋",
    layout="centered",
)


def _get_last_inserted_id_for_lot(lot_code: str):
    """Return the id of the most recently inserted row in erp_mo_to_import for this lot_code."""
    try:
        db = DatabaseManager()
        row = db.fetch_one(
            "SELECT id FROM erp_mo_to_import WHERE lot_code = %s ORDER BY id DESC LIMIT 1",
            (lot_code.strip(),),
        )
        return row["id"] if row and row.get("id") is not None else None
    except Exception:
        return None


def _mark_order_processed(order_id) -> bool:
    """Set processed_at for one row in erp_mo_to_import. Returns True if updated."""
    if order_id is None:
        return False
    try:
        db = DatabaseManager()
        current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        n = db.execute_query(
            "UPDATE erp_mo_to_import SET processed_at = %s WHERE id = %s AND processed_at IS NULL",
            (current_time, order_id),
        )
        return n > 0
    except Exception:
        return False


def _is_service_url_invalid(server_url: str) -> bool:
    """True if URL looks like MRPEasy web app instead of the automation service (e.g. Cloud Run)."""
    if not server_url or not server_url.strip():
        return True
    s = server_url.strip().lower()
    # La URL debe ser del servicio que expone /process_mo (ej. https://xxx.run.app), NO la web de MRPEasy
    if "app.mrpeasy.com" in s or "mrpeasy.com/accounting" in s:
        return True
    return False


def _close_mo_via_service(server_url: str, lot_code: str, quantity: float):
    """
    Call the same process_mo endpoint used by ERP Close MO to set MO status to Done.
    Returns (success, message).
    """
    if not (server_url and str(server_url).strip()):
        return False, "URL del servicio no configurada"
    if _is_service_url_invalid(server_url):
        return False, (
            "La URL en secrets apunta a la web de MRPEasy, no al servicio de cierre. "
            "Pon la URL del servicio que usa ERP Close MO (ej. https://tu-servicio.run.app)."
        )
    url = server_url.rstrip("/") + "/process_mo"
    payload = {"orders": [{"lot_number": lot_code, "quantity": float(quantity)}]}
    try:
        resp = requests.post(
            url,
            json=payload,
            headers={"Content-Type": "application/json"},
            timeout=300,
        )
        data = resp.json() if resp.headers.get("content-type", "").startswith("application/json") else {}
        results = data.get("results") or []
        for r in results:
            if (r.get("lot_number") or "").strip() == lot_code.strip():
                if r.get("success"):
                    return True, "MO cerrado (estado Done)."
                return False, r.get("error", "Error desconocido")
        if resp.status_code in (200, 201, 202, 204):
            return True, "MO cerrado (estado Done)."
        return False, data.get("error") or f"HTTP {resp.status_code}"
    except Exception as e:
        return False, str(e)

# Claves auxiliares: copiamos a los keys de los widgets ANTES de crear el form
# (Streamlit no permite modificar el key de un widget después de crearlo).
if "mo_preserved_lot" in st.session_state:
    st.session_state["mo_lot_code"] = st.session_state["mo_preserved_lot"]
    st.session_state["mo_uom"] = st.session_state.get("mo_preserved_uom", "")
    st.session_state["mo_show_lot_hint"] = True  # mostrar mensaje "ingresa cantidad"
    del st.session_state["mo_preserved_lot"]
    if "mo_preserved_uom" in st.session_state:
        del st.session_state["mo_preserved_uom"]
if "mo_preserved_quantity" in st.session_state:
    st.session_state["mo_quantity"] = st.session_state["mo_preserved_quantity"]
    del st.session_state["mo_preserved_quantity"]
if "mo_preserved_uom_lookup" in st.session_state:
    st.session_state["mo_uom"] = st.session_state["mo_preserved_uom_lookup"]
    del st.session_state["mo_preserved_uom_lookup"]
# Tras éxito: dejar formulario limpio para escanear el siguiente
if st.session_state.get("mo_clear_form_after_success"):
    st.session_state["mo_lot_code"] = ""
    st.session_state["mo_quantity"] = 0.0
    st.session_state["mo_uom"] = ""
    del st.session_state["mo_clear_form_after_success"]

# Inicializar cantidad/unidad si no existen (evita warning "default value + Session State API")
if "mo_quantity" not in st.session_state:
    st.session_state["mo_quantity"] = 0.0
if "mo_uom" not in st.session_state:
    st.session_state["mo_uom"] = ""

# --- Estilos tipo MORecordInsert: header oscuro y card del formulario ---
st.markdown("""
<style>
  /* Header estilo MORecordInsert (desktop) */
  div[data-testid="stVerticalBlock"] > div:first-child .stMarkdown h1 {
    margin-top: 0;
  }
  .mo-record-header {
    background: linear-gradient(135deg, #1e3a5f 0%, #2c5282 100%);
    color: white;
    padding: 1rem 1.5rem;
    border-radius: 8px;
    margin: -1rem -1rem 1.5rem -1rem;
    display: flex;
    align-items: center;
    justify-content: space-between;
    box-shadow: 0 2px 8px rgba(0,0,0,0.15);
  }
  .mo-record-header h2 {
    margin: 0;
    font-size: 1.6rem;
    font-weight: 700;
  }
  .mo-record-version {
    font-size: 0.9rem;
    opacity: 0.9;
  }
  /* Card del formulario (Lot Processing Form) */
  .mo-record-form-card {
    background: #fff;
    border: 1px solid #e2e8f0;
    border-radius: 12px;
    padding: 1.5rem 2rem;
    margin: 1rem 0;
    box-shadow: 0 2px 12px rgba(0,0,0,0.06);
  }
  /* Hint modo escáner */
  .mo-scanner-hint {
    font-size: 0.85rem;
    color: #475569;
    background: #f8fafc;
    border-left: 4px solid #3b82f6;
    padding: 0.5rem 0.75rem;
    border-radius: 4px;
    margin-bottom: 1rem;
  }
</style>
""", unsafe_allow_html=True)

# Header con título y versión (estilo MORecordInsert)
st.markdown("""
<div class="mo-record-header">
  <span>📋 MO Record Insert</span>
  <span class="mo-record-version">v1.0.0</span>
</div>
""", unsafe_allow_html=True)

st.caption(
    "Registra LOT y cantidad del sticker. Se guarda en la base de datos y aparece en **ERP Close MO** "
    "para cerrar los MO en lote (mismo flujo que MORecordInsert.exe)."
)
st.info(
    "Al pulsar **Registrar** se guarda en la base de datos, se actualiza la cantidad en MRPEasy y se marca el MO como **Done** (mismo flujo que ERP Close MO)."
)
# Avisar si la URL del servicio de cierre está mal (ej. apunta a la web de MRPEasy en vez del servicio)
_server_url = secrets.get("mrpeasy-could-run-po-automation-service-url") or secrets.get("mrpeasy_cloud_run_po_automation_service_url") or ""
if _server_url and _is_service_url_invalid(_server_url):
    st.error(
        "**Configuración:** La URL del servicio de cierre en secrets apunta a la **página web de MRPEasy**. "
        "Para que el estado pase a **Done** al registrar, pon en **.streamlit/secrets.toml** la clave "
        "**mrpeasy-could-run-po-automation-service-url** con la URL del **servicio** que usa ERP Close MO "
        "(ej. `https://tu-servicio.run.app`), no un enlace a app.mrpeasy.com."
    )

# Hint para uso con escáner de código de barras
st.markdown("""
<div class="mo-scanner-hint">
  <strong>Modo escáner:</strong> Haz clic en <strong>LOT Number</strong> (o recibe el foco al cargar). 
  Escanea el código → <kbd>Enter</kbd> hace <strong>Lookup</strong> y rellena automáticamente cantidad y unidad (como en MORecordInsert). 
  Revisa los valores y pulsa <strong>Registrar</strong>.
</div>
""", unsafe_allow_html=True)

# Mensaje tras escanear LOT (cantidad 0): "Ahora ingresa la cantidad"
if st.session_state.get("mo_show_lot_hint"):
    st.info(
        "✅ **LOT escaneado.** Ahora ingresa la **cantidad del sticker** y pulsa **Registrar**."
    )
    del st.session_state["mo_show_lot_hint"]
# Mensaje tras Lookup exitoso
if st.session_state.get("mo_show_lookup_success"):
    st.success("Lot information retrieved successfully.")
    source_info = st.session_state.get("mo_lookup_source")
    if source_info:
        st.caption(f"ℹ️ Fuente: {source_info}")
        # Si la fuente NO es la impresora y el usuario esperaba cantidad de la impresora, mostrar ayuda
        if "Impresora" not in source_info:
            st.info(
                "💡 **Nota:** La cantidad viene de otra fuente. Si el sticker muestra una cantidad diferente, "
                "configura la ruta del historial de la impresora en **.streamlit/secrets.toml** con "
                "**weightlabelprinter_history_path** (ver expander abajo)."
            )
        del st.session_state["mo_lookup_source"]
    del st.session_state["mo_show_lookup_success"]

# Contenedor tipo "Lot Processing Form" (card)
with st.container():
    st.markdown("#### Lot Processing Form")
    st.caption("Introduce el código de lote (o escanéalo) para recuperar información y procesar cantidades.")

    with st.form("mo_record_form", clear_on_submit=False):
        col_lot, col_btn = st.columns([3, 1])
        with col_lot:
            lot_code = st.text_input(
                "LOT Number *",
                placeholder="Ej: L28553",
                help="Código del LOT que aparece en el sticker (o escanéalo). Escanea y pulsa Enter para cargar cantidad y unidad automáticamente.",
                key="mo_lot_code",
                autocomplete="off",
                label_visibility="visible",
            )
        with col_btn:
            st.write("")  # align with input
            lookup_clicked = st.form_submit_button("Lookup", type="secondary")
        # Sin value= para evitar conflicto con session state (Lookup rellena mo_quantity/mo_uom)
        quantity = st.number_input(
            "Cantidad del sticker *",
            min_value=0.0,
            step=0.1,
            format="%.2f",
            help="La cantidad que dice el sticker (ej: 13 si dice '13 bag (40 pcs)'). Se rellena al hacer Lookup.",
            key="mo_quantity",
        )
        uom = st.text_input(
            "Unidad (opcional)",
            placeholder="Ej: bag, pcs, kg",
            help="Unidad si aplica (bag, pcs, kg, etc.). Se rellena al hacer Lookup.",
            key="mo_uom",
            autocomplete="off",
        )
        submitted = st.form_submit_button("Registrar", type="primary")

# Script para escáner: foco en LOT al cargar. Enter en LOT envía el form (Lookup). Enter en Cantidad no envía.
st.markdown("""
<script>
(function() {
  function focusLotInput() {
    var inputs = document.querySelectorAll('input[placeholder*="L28553"]');
    if (inputs.length) { inputs[0].focus(); return true; }
    var firstText = document.querySelector('form input[type="text"]');
    if (firstText) { firstText.focus(); return true; }
    return false;
  }
  function run() {
    if (!focusLotInput()) setTimeout(run, 200);
  }
  setTimeout(run, 300);
  document.addEventListener('keydown', function(e) {
    if (e.key !== 'Enter') return;
    var t = e.target;
    if (!t || !t.matches('input')) return;
    var numInput = document.querySelector('form input[type="number"]');
    var isQuantity = numInput && t === numInput;
    if (isQuantity) {
      e.preventDefault();
    }
  }, true);
})();
</script>
""", unsafe_allow_html=True)

# Lookup: al escanear lot y pulsar Enter (o clic en Lookup) se rellenan cantidad y unidad desde el MO
if lookup_clicked:
    if not (lot_code and str(lot_code).strip()):
        st.error("Ingresa el LOT Number para hacer Lookup.")
    else:
        with st.spinner("Buscando información del lote..."):
            # 1) Cantidad de la impresora (Total Entries / Total Weight) — prioridad sobre expected_output
            printer_q, printer_u = get_label_printer_quantity(lot_code.strip())
            # 2) Buscar MO en MRPEasy (unidad y fallback expected_output)
            ok, mo_data, msg = MOLookup().find_mo_by_lot_code(lot_code.strip())
            source_used = None
            if printer_q is not None and printer_q > 0:
                source_used = f"Impresora de etiquetas ({printer_q} {printer_u or ''})"
        if ok and mo_data:
            # Prioridad: impresora > DB > lote MRPEasy > expected_output del MO (no usar MO primero)
            u = (mo_data.get("expected_output_unit") or "").strip()
            if printer_q is not None and printer_q > 0:
                q = printer_q
                u = (printer_u or "").strip() or u
                if not source_used:
                    source_used = f"Impresora de etiquetas ({q} {u or ''})"
            else:
                q = None
            # 2) Total Entries en nuestra base (suma por lote) si no vino de la impresora
            if q is None or (isinstance(q, (int, float)) and q == 0):
                try:
                    db = DatabaseManager()
                    rows = db.fetch_all(
                        "SELECT quantity, uom FROM erp_mo_to_import WHERE lot_code = %s",
                        (lot_code.strip(),),
                    )
                    if rows:
                        total_entries = sum(float(r.get("quantity") or 0) for r in rows)
                        if total_entries > 0:
                            q = total_entries
                            if not source_used:
                                source_used = f"Base de datos (Total Entries: {total_entries})"
                        if not u and rows[0].get("uom"):
                            u = (rows[0].get("uom") or "").strip()
                except Exception:
                    pass
            # 3) Si aun no hay cantidad, usar la del lote en MRPEasy (produced/received)
            if q is None or (isinstance(q, (int, float)) and q == 0):
                try:
                    api = APIManager()
                    lot_data = api.get_single_lot(lot_code.strip())
                    if lot_data:
                        for key in ("quantity", "received", "qty", "produced", "actual_quantity", "output_quantity"):
                            if key in lot_data and lot_data[key] is not None:
                                try:
                                    q = float(lot_data[key])
                                    if not source_used:
                                        source_used = f"MRPEasy (lote: {q})"
                                    break
                                except (TypeError, ValueError):
                                    pass
                        if not u and lot_data.get("unit"):
                            u = (lot_data.get("unit") or "").strip()
                except Exception:
                    pass
            # 4) Ultimo recurso: cantidad esperada del MO (suele ser 1)
            if (q is None or (isinstance(q, (int, float)) and q == 0)) and mo_data.get("expected_output"):
                q = mo_data.get("expected_output")
                if not source_used:
                    source_used = f"MRPEasy (MO expected: {q})"
            # Guardar fuente usada para debug
            if source_used:
                st.session_state["mo_lookup_source"] = source_used
            # Código de lote tal como está en MRPeasy (ej. L33126) para guardar en BD
            if mo_data.get("lot_code"):
                st.session_state["mo_canonical_lot_code"] = mo_data["lot_code"]
            # No modificar mo_quantity/mo_uom aquí (widgets ya creados). Guardar en claves auxiliares y rerun.
            if q is not None:
                st.session_state["mo_preserved_quantity"] = float(q)
            if u:
                st.session_state["mo_preserved_uom_lookup"] = u
            st.session_state["mo_show_lookup_success"] = True
            st.rerun()
        else:
            # No MO found: try fallback sources with normalized lot code (L-prefix) to pre-fill
            lot_trim = lot_code.strip()
            if not lot_trim.upper().startswith("L"):
                alt_code = "L" + lot_trim
            else:
                alt_code = lot_trim[1:] if len(lot_trim) > 1 else lot_trim
            q, u, canonical_lot = None, None, None
            source_used = None
            # Try printer (both forms)
            for code in (lot_trim, alt_code):
                pq, pu = get_label_printer_quantity(code)
                if pq is not None and pq > 0:
                    q, u = pq, pu or ""
                    source_used = "impresora de etiquetas"
                    canonical_lot = code if code.upper().startswith("L") else ("L" + code)
                    break
            # Try DB (both forms)
            if (q is None or q == 0) and not source_used:
                try:
                    db = DatabaseManager()
                    for code in (lot_trim, alt_code):
                        rows = db.fetch_all(
                            "SELECT quantity, uom FROM erp_mo_to_import WHERE lot_code = %s",
                            (code,),
                        )
                        if rows:
                            total_entries = sum(float(r.get("quantity") or 0) for r in rows)
                            if total_entries > 0:
                                q = total_entries
                                u = (rows[0].get("uom") or "").strip() if rows[0].get("uom") else ""
                                source_used = "base de datos"
                                canonical_lot = code if code.upper().startswith("L") else ("L" + code)
                                break
                except Exception:
                    pass
            # Try MRPeasy lot API (both forms)
            if (q is None or q == 0) and not source_used:
                try:
                    api = APIManager()
                    for code in (lot_trim, alt_code):
                        lot_data = api.get_single_lot(code)
                        if lot_data:
                            for key in ("quantity", "received", "qty", "produced", "actual_quantity", "output_quantity"):
                                if key in lot_data and lot_data[key] is not None:
                                    try:
                                        q = float(lot_data[key])
                                        u = (lot_data.get("unit") or "").strip()
                                        source_used = "MRPEasy (lote)"
                                        canonical_lot = code if str(code).upper().startswith("L") else ("L" + code)
                                        break
                                    except (TypeError, ValueError):
                                        pass
                            if q is not None:
                                break
                except Exception:
                    pass
            if q is not None and (not isinstance(q, (int, float)) or q > 0):
                if canonical_lot:
                    st.session_state["mo_canonical_lot_code"] = canonical_lot
                if q is not None:
                    st.session_state["mo_preserved_quantity"] = float(q)
                if u:
                    st.session_state["mo_preserved_uom_lookup"] = u
                st.session_state["mo_show_lookup_success"] = True
                st.info(f"No se encontró MO en MRPeasy para este lote. Se obtuvo cantidad **{q}** {u or ''} desde **{source_used}**. Revisa los valores y pulsa **Registrar** si es correcto.")
                st.rerun()
            else:
                st.error(f"No se encontró información para el lote **{lot_trim}**. Introduce cantidad y unidad manualmente y pulsa **Registrar**.")

if submitted:
    if not (lot_code and str(lot_code).strip()):
        st.error("Ingresa el LOT Number.")
    elif not quantity or quantity <= 0:
        # Escáner suele enviar Enter después del LOT → form se envía con cantidad 0.
        # Guardamos LOT en clave auxiliar (no podemos tocar mo_lot_code tras crear el widget).
        lot_trim = lot_code.strip()
        st.session_state["mo_preserved_lot"] = lot_trim
        st.session_state["mo_preserved_uom"] = (uom and str(uom).strip()) or ""
        st.rerun()
    else:
        # Use canonical lot code (e.g. L33126) if set by fallback lookup; otherwise form value
        lot = (st.session_state.pop("mo_canonical_lot_code", None) or lot_code).strip()
        # La cantidad que se guarda y se envía a MRPEasy es exactamente la de "Cantidad del sticker"
        qty = float(quantity)
        uom_val = uom.strip() if (uom and str(uom).strip()) else None

        # 1) Siempre guardar en la base (misma tabla que usa ERP Close MO)
        with st.spinner("Guardando en la base de datos..."):
            saved = insert_production_quantity(
                lot_code=lot,
                quantity=qty,
                uom=uom_val,
                user_operations="MO Record Insert",
            )

        if not saved:
            st.error("No se pudo guardar en la base de datos. Revisa los logs.")
        else:
            # ID del registro recién insertado (para marcar processed_at tras cerrar el MO)
            inserted_id = _get_last_inserted_id_for_lot(lot)

            # 2) Actualizar MRPEasy (cantidad + intento de poner estado Done por API — nuestro "cerrar MO" interno)
            with st.spinner(f"Actualizando MO en MRPEasy con cantidad {qty}..."):
                workflow = ProductionWorkflow()
                success, result_data, message = workflow.process_production_completion(
                    lot_code=lot,
                    produced_quantity=qty,  # Exactamente el valor de "Cantidad del sticker"
                    uom=uom_val,
                    item_code=None,
                )

            # ¿Nuestro intento por API puso ya el estado a Done?
            status_set_done_via_api = bool(result_data and (result_data.get("mo_update") or {}).get("status_set_done"))

            # 3) Si la API no aceptó Done, intentar cerrar con el servicio externo (ERP Close MO)
            server_url = secrets.get("mrpeasy-could-run-po-automation-service-url") or secrets.get("mrpeasy_cloud_run_po_automation_service_url") or ""
            close_success, close_message = status_set_done_via_api, ("MO cerrado (estado Done)." if status_set_done_via_api else None)
            if status_set_done_via_api and inserted_id is not None:
                _mark_order_processed(inserted_id)
            elif server_url and not _is_service_url_invalid(server_url):
                with st.spinner("Cerrando MO en MRPEasy (estado Done)..."):
                    close_success, close_message = _close_mo_via_service(server_url, lot, qty)
                if close_success and inserted_id is not None:
                    _mark_order_processed(inserted_id)

            # Guardar mensajes de éxito, limpiar formulario y rerun para dejar listo el siguiente escaneo
            st.session_state["mo_success_messages"] = {
                "db_ok": True,
                "workflow_success": success,
                "workflow_message": message,
                "result_data": result_data,
                "lot": lot,
                "uom_val": uom_val,
                "close_mo_success": close_success,
                "close_mo_message": close_message,
            }
            st.session_state["mo_clear_form_after_success"] = True
            st.rerun()

# Mostrar mensajes de éxito del procesamiento anterior (una vez) y dejar formulario limpio
if "mo_success_messages" in st.session_state:
    sm = st.session_state["mo_success_messages"]
    st.success("✅ Registro guardado en la base de datos.")
    st.balloons()
    if sm.get("close_mo_success"):
        st.success(f"✅ **Estado en MRPEasy:** {sm.get('close_mo_message', 'MO cerrado (Done).')}")
    elif sm.get("close_mo_message") is not None:
        st.warning(
            f"⚠️ **Las cantidades se guardaron, pero el estado no se cambió a Done.**\n\n"
            f"{sm['close_mo_message']}\n\n"
            "**Para que el MO pase de «Not booked» a Done:** (1) Configura en **.streamlit/secrets.toml** la clave "
            "**mrpeasy-could-run-po-automation-service-url** con la URL **del servicio** que usa ERP Close MO "
            "(ej. `https://tu-servicio.run.app`), **no** la página web de MRPEasy. (2) O marca el MO como Done manualmente en MRPEasy. "
            "(3) O procesa este registro desde **ERP Close MO** cuando el servicio esté bien configurado."
        )
    if sm.get("workflow_success"):
        st.success(f"✅ {sm['workflow_message']}")
        result_data = sm.get("result_data")
        if result_data:
            mo_update = result_data.get("mo_update", {})
            qty_sent = mo_update.get("actual_quantity", "N/A")
            uom_val = sm.get("uom_val") or ""
            st.caption(f"En MRPEasy se actualizó la cantidad **{qty_sent}** {uom_val} (el valor de **Cantidad del sticker**).")
            mo_lookup = result_data.get("mo_lookup", {})
            st.markdown("### 📊 Detalles del MO")
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**MO:** {mo_lookup.get('mo_number', 'N/A')}")
                st.write(f"**Item:** {mo_lookup.get('item_code', 'N/A')}")
            with col2:
                st.write(f"**Cantidad actual:** {qty_sent} {uom_val}")
            summary_pdf = result_data.get("summary_pdf")
            if summary_pdf:
                lot = sm.get("lot", "")
                st.download_button(
                    label="📥 Descargar resumen (PDF)",
                    data=summary_pdf.getvalue(),
                    file_name=f"production_summary_{lot}.pdf",
                    mime="application/pdf",
                )
    else:
        err = sm.get("workflow_message", "")
        st.warning(
            f"**No se pudo actualizar MRPEasy:** {err}"
        )
        st.info(
            "El registro **sí está guardado** en la base de datos. Si en MRPEasy no cambió nada, suele ser porque: "
            "**(1)** No se encontró un MO con ese lote (el lote debe estar en **Target lots** del MO en MRPEasy), o "
            "**(2)** la API rechazó la actualización. Puedes procesar esta fila desde **ERP Close MO** o revisar en MRPEasy que el lote **" + (sm.get("lot", "") or "") + "** esté vinculado a un MO."
        )
    del st.session_state["mo_success_messages"]

st.divider()

# Impresora de etiquetas (Lookup)
with st.expander("🏷️ Cantidad desde impresora de etiquetas (WeightLabelPrinter)"):
    st.caption(
        "Al hacer **Lookup**, la cantidad se obtiene primero de **data/production/label_printer_history.json** "
        "(Total Weight o Total Entries por lote). Si no hay dato para el lote, se intenta MySQL (erp_lot_label_print) y demás fuentes."
    )
    # Verificar configuración: MySQL (erp_lot_label_print), .db, JSON
    try:
        from shared.weightlabelprinter_helper import (
            _get_label_printer_db_path,
            _get_label_printer_history_path,
            _get_label_printer_mysql_config,
        )
        mysql_cfg = _get_label_printer_mysql_config()
        if mysql_cfg:
            st.success(f"✅ Se leerá la cantidad desde **MySQL** (base `{mysql_cfg.get('database', '')}`, tabla erp_lot_label_print).")
        db_path = _get_label_printer_db_path()
        if db_path:
            if os.path.isfile(db_path):
                st.success(f"✅ Base de datos de la impresora: `{db_path}` (Total Weight se lee de aquí)")
            else:
                st.warning(f"⚠️ Archivo no encontrado: `{db_path}`")
        else:
            # Comprobar si el fallback (fava-touchscreen/dist) encontró algo
            try:
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                code_dir = os.path.dirname(project_root)
                dist_dir = os.path.join(code_dir, "fava-touchscreen", "dist")
                if os.path.isdir(dist_dir):
                    db_files = [n for n in os.listdir(dist_dir) if n.endswith((".db", ".sqlite", ".sqlite3"))]
                    if db_files:
                        st.success(f"✅ Se usa la base de datos en **code/fava-touchscreen/dist**: `{db_files[0]}`")
                    else:
                        st.warning(
                            "**Por eso la cantidad puede salir 1 en vez de 26:** no hay archivo .db en `fava-touchscreen/dist`. "
                            "Para que el Lookup traiga el Total # of Entries (26) de Weight Label Printer: "
                            "**(1)** Copia el .db de la app Weight Label Printer (misma carpeta del .exe o donde lo guarde) a "
                            "**code/fava-touchscreen/dist/** o a **data/production/** de este proyecto; "
                            "**(2)** o en **secrets.toml** descomenta **weightlabelprinter_db_path** y pon la ruta real del .db."
                        )
                else:
                    st.warning("**Si el Lookup no trae la cantidad de la impresora:** la app Weight Label Printer guarda en su propia ruta. En **.streamlit/secrets.toml** añade la ruta a su .db o JSON (ver comentarios al final del archivo) y reinicia.")
                    st.code('weightlabelprinter_db_path = "C:/ruta/donde/WeightLabelPrinter/guarda/su.archivo.db"', language="toml")
            except Exception:
                st.info("Para usar la base de datos de WeightLabelPrinter.exe, configura **weightlabelprinter_db_path** en **.streamlit/secrets.toml** apuntando a la carpeta **code/fava-touchscreen/dist** (o la ruta donde esté el .db).")
        history_path = _get_label_printer_history_path()
        if history_path and not db_path:
            if os.path.isfile(history_path):
                st.success(f"✅ Archivo configurado: `{history_path}`")
                try:
                    import json
                    with open(history_path, "r", encoding="utf-8") as f:
                        data = json.load(f)
                    if isinstance(data, list):
                        st.caption(f"📊 {len(data)} entradas en el historial")
                except Exception as e:
                    st.warning(f"⚠️ No se pudo leer el archivo: {e}")
            else:
                st.warning(f"⚠️ Archivo no encontrado: `{history_path}`")
        elif not db_path:
            st.info(
                "ℹ️ **Opcional:** Para usar un JSON en vez de MySQL, configura "
                "**weightlabelprinter_history_path** (en secrets.toml) o la variable de entorno **WEIGHTLABELPRINTER_HISTORY_PATH**."
            )
    except Exception:
        pass
    default_json_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "production", "label_printer_history.json")
    if os.path.isfile(default_json_path):
        st.success(f"✅ Se usa el JSON por defecto: **data/production/label_printer_history.json** (Total Weight por lote)")
    else:
        st.caption("Puedes crear **data/production/label_printer_history.json** con el formato de abajo; se usará automáticamente (prioridad sobre la DB).")
    st.markdown("**Formato esperado del JSON** (igual que el historial de HistorySidebar / `controller.get_print_history`):")
    st.markdown("Lista de entradas por impresión. Cada objeto con **lot** o **lot_code**, y según el tipo:")
    st.markdown("- **Total Weight** (ej. 116 kg): entradas con **weight**, **uom**; sin **container_type**. Se suma el peso.")
    st.markdown("- **Total Entries** (ej. 2 bag): entradas con **container_type**. Se cuenta el número.")
    st.code('''[
  { "lot": "L33122", "weight": 50.5, "uom": "kg", "voided_at": null },
  { "lot": "L33122", "weight": 65.5, "uom": "kg", "voided_at": null }
]''', language="json")
    st.caption("O formato simple: objetos con \"quantity\" y \"uom\"; se usa la entrada más reciente.")

# Mostrar dónde se guarda la información
with st.expander("📂 Ver base de datos (dónde se guarda la información)"):
    try:
        from shared.mysql_backend import is_mysql_available
        use_mysql = is_mysql_available()
    except Exception:
        use_mysql = False
    if use_mysql:
        st.success("**Base de datos:** MySQL (configurado en secrets). Ideal para 30–40 MO/día.")
        st.caption("La tabla **erp_mo_to_import** está en tu servidor MySQL. La usa **ERP Close MO**.")
    else:
        db_path = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "data", "production", "erp_mo_to_import.json")
        st.markdown("**Ubicación:** archivo JSON (MySQL no configurado o no disponible).")
        st.code(db_path, language=None)
        st.caption("Para usar MySQL, configura mysql_* en `.streamlit/secrets.toml` e instala: `pip install pymysql`.")
    try:
        db = DatabaseManager()
        rows = db.fetch_all(
            "SELECT id, lot_code, quantity, uom, user_operations, inserted_at, processed_at, failed_code FROM erp_mo_to_import ORDER BY inserted_at DESC LIMIT 50"
        )
        if rows:
            display_data = []
            for r in rows:
                display_data.append({
                    "id": r.get("id"),
                    "lot_code": r.get("lot_code"),
                    "quantity": r.get("quantity"),
                    "uom": r.get("uom") or "",
                    "user_operations": (r.get("user_operations") or "")[:20],
                    "inserted_at": str(r.get("inserted_at", ""))[:19] if r.get("inserted_at") else "",
                    "processed_at": "Sí" if r.get("processed_at") else "No",
                    "failed_code": "Sí" if r.get("failed_code") else "",
                })
            st.dataframe(display_data, use_container_width=True, hide_index=True)
            st.caption(f"Últimos {len(display_data)} registros. Los que tienen processed_at = No aparecen en ERP Close MO como pendientes.")
        else:
            st.info("Aún no hay registros en la base de datos.")
    except Exception as e:
        st.warning(f"No se pudo cargar la vista: {e}")

st.markdown("""
**Resumen:** Igual que MORecordInsert.exe: registras LOT + cantidad → se guarda en la base y se cierra el MO en MRPEasy automáticamente.
""")
