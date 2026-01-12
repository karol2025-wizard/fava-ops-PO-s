"""
Process Lot Manually - Update MRPeasy

Esta página permite procesar un lote escaneado manualmente
cuando no se actualizó automáticamente en MRPeasy.
"""

import streamlit as st
import sys
import os
from datetime import datetime

# Add project root to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from shared.production_workflow import ProductionWorkflow
from shared.mo_lookup import MOLookup
from shared.json_storage import JSONStorage

# Page configuration
st.set_page_config(
    page_title="Procesar Lote Manualmente",
    page_icon="🔧",
    layout="wide"
)

st.title("🔧 Procesar Lote Manualmente")
st.markdown("Procesa un lote escaneado y actualiza MRPeasy cuando no se actualizó automáticamente")

# Sidebar info
with st.sidebar:
    st.header("ℹ️ Información")
    st.info("""
    Esta herramienta permite:
    - Buscar el MO asociado a un lote
    - Actualizar MRPeasy con la cantidad producida
    - Cambiar el status del MO a "Done"
    - Ver el registro de producción guardado
    """)
    
    st.markdown("---")
    st.header("🔧 Diagnóstico")
    
    if st.button("🧪 Probar Conexión MRPeasy"):
        with st.spinner("Probando conexión..."):
            try:
                from shared.api_manager import APIManager
                api = APIManager()
                
                # Try to fetch a small number of MOs
                st.write("Intentando obtener Manufacturing Orders...")
                mos = api.fetch_manufacturing_orders()
                
                if mos is None:
                    st.error("❌ La API retornó None. Verifica credenciales y conexión.")
                elif isinstance(mos, list):
                    st.success(f"✅ Conexión exitosa! Se obtuvieron {len(mos)} Manufacturing Orders")
                    if len(mos) > 0:
                        st.json({"Primer MO": mos[0].get('code', 'N/A'), "Total": len(mos)})
                else:
                    st.error(f"❌ Respuesta inesperada: {type(mos)}")
            except ValueError as ve:
                st.error(f"❌ Error de API: {str(ve)}")
            except Exception as e:
                st.error(f"❌ Error: {str(e)}")
                st.exception(e)

# Initialize workflow
workflow = ProductionWorkflow()
storage = JSONStorage()
lookup = MOLookup()

# Main content
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📝 Datos del Lote")
    
    lot_code = st.text_input(
        "Código del Lote (ej: L28553)",
        help="Ingresa el código del lote que escaneaste"
    ).strip()
    
    if lot_code:
        # Try to find MO
        st.subheader("🔍 Buscando MO...")
        
        # Alternative: Try to get MO directly if we know the code (from image, L28868 -> MO06719)
        use_direct_lookup = st.checkbox(
            "Intentar búsqueda directa por código MO (si conoces el código)",
            help="Si sabes el código del MO (ej: MO06719), puedes buscarlo directamente"
        )
        
        if use_direct_lookup:
            mo_code = st.text_input("Código del MO (ej: MO06719)", help="Ingresa el código del MO directamente")
            
            if mo_code:
                from shared.api_manager import APIManager
                api = APIManager()
                
                with st.spinner(f"Buscando MO {mo_code}..."):
                    try:
                        mo_direct = api.get_manufacturing_order_by_code(mo_code)
                        
                        if mo_direct:
                            mo_id = mo_direct.get('man_ord_id')
                            detailed_mo = api.get_manufacturing_order_details(mo_id) if mo_id else None
                            
                            if detailed_mo:
                                # Check if lot code matches
                                target_lots = detailed_mo.get('target_lots', [])
                                lot_found = any(
                                    lot.get('code', '').strip().upper() == lot_code.upper()
                                    for lot in target_lots
                                )
                                
                                if lot_found:
                                    st.success("✅ MO encontrado directamente")
                                    
                                    # Create mo_data in the expected format
                                    mo_data = {
                                        'mo_number': detailed_mo.get('code', mo_code),
                                        'mo_id': mo_id,
                                        'item_code': detailed_mo.get('item_code', 'N/A'),
                                        'item_title': detailed_mo.get('item_title', 'N/A'),
                                        'status': detailed_mo.get('status', 'N/A'),
                                        'expected_output': detailed_mo.get('quantity', 0),
                                        'expected_output_unit': detailed_mo.get('unit', ''),
                                        'lot_code': lot_code
                                    }
                                    
                                    lookup_success = True
                                    lookup_message = f"MO {mo_code} encontrado directamente"
                                else:
                                    st.warning(f"⚠️ MO {mo_code} encontrado, pero el lote {lot_code} no está asociado")
                                    st.markdown(f"**Lotes en este MO:** {[l.get('code') for l in target_lots]}")
                                    mo_data = None
                                    lookup_success = False
                                    lookup_message = f"El lote {lot_code} no está en el MO {mo_code}"
                            else:
                                st.error(f"❌ No se pudieron obtener los detalles del MO {mo_code}")
                                mo_data = None
                                lookup_success = False
                                lookup_message = f"No se pudieron obtener detalles del MO {mo_code}"
                        else:
                            st.error(f"❌ MO {mo_code} no encontrado")
                            mo_data = None
                            lookup_success = False
                            lookup_message = f"MO {mo_code} no encontrado"
                            
                    except Exception as e:
                        st.error(f"❌ Error al buscar MO directamente: {str(e)}")
                        mo_data = None
                        lookup_success = False
                        lookup_message = f"Error: {str(e)}"
            else:
                lookup_success = False
                mo_data = None
                lookup_message = "Por favor ingresa un código de MO"
        else:
            # Original lookup method
            with st.spinner(f"Buscando Manufacturing Order para {lot_code}... Esto puede tardar si hay muchos MOs..."):
                try:
                    lookup_success, mo_data, lookup_message = lookup.find_mo_by_lot_code(lot_code)
                except ValueError as ve:
                    # This is likely an API error with detailed message
                    st.error(f"❌ Error de API: {str(ve)}")
                    lookup_success = False
                    mo_data = None
                    lookup_message = str(ve)
                    
                    # Show detailed troubleshooting
                    with st.expander("🔧 Solución de Problemas Detallada"):
                        if "401" in str(ve) or "Authentication" in str(ve):
                            st.error("**Problema de Autenticación**")
                            st.markdown("""
                            - Verifica que `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` sean correctos
                            - Asegúrate de que no haya espacios extra al inicio o final
                            - Verifica que las credenciales no hayan expirado
                            - Intenta regenerar las credenciales en MRPeasy
                            """)
                        elif "403" in str(ve) or "forbidden" in str(ve).lower():
                            st.error("**Problema de Permisos**")
                            st.markdown("""
                            - Tu API key no tiene permisos para leer Manufacturing Orders
                            - Contacta al administrador de MRPeasy para verificar los permisos
                            - Asegúrate de que la API key tenga acceso a Manufacturing Orders
                            """)
                        elif "429" in str(ve) or "Rate limit" in str(ve) or "Too Many Requests" in str(ve):
                            st.error("**⚠️ Rate Limit Excedido (429)**")
                            st.markdown("""
                            **El problema:** MRPeasy está limitando las solicitudes porque se están haciendo demasiadas peticiones.
                            
                            **Soluciones:**
                            - ⏰ **Espera 1-2 minutos** y vuelve a intentar
                            - 🔍 **Usa la búsqueda directa por código MO** (checkbox arriba) en lugar de buscar todos los MOs
                            - 📉 **Reduce la frecuencia** de búsquedas
                            
                            **Nota:** Obtener todos los Manufacturing Orders puede tardar varios minutos y puede activar el rate limit.
                            """)
                            st.warning("💡 **Sugerencia:** Marca el checkbox 'Intentar búsqueda directa por código MO' y usa el código MO06719 para evitar obtener todos los MOs.")
                        elif "timeout" in str(ve).lower() or "Connection" in str(ve):
                            st.error("**Problema de Conexión**")
                            st.markdown("""
                            - Verifica tu conexión a internet
                            - Verifica que no haya un firewall bloqueando la conexión
                            - Intenta nuevamente en unos momentos
                            """)
                        elif "500" in str(ve) or "server error" in str(ve).lower():
                            st.error("**Error del Servidor MRPeasy**")
                            st.markdown("""
                            - El servicio de MRPeasy puede estar temporalmente no disponible
                            - Intenta nuevamente en unos minutos
                            - Si el problema persiste, contacta al soporte de MRPeasy
                            """)
                        else:
                            st.warning("**Error Desconocido**")
                            st.code(str(ve))
                except Exception as e:
                    st.error(f"❌ Error inesperado: {str(e)}")
                    st.exception(e)
                    lookup_success = False
                    mo_data = None
                    lookup_message = f"Error: {str(e)}"
        
        if lookup_success and mo_data:
            st.success("✅ MO Encontrado")
            
            # Display MO info
            st.markdown("### Información del MO:")
            st.json({
                "MO Number": mo_data['mo_number'],
                "Item Code": mo_data['item_code'],
                "Item Title": mo_data['item_title'],
                "Expected Output": f"{mo_data['expected_output']} {mo_data['expected_output_unit']}",
                "Current Status": mo_data['status']
            })
            
            # Get produced quantity
            st.markdown("### Cantidad Producida:")
            
            # Try to get quantity from lot details
            quantity = st.number_input(
                "Cantidad Producida",
                min_value=0.0,
                step=0.1,
                value=float(mo_data.get('expected_output', 0)),
                help="Ingresa la cantidad real producida"
            )
            
            uom = st.text_input(
                "Unidad de Medida (UOM)",
                value=mo_data.get('expected_output_unit', ''),
                help="Unidad de medida (ej: tray, kg, pcs)"
            ).strip()
            
            # Process button
            if st.button("🚀 Procesar Lote y Actualizar MRPeasy", type="primary"):
                if not quantity or quantity <= 0:
                    st.error("⚠️ Por favor ingresa una cantidad válida mayor a 0")
                else:
                    with st.spinner(f"Procesando {lot_code}..."):
                        try:
                            success, result_data, message = workflow.process_production_completion(
                                lot_code=lot_code,
                                produced_quantity=quantity,
                                uom=uom if uom else None,
                                item_code=mo_data.get('item_code')
                            )
                            
                            if success:
                                st.success(f"✅ {message}")
                                
                                # Show result data
                                if result_data:
                                    with st.expander("📊 Ver Detalles del Procesamiento"):
                                        st.json({
                                            "MO Number": result_data.get('mo_update', {}).get('mo_number'),
                                            "Actual Quantity": result_data.get('mo_update', {}).get('actual_quantity'),
                                            "Status": result_data.get('mo_update', {}).get('status'),
                                            "Timestamp": result_data.get('workflow_timestamp')
                                        })
                                
                                # Show saved production record
                                st.markdown("### 📝 Registro Guardado:")
                                records = storage.get_production_records(lot=lot_code, limit=1)
                                if records:
                                    st.json(records[0])
                                
                                st.balloons()
                            else:
                                st.error(f"❌ Error: {message}")
                                st.markdown("**Por favor verifica:**")
                                st.markdown("- El código del lote es correcto")
                                st.markdown("- El MO existe en MRPeasy")
                                st.markdown("- La cantidad producida es válida")
                                st.markdown("- Tienes permisos para actualizar el MO")
                                
                        except Exception as e:
                            st.error(f"❌ Error al procesar: {str(e)}")
                            st.exception(e)
        else:
            st.error(f"❌ {lookup_message}")
            
            # Check if it's an API connection error
            if "API" in lookup_message or "connection" in lookup_message.lower() or "credentials" in lookup_message.lower():
                st.error("🔴 **Error de Conexión con MRPeasy**")
                st.markdown("**Pasos para solucionar:**")
                st.markdown("1. Verifica que `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` estén configurados en `.streamlit/secrets.toml`")
                st.markdown("2. Verifica tu conexión a internet")
                st.markdown("3. Verifica que las credenciales de API sean correctas")
                st.markdown("4. Verifica que el servicio de MRPeasy esté disponible")
                
                # Show credentials status (without revealing them)
                try:
                    from config import secrets
                    has_key = 'MRPEASY_API_KEY' in secrets and secrets.get('MRPEASY_API_KEY')
                    has_secret = 'MRPEASY_API_SECRET' in secrets and secrets.get('MRPEASY_API_SECRET')
                    
                    st.markdown("**Estado de las Credenciales:**")
                    st.markdown(f"- API Key configurada: {'✅ Sí' if has_key else '❌ No'}")
                    st.markdown(f"- API Secret configurado: {'✅ Sí' if has_secret else '❌ No'}")
                    
                    if not has_key or not has_secret:
                        st.warning("⚠️ Faltan credenciales. Por favor configura `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` en `.streamlit/secrets.toml`")
                except Exception as e:
                    st.warning(f"No se pudo verificar las credenciales: {str(e)}")
            else:
                st.markdown("**Posibles causas:**")
                st.markdown("- El código del lote no existe en MRPeasy")
                st.markdown("- No hay un MO asociado a este lote")
                st.markdown("- Hay múltiples MOs asociados (requiere supervisión)")
                st.markdown("- Problema de conexión con MRPeasy")
            
            # Alternative: Try to get MO directly by code if we know it from the image
            if lot_code == "L28868":
                st.info("💡 **Alternativa:** Basado en la información que veo, este lote está asociado al MO06719. Puedes intentar buscar el MO directamente por código.")
                st.markdown("O puedes usar la página 'ERP Close MO' para procesar este lote.")

with col2:
    st.header("📜 Registros de Producción Recientes")
    
    # Filter options
    filter_lot = st.text_input("Filtrar por Lote (opcional)", help="Deja vacío para ver todos")
    
    if st.button("🔄 Actualizar Registros"):
        st.rerun()
    
    # Get recent records
    records = storage.get_production_records(
        lot=filter_lot if filter_lot else None,
        limit=10
    )
    
    if records:
        st.markdown(f"**Últimos {len(records)} registros:**")
        
        for i, record in enumerate(records):
            with st.expander(f"📋 {record.get('lot')} - {record.get('mo')} - {record.get('timestamp')}"):
                col_a, col_b = st.columns(2)
                
                with col_a:
                    st.markdown(f"**Lote:** {record.get('lot')}")
                    st.markdown(f"**MO:** {record.get('mo')}")
                    st.markdown(f"**Status:** {record.get('status')}")
                
                with col_b:
                    st.markdown(f"**Cantidad Estimada:** {record.get('estimated_qty')}")
                    st.markdown(f"**Cantidad Real:** {record.get('actual_qty')}")
                    st.markdown(f"**Timestamp:** {record.get('timestamp')}")
                
                # Show full record
                if st.checkbox(f"Ver JSON completo", key=f"show_json_{i}"):
                    st.json(record)
    else:
        st.info("No hay registros de producción aún")
    
    # Logs section
    st.markdown("---")
    st.header("📋 Logs de Operaciones")
    
    filter_log_lot = st.text_input("Filtrar Logs por Lote (opcional)", key="filter_log")
    filter_log_mo = st.text_input("Filtrar Logs por MO (opcional)", key="filter_mo")
    
    logs = storage.get_production_logs(
        lot_code=filter_log_lot if filter_log_lot else None,
        mo_number=filter_log_mo if filter_log_mo else None,
        limit=10
    )
    
    if logs:
        for log in logs:
            status_icon = "✅" if log.get('success') else "❌"
            with st.expander(f"{status_icon} {log.get('lot_code')} - {log.get('mo_number')} - {log.get('timestamp', '')[:16]}"):
                st.markdown(f"**Lote:** {log.get('lot_code')}")
                st.markdown(f"**MO:** {log.get('mo_number')} (ID: {log.get('mo_id')})")
                st.markdown(f"**Cantidad:** {log.get('quantity')}")
                
                if log.get('status_before') and log.get('status_after'):
                    st.markdown(f"**Status:** {log.get('status_before')} → {log.get('status_after')}")
                
                if log.get('error_message'):
                    st.error(f"**Error:** {log.get('error_message')}")
                
                if st.checkbox(f"Ver JSON completo", key=f"show_log_json_{log.get('timestamp')}"):
                    st.json(log)
    else:
        st.info("No hay logs de operaciones aún")

# Footer
st.markdown("---")
st.markdown("**💡 Tip:** Si escaneaste un lote pero no se actualizó MRPeasy, usa esta herramienta para procesarlo manualmente.")

