"""
MO Record Insert - Registro de cantidad del sticker → MRPEasy

Flujo:
1. Producción imprime el sticker con la cantidad real (ej: "13 bag (40 pcs)").
2. Tú tomas ese papel y entras aquí el LOT y la cantidad que dice el sticker.
3. Al hacer clic en "Registrar", el sistema envía la cantidad real al MO en MRPEasy.

Nota: La API de MRPEasy no permite cambiar el estado por API. Si el MO sigue
"Not booked" / "Not scheduled", hay que marcar como Done/Received en MRPEasy a mano.
"""

import streamlit as st
import sys
import os

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.production_workflow import ProductionWorkflow

st.set_page_config(
    page_title="MO Record Insert - Lot y cantidad del sticker",
    page_icon="📋",
    layout="centered",
)

st.title("📋 MO Record Insert")
st.caption("Ingresa el LOT y la cantidad del sticker. Se envía la cantidad real al MO en MRPEasy.")
st.info(
    "**Importante:** La API de MRPEasy no permite cambiar el estado del MO. "
    "Si después de registrar el MO sigue en «Not booked» o «Not scheduled», "
    "marca el MO como **Done** o **Received** manualmente en MRPEasy."
)

with st.form("mo_record_form", clear_on_submit=True):
    lot_code = st.text_input(
        "LOT Number *",
        placeholder="Ej: L28553",
        help="Código del LOT que aparece en el sticker.",
    )
    quantity = st.number_input(
        "Cantidad del sticker *",
        min_value=0.0,
        step=0.1,
        format="%.2f",
        help="La cantidad que dice el sticker (ej: 13 si dice '13 bag (40 pcs)').",
    )
    uom = st.text_input(
        "Unidad (opcional)",
        placeholder="Ej: bag, pcs, kg",
        help="Unidad si aplica (bag, pcs, kg, etc.).",
    )
    submitted = st.form_submit_button("Registrar cantidad en MRPEasy")

if submitted:
    if not (lot_code and str(lot_code).strip()):
        st.error("Ingresa el LOT Number.")
    elif not quantity or quantity <= 0:
        st.error("Ingresa una cantidad mayor a 0.")
    else:
        with st.spinner("Procesando producción y actualizando MRPEasy..."):
            # Use the same ProductionWorkflow that works in erp_close_mo.py
            workflow = ProductionWorkflow()
            success, result_data, message = workflow.process_production_completion(
                lot_code=lot_code.strip(),
                produced_quantity=float(quantity),
                uom=uom.strip() if (uom and str(uom).strip()) else None,
                item_code=None  # Will be retrieved from MO lookup
            )
        if success:
            st.success(f"✅ {message}")
            st.balloons()
            # Show additional details if available
            if result_data:
                with st.expander("📊 Detalles del procesamiento"):
                    st.json(result_data)
        else:
            st.error(f"❌ {message}")

st.divider()
st.markdown("""
**Flujo:** Sticker generado → ingresas aquí LOT + cantidad → se envía la cantidad al MO en MRPEasy.  
Si el estado no cambia a Done, márcalo manualmente en MRPEasy (la API no permite cambiar estado).
""")
