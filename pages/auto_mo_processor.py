"""
Auto MO Processor Page

This page provides an interface to automatically process Manufacturing Orders
when production quantities are entered in WeightLabelPrinter.spec.

The system:
1. Monitors erp_mo_to_import for new entries with LOT codes and quantities
2. Finds the associated MO using the LOT code
3. Updates the MO with actual produced quantity
4. Changes status from "not booked" to "Done"
5. Closes the Manufacturing Order
"""

import streamlit as st
import time
from datetime import datetime
import sys
import os

# Add the project root to Python path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.auto_mo_processor import AutoMOProcessor
from shared.database_manager import DatabaseManager

# Page configuration
st.set_page_config(
    page_title="Auto MO Processor - WeightLabelPrinter Integration",
    page_icon="🤖",
    layout="wide"
)

# Initialize processor
@st.cache_resource
def get_processor():
    return AutoMOProcessor()

processor = get_processor()

# Title and description
st.title("🤖 Auto MO Processor")
st.markdown("""
Este sistema procesa automáticamente las Órdenes de Manufactura (MOs) cuando se ingresa 
la cantidad real producida en WeightLabelPrinter.spec.

**Flujo automático:**
1. Cuando se ingresa una cantidad real para un LOT en WeightLabelPrinter.spec
2. El sistema busca el MO asociado usando el código LOT
3. Actualiza el MO con la cantidad real producida
4. Cambia el estado de "not booked" a "Done"
5. Cierra la Orden de Manufactura
""")

# Sidebar controls
with st.sidebar:
    st.header("⚙️ Configuración")
    
    auto_process = st.checkbox(
        "🔄 Procesamiento Automático",
        value=False,
        help="Activa el procesamiento automático continuo de nuevas entradas"
    )
    
    refresh_interval = st.number_input(
        "Intervalo de actualización (segundos)",
        min_value=5,
        max_value=300,
        value=30,
        step=5,
        help="Cada cuántos segundos verificar nuevas entradas"
    )
    
    st.divider()
    
    st.header("📊 Estadísticas")
    
    # Fetch pending count
    try:
        db = DatabaseManager()
        query = """
        SELECT COUNT(*) as count
        FROM erp_mo_to_import 
        WHERE processed_at IS NULL 
        AND (failed_code IS NULL OR failed_code = '')
        """
        result = db.fetch_one(query)
        pending_count = result.get('count', 0) if result else 0
        
        st.metric("Entradas Pendientes", pending_count)
    except Exception as e:
        st.error(f"Error obteniendo estadísticas: {str(e)}")
        pending_count = 0

# Main content area
col1, col2 = st.columns([2, 1])

with col1:
    st.header("📋 Procesamiento Manual")
    
    # Manual process button
    if st.button("🚀 Procesar Todas las Entradas Pendientes", type="primary", use_container_width=True):
        with st.spinner("Procesando entradas pendientes..."):
            results = processor.process_all_pending()
            
            if results['total'] == 0:
                st.info("✅ No hay entradas pendientes para procesar")
            else:
                st.success(
                    f"✅ Procesamiento completado: "
                    f"{results['processed']} procesadas, "
                    f"{results['failed']} fallidas de {results['total']} totales"
                )
                
                # Show detailed results
                if results['results']:
                    st.subheader("📊 Resultados Detallados")
                    for result in results['results']:
                        if result['success']:
                            st.success(f"✅ {result['lot_code']}: {result['message']}")
                        else:
                            st.error(f"❌ {result['lot_code']}: {result['message']}")
                
                st.rerun()
    
    st.divider()
    
    # Manual entry form
    st.subheader("➕ Procesar Entrada Manual")
    st.markdown("Ingresa manualmente un LOT y cantidad para procesar inmediatamente")
    
    with st.form("manual_entry_form", clear_on_submit=True):
        col_lot, col_qty = st.columns(2)
        
        with col_lot:
            lot_code_input = st.text_input(
                "Código LOT *",
                placeholder="Ej: L28553",
                help="Ingresa el código del LOT"
            )
        
        with col_qty:
            quantity_input = st.number_input(
                "Cantidad Producida *",
                min_value=0.0,
                step=0.1,
                format="%.2f",
                help="Ingresa la cantidad real producida"
            )
        
        uom_input = st.text_input(
            "Unidad de Medida (UOM)",
            placeholder="Ej: kg, lb, gr",
            help="Opcional: Unidad de medida"
        )
        
        submitted = st.form_submit_button("🚀 Procesar", type="primary", use_container_width=True)
        
        if submitted:
            if not lot_code_input or not lot_code_input.strip():
                st.error("❌ Por favor ingresa un código LOT")
            elif not quantity_input or quantity_input <= 0:
                st.error("❌ Por favor ingresa una cantidad válida mayor a 0")
            else:
                with st.spinner(f"Procesando LOT {lot_code_input}..."):
                    success, message = processor.process_single_entry_by_lot(
                        lot_code=lot_code_input.strip(),
                        quantity=float(quantity_input),
                        uom=uom_input.strip() if uom_input else None
                    )
                    
                    if success:
                        st.success(f"✅ {message}")
                        st.balloons()
                    else:
                        st.error(f"❌ {message}")

with col2:
    st.header("📈 Estado del Sistema")
    
    # Show recent activity
    st.subheader("🔄 Actividad Reciente")
    
    # Fetch recent processed entries
    try:
        db = DatabaseManager()
        query = """
        SELECT lot_code, quantity, uom, processed_at
        FROM erp_mo_to_import 
        WHERE processed_at IS NOT NULL
        ORDER BY processed_at DESC
        LIMIT 10
        """
        recent = db.fetch_all(query)
        
        if recent:
            for entry in recent:
                processed_time = entry.get('processed_at', 'N/A')
                lot_code = entry.get('lot_code', 'N/A')
                quantity = entry.get('quantity', 0)
                uom = entry.get('uom', '')
                
                st.markdown(f"**{lot_code}**")
                st.caption(f"{quantity} {uom} - {processed_time}")
                st.divider()
        else:
            st.info("No hay actividad reciente")
    except Exception as e:
        st.error(f"Error obteniendo actividad: {str(e)}")
    
    # Auto-processing status
    if auto_process:
        st.success("🟢 Procesamiento automático activo")
        
        # Auto-processing loop (simplified - in production, use a background task)
        if 'last_auto_process' not in st.session_state:
            st.session_state.last_auto_process = datetime.now()
        
        time_since_last = (datetime.now() - st.session_state.last_auto_process).total_seconds()
        
        if time_since_last >= refresh_interval:
            with st.spinner("Procesando automáticamente..."):
                results = processor.process_all_pending()
                st.session_state.last_auto_process = datetime.now()
                
                if results['total'] > 0:
                    st.info(
                        f"Procesadas {results['processed']} entradas automáticamente"
                    )
                    time.sleep(1)
                    st.rerun()
    else:
        st.info("⚪ Procesamiento automático inactivo")

# Footer with instructions
st.divider()
st.markdown("""
### 📝 Instrucciones de Uso

**Para integración con WeightLabelPrinter.spec:**

1. **Procesamiento Automático**: Activa el checkbox "Procesamiento Automático" 
   en la barra lateral. El sistema verificará nuevas entradas cada X segundos.

2. **Procesamiento Manual**: Usa el botón "Procesar Todas las Entradas Pendientes" 
   para procesar todas las entradas en la base de datos `erp_mo_to_import`.

3. **Entrada Manual**: Si necesitas procesar un LOT específico inmediatamente, 
   usa el formulario "Procesar Entrada Manual".

**Nota**: Asegúrate de que WeightLabelPrinter.spec esté insertando las entradas 
en la tabla `erp_mo_to_import` con los campos:
- `lot_code`: Código del LOT (ej: L28553)
- `quantity`: Cantidad real producida
- `uom`: Unidad de medida (opcional)
""")
