import streamlit as st
import pandas as pd
import io
import gspread
from shared.gsheets_manager import GSheetsManager
from config import secrets
import os

# ============================================================================
# CONFIGURATION
# ============================================================================
# URL of the Google Sheet "PO" - ADJUST AS NEEDED
PO_SHEET_URL = secrets.get('PO_SHEET_URL', '')  # Configure in secrets.toml
PO_WORKSHEET_NAME = secrets.get('PO_WORKSHEET_NAME', 'PO')  # Name of the worksheet within the spreadsheet

# Name of the column that contains the PO number - ADJUST to the actual column name
PO_COLUMN_NAME = secrets.get('PO_COLUMN_NAME', 'PO_Number')  # Can be configured in secrets.toml

# Template CSV path - can be configured in secrets.toml or use default
TEMPLATE_CSV_PATH = secrets.get('GFS_TEMPLATE_CSV_PATH', 'csv_template_french-v3.csv')

# ============================================================================
# COLUMN MAPPING (Optional - for specific mappings)
# ============================================================================
# If you need specific mappings between template columns and PO fields,
# add a dictionary here. If empty, automatic mapping is used.
# Format: {'Template Column': 'PO Field'}
COLUMN_MAPPING = {
    # Ejemplos (descomentar y ajustar según necesidad):
    # 'Item Number': 'SKU',
    # 'Description': 'Product Name',
    # 'Ordered Qty': 'Quantity',
    # 'Delivery Date': 'Delivery Date',
    # 'PO Number': PO_COLUMN_NAME,
}

# ============================================================================
# FUNCIONES AUXILIARES
# ============================================================================

def get_gsheets_manager():
    """Gets or initializes the GSheetsManager"""
    if 'gsheets_manager' not in st.session_state:
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
        if not creds_path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH not configured in secrets")
        
        # Verificar que el archivo de credenciales exista y sea accesible
        if not os.path.isabs(creds_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Archivo de credenciales no encontrado: {creds_path}")
        
        if not os.access(creds_path, os.R_OK):
            raise PermissionError(
                f"No tienes permisos para leer el archivo de credenciales: {creds_path}\n"
                f"Verifica los permisos del archivo o ejecuta la aplicación con los permisos adecuados."
            )
        
        try:
            gsheets_manager = GSheetsManager(credentials_path=creds_path)
            gsheets_manager.authenticate()
            st.session_state.gsheets_manager = gsheets_manager
        except PermissionError as e:
            raise PermissionError(
                f"Error de permisos al acceder a las credenciales: {str(e)}\n"
                f"Verifica que el archivo {creds_path} sea accesible."
            )
        except Exception as e:
            raise Exception(f"Error al autenticar con Google Sheets: {str(e)}")
    
    return st.session_state.gsheets_manager


def get_po_data(po_number):
    """
    Searches for the PO in Google Sheets and returns the data from the found row.
    
    Args:
        po_number: PO number to search for (e.g.: "PO02337")
    
    Returns:
        dict: Dictionary with PO data or None if not found
        str: Error message if there are problems
    """
    try:
        gsheets_manager = get_gsheets_manager()
        
        # Open the "PO" sheet
        worksheet = gsheets_manager.open_sheet_by_url(PO_SHEET_URL, PO_WORKSHEET_NAME)
        
        # Get all records as DataFrame
        df = gsheets_manager.get_as_dataframe(worksheet)
        
        if df.empty:
            return None, "The sheet is empty"
        
        # Verify that the PO column exists
        if PO_COLUMN_NAME not in df.columns:
            return None, f"Column '{PO_COLUMN_NAME}' does not exist in the sheet. Available columns: {', '.join(df.columns)}"
        
        # Search for the PO (case-insensitive and without spaces)
        po_number_clean = str(po_number).strip().upper()
        df[PO_COLUMN_NAME] = df[PO_COLUMN_NAME].astype(str).str.strip().str.upper()
        
        matches = df[df[PO_COLUMN_NAME] == po_number_clean]
        
        if len(matches) == 0:
            return None, "PO not found"
        elif len(matches) > 1:
            return None, "Duplicate PO"
        else:
            # Return the first row as a dictionary
            po_data = matches.iloc[0].to_dict()
            return po_data, None
    
    except gspread.exceptions.SpreadsheetNotFound:
        error_msg = (
            f"❌ No se pudo encontrar el Google Sheet.\n\n"
            f"**Posibles causas:**\n"
            f"1. El Google Sheet no está compartido con la cuenta de servicio\n"
            f"2. La URL del sheet es incorrecta\n"
            f"3. No tienes permisos para acceder al sheet\n\n"
            f"**Solución:**\n"
            f"- Comparte el Google Sheet con: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
            f"- Verifica que la URL sea correcta: {PO_SHEET_URL}"
        )
        return None, error_msg
    
    except gspread.exceptions.WorksheetNotFound:
        error_msg = (
            f"❌ No se encontró la hoja '{PO_WORKSHEET_NAME}' en el Google Sheet.\n\n"
            f"**Solución:**\n"
            f"- Verifica que el nombre de la hoja sea exactamente: `{PO_WORKSHEET_NAME}`\n"
            f"- O actualiza `PO_WORKSHEET_NAME` en `.streamlit/secrets.toml` con el nombre correcto"
        )
        return None, error_msg
    
    except gspread.exceptions.APIError as e:
        error_code = getattr(e, 'response', {}).get('status', 'Unknown')
        if error_code == 403:
            error_msg = (
                f"❌ Error de permisos (403): No tienes acceso al Google Sheet.\n\n"
                f"**Solución:**\n"
                f"- Comparte el Google Sheet con: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
                f"- Asegúrate de dar permisos de 'Editor' o 'Lector'"
            )
        else:
            error_msg = (
                f"❌ Error de API de Google Sheets (Código: {error_code})\n\n"
                f"**Detalles:** {str(e)}\n\n"
                f"**Solución:**\n"
                f"- Verifica tu conexión a internet\n"
                f"- Intenta nuevamente en unos momentos"
            )
        return None, error_msg
    
    except PermissionError as e:
        error_msg = (
            f"❌ Error de permisos al acceder a los archivos o recursos.\n\n"
            f"**Detalles:** {str(e)}\n\n"
            f"**Posibles causas:**\n"
            f"1. No tienes permisos para leer el archivo de credenciales\n"
            f"2. El archivo de credenciales está bloqueado por otro proceso\n"
            f"3. Problemas de permisos del sistema de archivos\n\n"
            f"**Solución:**\n"
            f"- Verifica que el archivo `credentials/starship-431114-129e01fe3c06.json` sea accesible\n"
            f"- Asegúrate de tener permisos de lectura en la carpeta `credentials/`\n"
            f"- Si estás en Windows, verifica que el archivo no esté abierto en otro programa\n"
            f"- Intenta ejecutar la aplicación con permisos de administrador si es necesario"
        )
        return None, error_msg
    
    except FileNotFoundError as e:
        error_msg = (
            f"❌ Archivo no encontrado.\n\n"
            f"**Detalles:** {str(e)}\n\n"
            f"**Solución:**\n"
            f"- Verifica que el archivo de credenciales exista en la ruta configurada\n"
            f"- Revisa la configuración de `GOOGLE_CREDENTIALS_PATH` en `.streamlit/secrets.toml`"
        )
        return None, error_msg
    
    except ValueError as e:
        if "Not authenticated" in str(e):
            error_msg = (
                f"❌ Error de autenticación con Google Sheets.\n\n"
                f"**Solución:**\n"
                f"- Verifica que `GOOGLE_CREDENTIALS_PATH` esté configurado correctamente\n"
                f"- Verifica que el archivo de credenciales exista y sea válido"
            )
        else:
            error_msg = f"❌ Error de configuración: {str(e)}"
        return None, error_msg
    
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        # Si el error ya viene con un mensaje detallado (contiene ❌), usarlo directamente
        if "❌" in error_message:
            return None, error_message
        
        # Si es un error genérico, proporcionar contexto adicional
        error_msg = (
            f"❌ Error inesperado al buscar el PO: {error_type}\n\n"
            f"**Detalles:** {error_message}\n\n"
            f"**Posibles causas:**\n"
            f"- Problema de conexión con Google Sheets\n"
            f"- El sheet no está compartido correctamente\n"
            f"- Error en la configuración\n\n"
            f"**Solución:**\n"
            f"- Verifica que el Google Sheet esté compartido con la cuenta de servicio\n"
            f"- Revisa la configuración en `.streamlit/secrets.toml`\n"
            f"- Verifica tu conexión a internet"
        )
        return None, error_msg


def find_template_file():
    """
    Finds the template CSV file by checking multiple locations.
    
    Returns:
        str: Path to the template file, or None if not found
    """
    # List of possible locations to check
    possible_paths = []
    
    # 1. The configured path (absolute or relative)
    possible_paths.append(TEMPLATE_CSV_PATH)
    
    # 2. Relative to project root
    if not os.path.isabs(TEMPLATE_CSV_PATH):
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        possible_paths.append(os.path.join(project_root, TEMPLATE_CSV_PATH))
    
    # 3. In the pages directory
    pages_dir = os.path.dirname(os.path.abspath(__file__))
    possible_paths.append(os.path.join(pages_dir, TEMPLATE_CSV_PATH))
    
    # Check each path
    for path in possible_paths:
        if os.path.exists(path) and os.path.isfile(path):
            return path
    
    return None


def load_template():
    """
    Loads the CSV template and returns an empty DataFrame with the same structure.
    
    Returns:
        pd.DataFrame: DataFrame with the template structure
        str: Error message if there are problems
    """
    try:
        # Find the template file
        template_path = find_template_file()
        
        if not template_path:
            error_msg = (
                f"Template file '{TEMPLATE_CSV_PATH}' not found.\n\n"
                f"**Please do one of the following:**\n"
                f"1. Place the CSV template file in the project root directory\n"
                f"2. Configure 'GFS_TEMPLATE_CSV_PATH' in `.streamlit/secrets.toml` with the full path\n"
                f"3. Make sure the file exists and the path is correct"
            )
            return None, error_msg
        
        # Load the template
        template_df = pd.read_csv(template_path)
        
        if template_df.empty:
            return None, f"Template file '{template_path}' is empty or has no columns."
        
        if len(template_df.columns) == 0:
            return None, f"Template file '{template_path}' has no columns defined."
        
        # Create an empty DataFrame with the same structure
        empty_df = pd.DataFrame(columns=template_df.columns)
        
        return empty_df, None
    
    except pd.errors.EmptyDataError:
        return None, f"Template file is empty or invalid."
    except pd.errors.ParserError as e:
        return None, f"Error parsing template CSV: {str(e)}. Please check the file format."
    except Exception as e:
        return None, f"Error loading template: {str(e)}"


def fill_template(po_data, template_df):
    """
    Fills the template with PO data.
    
    Args:
        po_data: Dictionary with PO data
        template_df: Template DataFrame (empty)
    
    Returns:
        pd.DataFrame: DataFrame filled with PO data
        str: Error message if there are problems
    """
    try:
        # Create a copy of the template
        filled_df = template_df.copy()
        
        # Create a new empty row
        new_row = {col: '' for col in template_df.columns}
        
        # ====================================================================
        # DATA MAPPING
        # ====================================================================
        # First apply specific mappings if defined
        if COLUMN_MAPPING:
            for template_col, po_field in COLUMN_MAPPING.items():
                if template_col in new_row:
                    value = po_data.get(po_field, '')
                    if pd.isna(value):
                        new_row[template_col] = ''
                    else:
                        new_row[template_col] = str(value)
        
        # Then apply automatic mapping for unmapped columns
        for col in template_df.columns:
            # If already specifically mapped, skip it
            if COLUMN_MAPPING and col in COLUMN_MAPPING:
                continue
            
            # Search for exact matches first
            if col in po_data:
                value = po_data[col]
                # Convert NaN to empty string
                if pd.isna(value):
                    new_row[col] = ''
                else:
                    new_row[col] = str(value)
            # Search for case-insensitive matches
            else:
                col_lower = col.lower().strip()
                for po_key, po_value in po_data.items():
                    if po_key and str(po_key).lower().strip() == col_lower:
                        if pd.isna(po_value):
                            new_row[col] = ''
                        else:
                            new_row[col] = str(po_value)
                        break
        
        # Add the row to the DataFrame
        filled_df = pd.concat([filled_df, pd.DataFrame([new_row])], ignore_index=True)
        
        return filled_df, None
    
    except Exception as e:
        return None, f"Error filling template: {str(e)}"


def validate_required_data(po_data, template_df):
    """
    Validates that required data exists in the PO.
    
    Args:
        po_data: Dictionary with PO data
        template_df: Template DataFrame
    
    Returns:
        str: Error message if data is missing, None if everything is okay
    """
    # List of columns considered mandatory (adjust as needed)
    required_columns = []  # Add mandatory columns here if necessary
    
    if not required_columns:
        return None  # No specific validations
    
    missing = []
    for col in required_columns:
        if col in template_df.columns:
            # Verify if the data exists in po_data
            found = False
            for key, value in po_data.items():
                if key and str(key).lower().strip() == col.lower().strip():
                    if value and str(value).strip():
                        found = True
                        break
            
            if not found:
                missing.append(col)
    
    if missing:
        return f"Missing required data: {', '.join(missing)}"
    
    return None


# ============================================================================
# STREAMLIT INTERFACE
# ============================================================================

st.set_page_config(page_title="Generate CSV for GFS", layout="wide")

st.title("📄 Generate CSV for GFS")

st.markdown("""
This tool allows you to generate a CSV file ready to upload to GFS from a PO number.
""")

# Show process steps
st.divider()
st.subheader("📋 Process Steps")

steps_col1, steps_col2, steps_col3 = st.columns(3)

with steps_col1:
    st.markdown("""
    **Step 1: Enter PO**
    
    Enter the Purchase Order number you want to process.
    """)

with steps_col2:
    st.markdown("""
    **Step 2: Review Data**
    
    Verify that the PO data is correct.
    """)

with steps_col3:
    st.markdown("""
    **Step 3: Download CSV**
    
    Download the CSV file ready to upload to GFS.
    """)

st.divider()

# Inicializar session state
if 'csv_generated' not in st.session_state:
    st.session_state.csv_generated = None
if 'po_data' not in st.session_state:
    st.session_state.po_data = None

# ============================================================================
# CONFIGURATION CHECK
# ============================================================================
config_status_col1, config_status_col2 = st.columns([3, 1])

with config_status_col1:
    # Verify configuration
    config_issues = []
    config_warnings = []
    
    if not PO_SHEET_URL:
        config_issues.append("PO_SHEET_URL")
    if not secrets.get('GOOGLE_CREDENTIALS_PATH'):
        config_issues.append("GOOGLE_CREDENTIALS_PATH")
    
    # Check optional configurations
    if not secrets.get('PO_WORKSHEET_NAME'):
        config_warnings.append("PO_WORKSHEET_NAME (using default: 'PO')")
    if not secrets.get('PO_COLUMN_NAME'):
        config_warnings.append("PO_COLUMN_NAME (using default: 'PO_Number')")
    if not secrets.get('GFS_TEMPLATE_CSV_PATH'):
        config_warnings.append("GFS_TEMPLATE_CSV_PATH (using default: 'csv_template_french-v3.csv')")
    
    if config_issues:
        st.error("⚠️ **Configuración Requerida**")
        st.markdown("**Los siguientes valores deben configurarse en `.streamlit/secrets.toml`:**")
        for issue in config_issues:
            st.markdown(f"- `{issue}`")
        st.markdown("---")
    
    if config_warnings:
        with st.expander("ℹ️ Configuraciones Opcionales", expanded=False):
            st.markdown("**Las siguientes configuraciones son opcionales (tienen valores por defecto):**")
            for warning in config_warnings:
                st.markdown(f"- `{warning}`")

with config_status_col2:
    if not config_issues:
        st.success("✅ Configuración OK")
    else:
        st.warning("⚠️ Configuración Incompleta")

# Configuration Help Section
if config_issues or st.button("📋 Ver Guía de Configuración", key="show_config_help"):
    with st.expander("📋 Guía de Configuración - `.streamlit/secrets.toml`", expanded=bool(config_issues)):
        st.markdown("### 🔧 Configuración Requerida")
        
        st.markdown("**1. Google Sheets Configuration**")
        st.code("""# URL de tu Google Sheet "PO"
PO_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
PO_WORKSHEET_NAME = "PO"  # Opcional, default: "PO"
PO_COLUMN_NAME = "PO_Number"  # Opcional, default: "PO_Number"
""", language="toml")
        
        st.markdown("**2. Google Credentials**")
        st.code("""# Ruta a tus credenciales de Google Service Account
GOOGLE_CREDENTIALS_PATH = "credentials/your-credentials.json"
""", language="toml")
        
        st.markdown("**3. CSV Template (Opcional)**")
        st.code("""# Ruta al archivo template CSV
GFS_TEMPLATE_CSV_PATH = "csv_template_french-v3.csv"  # Opcional
""", language="toml")
        
        st.markdown("---")
        
        st.markdown("### 📝 Ejemplo Completo de Configuración")
        st.code("""# Google Credentials Configuration
GOOGLE_CREDENTIALS_PATH = "credentials/starship-431114-129e01fe3c06.json"

# PO Sheet Configuration (for generar_csv_gfs.py)
PO_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
PO_WORKSHEET_NAME = "PO"
PO_COLUMN_NAME = "PO_Number"
GFS_TEMPLATE_CSV_PATH = "csv_template_french-v3.csv"
""", language="toml")
        
        st.markdown("---")
        
        st.markdown("### ⚠️ Notas Importantes")
        st.markdown("""
        - **Compartir Google Sheet**: Asegúrate de compartir tu Google Sheet con el email de la cuenta de servicio
        - **Ubicación del Template CSV**: El archivo template debe estar en la raíz del proyecto o especifica la ruta completa
        - **Formato del Template**: El CSV debe tener headers (primera fila con nombres de columnas)
        """)
        
        if config_issues:
            st.markdown("---")
            st.info("💡 **Después de configurar los valores requeridos, recarga la página para que los cambios surtan efecto.**")

# Only show the main workflow if configuration is complete
if config_issues:
    st.divider()
    st.info("🔒 **Por favor completa la configuración antes de usar esta herramienta.**")

# ============================================================================
# MAIN WORKFLOW (only if configuration is complete)
# ============================================================================
if not config_issues:
    st.divider()
    
    # Input form
    st.subheader("🔹 Paso 1: Ingresa el Número de PO")

    po_input = st.text_input(
        "Número de PO",
        placeholder="Ejemplo: PO02337",
        help="Ingresa el número de Purchase Order que quieres procesar"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        generate_button = st.button(
            "🔍 Generar CSV", 
            type="primary", 
            use_container_width=True,
            disabled=not PO_SHEET_URL
        )

    # Show step status
    if st.session_state.po_data:
        st.success("✅ Paso 1 completado: PO encontrado")
    else:
        st.info("⏳ Paso 1: Esperando que ingreses el número de PO")

    # Process when button is pressed
    if generate_button:
        if not po_input or not po_input.strip():
            st.error("❌ Por favor ingresa un número de PO")
        else:
            with st.spinner("🔍 Buscando PO en Google Sheets..."):
                # Search for the PO
                po_data, error = get_po_data(po_input.strip())
                
                if error:
                    if "PO not found" in error:
                        st.error(f"❌ {error}")
                    elif "Duplicate PO" in error:
                        st.error(f"❌ {error}")
                    else:
                        # Mostrar errores largos con mejor formato
                        st.error("❌ Error al buscar el PO")
                        st.markdown(error)
                else:
                    st.session_state.po_data = po_data
                    
                    # Load the template
                    with st.spinner("📄 Cargando template CSV..."):
                        template_df, template_error = load_template()
                        
                        if template_error:
                            st.error(f"❌ {template_error}")
                            with st.expander("🔍 Template File Help"):
                                st.markdown("""
                                ### Template CSV Requirements:
                                
                                The template CSV file should:
                                - Be a valid CSV file with headers
                                - Contain the column structure you want in the final GFS CSV
                                - Be placed in the project root or configured path
                                
                                ### Example Template Structure:
                                
                                The template should have columns that match the data you want to export.
                                Common columns might include:
                                - Item Number / SKU
                                - Description
                                - Quantity
                                - Unit Price
                                - Delivery Date
                                - PO Number
                                
                                The system will automatically map PO data to template columns by matching column names.
                                """)
                        else:
                            # Show template columns info
                            st.info(f"✅ Template loaded successfully with {len(template_df.columns)} columns: {', '.join(template_df.columns.tolist())}")
                            # Validate required data
                            validation_error = validate_required_data(po_data, template_df)
                            
                            if validation_error:
                                st.error(f"❌ {validation_error}")
                            else:
                                # Fill the template
                                with st.spinner("⚙️ Generando CSV..."):
                                    filled_df, fill_error = fill_template(po_data, template_df)
                                    
                                    if fill_error:
                                        st.error(f"❌ {fill_error}")
                                    else:
                                        st.session_state.csv_generated = filled_df
                                        st.success(f"✅ CSV generado exitosamente para PO {po_input.strip()}")

    # Show PO data if available
    if st.session_state.po_data:
        st.divider()
        st.subheader("🔹 Paso 2: Datos del PO Encontrados")
        
        # Show data in table format
        po_df = pd.DataFrame([st.session_state.po_data])
        st.dataframe(po_df.T, use_container_width=True, height=300)
        
        with st.expander("📋 Ver Datos del PO (JSON)", expanded=False):
            st.json(st.session_state.po_data)
        
        if st.session_state.csv_generated is not None:
            st.success("✅ Paso 2 completado: CSV generado exitosamente")
        else:
            st.info("⏳ Paso 2: Revisando datos del PO...")
    else:
        st.divider()
        st.subheader("🔹 Paso 2: Datos del PO")
        st.info("⏳ Esperando que se busque el PO...")

    # Show download button if CSV is generated
    if st.session_state.csv_generated is not None:
        st.divider()
        st.subheader("🔹 Paso 3: Descargar CSV")
        
        # Convert DataFrame to CSV in memory
        csv_buffer = io.StringIO()
        st.session_state.csv_generated.to_csv(csv_buffer, index=False)
        csv_string = csv_buffer.getvalue()
        
        # File name
        if st.session_state.po_data and PO_COLUMN_NAME in st.session_state.po_data:
            po_number = str(st.session_state.po_data.get(PO_COLUMN_NAME, 'PO')).strip()
        else:
            po_number = po_input.strip() if po_input else "PO"
        filename = f"GFS_{po_number}.csv"
        
        st.download_button(
            label="📥 Descargar CSV para GFS",
            data=csv_string,
            file_name=filename,
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
        
        # Show CSV preview
        with st.expander("👁️ Vista Previa del CSV", expanded=False):
            st.dataframe(st.session_state.csv_generated, use_container_width=True)
        
        st.success("✅ Paso 3: CSV listo para descargar")
    else:
        st.divider()
        st.subheader("🔹 Paso 3: Descargar CSV")
        st.info("⏳ Esperando que se genere el CSV...")

    # Help information
    st.divider()
    with st.expander("ℹ️ Información y Guía de Uso"):
        st.markdown("""
        ### 📖 Flujo de Trabajo:
        
        1. **Ingresa el número de PO** (ejemplo: PO02337)
        2. La aplicación busca el PO en Google Sheets
        3. Se carga el template CSV
        4. Los datos del PO se llenan en el template
        5. Descarga el CSV final listo para GFS
        
        ### 🔄 Mapeo de Datos:
        
        - El mapeo de datos se hace automáticamente buscando coincidencias entre las columnas del template y los campos del PO
        - Si necesitas mapeos específicos, edita el diccionario `COLUMN_MAPPING` en el código
        - El CSV se genera 100% en memoria, sin escribir archivos temporales
        
        ### 📝 Notas:
        
        - **Template CSV**: Debe tener headers (primera fila con nombres de columnas)
        - **Búsqueda de PO**: La búsqueda es case-insensitive (no distingue mayúsculas/minúsculas)
        - **Validación**: El sistema valida que exista el PO antes de generar el CSV
        """)

