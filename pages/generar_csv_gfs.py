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
    # Examples (uncomment and adjust as needed):
    # 'Item Number': 'SKU',
    # 'Description': 'Product Name',
    # 'Ordered Qty': 'Quantity',
    # 'Delivery Date': 'Delivery Date',
    # 'PO Number': PO_COLUMN_NAME,
}

# ============================================================================
# HELPER FUNCTIONS
# ============================================================================

def get_gsheets_manager():
    """Gets or initializes the GSheetsManager"""
    if 'gsheets_manager' not in st.session_state:
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
        if not creds_path:
            raise ValueError("GOOGLE_CREDENTIALS_PATH not configured in secrets")
        
        # Verify that the credentials file exists and is accessible
        if not os.path.isabs(creds_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            raise FileNotFoundError(f"Credentials file not found: {creds_path}")
        
        if not os.access(creds_path, os.R_OK):
            raise PermissionError(
                f"You don't have permission to read the credentials file: {creds_path}\n"
                f"Check file permissions or run the application with appropriate permissions."
            )
        
        try:
            gsheets_manager = GSheetsManager(credentials_path=creds_path)
            gsheets_manager.authenticate()
            st.session_state.gsheets_manager = gsheets_manager
        except PermissionError as e:
            raise PermissionError(
                f"Permission error accessing credentials: {str(e)}\n"
                f"Verify that the file {creds_path} is accessible."
            )
        except Exception as e:
            raise Exception(f"Error authenticating with Google Sheets: {str(e)}")
    
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
            f"❌ Could not find the Google Sheet.\n\n"
            f"**Possible causes:**\n"
            f"1. The Google Sheet is not shared with the service account\n"
            f"2. The sheet URL is incorrect\n"
            f"3. You don't have permission to access the sheet\n\n"
            f"**Solution:**\n"
            f"- Share the Google Sheet with: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
            f"- Verify that the URL is correct: {PO_SHEET_URL}"
        )
        return None, error_msg
    
    except gspread.exceptions.WorksheetNotFound:
        error_msg = (
            f"❌ Worksheet '{PO_WORKSHEET_NAME}' not found in the Google Sheet.\n\n"
            f"**Solution:**\n"
            f"- Verify that the worksheet name is exactly: `{PO_WORKSHEET_NAME}`\n"
            f"- Or update `PO_WORKSHEET_NAME` in `.streamlit/secrets.toml` with the correct name"
        )
        return None, error_msg
    
    except gspread.exceptions.APIError as e:
        error_code = getattr(e, 'response', {}).get('status', 'Unknown')
        if error_code == 403:
            error_msg = (
                f"❌ Permission error (403): You don't have access to the Google Sheet.\n\n"
                f"**Solution:**\n"
                f"- Share the Google Sheet with: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
                f"- Make sure to give 'Editor' or 'Viewer' permissions"
            )
        else:
            error_msg = (
                f"❌ Google Sheets API error (Code: {error_code})\n\n"
                f"**Details:** {str(e)}\n\n"
                f"**Solution:**\n"
                f"- Check your internet connection\n"
                f"- Try again in a few moments"
            )
        return None, error_msg
    
    except PermissionError as e:
        error_msg = (
            f"❌ Permission error accessing files or resources.\n\n"
            f"**Details:** {str(e)}\n\n"
            f"**Possible causes:**\n"
            f"1. You don't have permission to read the credentials file\n"
            f"2. The credentials file is locked by another process\n"
            f"3. File system permission issues\n\n"
            f"**Solution:**\n"
            f"- Verify that the file `credentials/starship-431114-129e01fe3c06.json` is accessible\n"
            f"- Make sure you have read permissions in the `credentials/` folder\n"
            f"- If you're on Windows, verify that the file is not open in another program\n"
            f"- Try running the application with administrator permissions if necessary"
        )
        return None, error_msg
    
    except FileNotFoundError as e:
        error_msg = (
            f"❌ File not found.\n\n"
            f"**Details:** {str(e)}\n\n"
            f"**Solution:**\n"
            f"- Verify that the credentials file exists in the configured path\n"
            f"- Check the `GOOGLE_CREDENTIALS_PATH` configuration in `.streamlit/secrets.toml`"
        )
        return None, error_msg
    
    except ValueError as e:
        if "Not authenticated" in str(e):
            error_msg = (
                f"❌ Authentication error with Google Sheets.\n\n"
                f"**Solution:**\n"
                f"- Verify that `GOOGLE_CREDENTIALS_PATH` is configured correctly\n"
                f"- Verify that the credentials file exists and is valid"
            )
        else:
            error_msg = f"❌ Configuration error: {str(e)}"
        return None, error_msg
    
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        # If the error already has a detailed message (contains ❌), use it directly
        if "❌" in error_message:
            return None, error_message
        
        # If it's a generic error, provide additional context
        error_msg = (
            f"❌ Unexpected error searching for PO: {error_type}\n\n"
            f"**Details:** {error_message}\n\n"
            f"**Possible causes:**\n"
            f"- Connection problem with Google Sheets\n"
            f"- The sheet is not shared correctly\n"
            f"- Configuration error\n\n"
            f"**Solution:**\n"
            f"- Verify that the Google Sheet is shared with the service account\n"
            f"- Check the configuration in `.streamlit/secrets.toml`\n"
            f"- Check your internet connection"
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
        st.error("⚠️ **Required Configuration**")
        st.markdown("**The following values must be configured in `.streamlit/secrets.toml`:**")
        for issue in config_issues:
            st.markdown(f"- `{issue}`")
        st.markdown("---")
    
    if config_warnings:
        with st.expander("ℹ️ Optional Configurations", expanded=False):
            st.markdown("**The following configurations are optional (have default values):**")
            for warning in config_warnings:
                st.markdown(f"- `{warning}`")

with config_status_col2:
    if not config_issues:
        st.success("✅ Configuration OK")
    else:
        st.warning("⚠️ Incomplete Configuration")

# Configuration Help Section
if config_issues or st.button("📋 View Configuration Guide", key="show_config_help"):
    with st.expander("📋 Configuration Guide - `.streamlit/secrets.toml`", expanded=bool(config_issues)):
        st.markdown("### 🔧 Required Configuration")
        
        st.markdown("**1. Google Sheets Configuration**")
        st.code("""# URL of your Google Sheet "PO"
PO_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
PO_WORKSHEET_NAME = "PO"  # Optional, default: "PO"
PO_COLUMN_NAME = "PO_Number"  # Optional, default: "PO_Number"
""", language="toml")
        
        st.markdown("**2. Google Credentials**")
        st.code("""# Path to your Google Service Account credentials
GOOGLE_CREDENTIALS_PATH = "credentials/your-credentials.json"
""", language="toml")
        
        st.markdown("**3. CSV Template (Optional)**")
        st.code("""# Path to the CSV template file
GFS_TEMPLATE_CSV_PATH = "csv_template_french-v3.csv"  # Optional
""", language="toml")
        
        st.markdown("---")
        
        st.markdown("### 📝 Complete Configuration Example")
        st.code("""# Google Credentials Configuration
GOOGLE_CREDENTIALS_PATH = "credentials/starship-431114-129e01fe3c06.json"

# PO Sheet Configuration (for generar_csv_gfs.py)
PO_SHEET_URL = "https://docs.google.com/spreadsheets/d/YOUR_SHEET_ID"
PO_WORKSHEET_NAME = "PO"
PO_COLUMN_NAME = "PO_Number"
GFS_TEMPLATE_CSV_PATH = "csv_template_french-v3.csv"
""", language="toml")
        
        st.markdown("---")
        
        st.markdown("### ⚠️ Important Notes")
        st.markdown("""
        - **Share Google Sheet**: Make sure to share your Google Sheet with the service account email
        - **CSV Template Location**: The template file must be in the project root or specify the full path
        - **Template Format**: The CSV must have headers (first row with column names)
        """)
        
        if config_issues:
            st.markdown("---")
            st.info("💡 **After configuring the required values, reload the page for the changes to take effect.**")

# Only show the main workflow if configuration is complete
if config_issues:
    st.divider()
    st.info("🔒 **Please complete the configuration before using this tool.**")

# ============================================================================
# MAIN WORKFLOW (only if configuration is complete)
# ============================================================================
if not config_issues:
    st.divider()
    
    # Input form
    st.subheader("🔹 Step 1: Enter PO Number")

    po_input = st.text_input(
        "PO Number",
        placeholder="Example: PO02337",
        help="Enter the Purchase Order number you want to process"
    )

    col1, col2 = st.columns([1, 4])

    with col1:
        generate_button = st.button(
            "🔍 Generate CSV", 
            type="primary", 
            use_container_width=True,
            disabled=not PO_SHEET_URL
        )

    # Show step status
    if st.session_state.po_data:
        st.success("✅ Step 1 completed: PO found")
    else:
        st.info("⏳ Step 1: Waiting for you to enter the PO number")

    # Process when button is pressed
    if generate_button:
        if not po_input or not po_input.strip():
            st.error("❌ Please enter a PO number")
        else:
            with st.spinner("🔍 Searching for PO in Google Sheets..."):
                # Search for the PO
                po_data, error = get_po_data(po_input.strip())
                
                if error:
                    if "PO not found" in error:
                        st.error(f"❌ {error}")
                    elif "Duplicate PO" in error:
                        st.error(f"❌ {error}")
                    else:
                        # Show long errors with better formatting
                        st.error("❌ Error searching for PO")
                        st.markdown(error)
                else:
                    st.session_state.po_data = po_data
                    
                    # Load the template
                    with st.spinner("📄 Loading CSV template..."):
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
                                with st.spinner("⚙️ Generating CSV..."):
                                    filled_df, fill_error = fill_template(po_data, template_df)
                                    
                                    if fill_error:
                                        st.error(f"❌ {fill_error}")
                                    else:
                                        st.session_state.csv_generated = filled_df
                                        st.success(f"✅ CSV generated successfully for PO {po_input.strip()}")

    # Show PO data if available
    if st.session_state.po_data:
        st.divider()
        st.subheader("🔹 Step 2: PO Data Found")
        
        # Show data in table format
        po_df = pd.DataFrame([st.session_state.po_data])
        st.dataframe(po_df.T, use_container_width=True, height=300)
        
        with st.expander("📋 View PO Data (JSON)", expanded=False):
            st.json(st.session_state.po_data)
        
        if st.session_state.csv_generated is not None:
            st.success("✅ Step 2 completed: CSV generated successfully")
        else:
            st.info("⏳ Step 2: Reviewing PO data...")
    else:
        st.divider()
        st.subheader("🔹 Step 2: PO Data")
        st.info("⏳ Waiting for PO to be searched...")

    # Show download button if CSV is generated
    if st.session_state.csv_generated is not None:
        st.divider()
        st.subheader("🔹 Step 3: Download CSV")
        
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
            label="📥 Download CSV for GFS",
            data=csv_string,
            file_name=filename,
            mime="text/csv",
            type="primary",
            use_container_width=True
        )
        
        # Show CSV preview
        with st.expander("👁️ CSV Preview", expanded=False):
            st.dataframe(st.session_state.csv_generated, use_container_width=True)
        
        st.success("✅ Step 3: CSV ready to download")
    else:
        st.divider()
        st.subheader("🔹 Step 3: Download CSV")
        st.info("⏳ Waiting for CSV to be generated...")

    # Help information
    st.divider()
    with st.expander("ℹ️ Information and Usage Guide"):
        st.markdown("""
        ### 📖 Workflow:
        
        1. **Enter the PO number** (example: PO02337)
        2. The application searches for the PO in Google Sheets
        3. The CSV template is loaded
        4. PO data is filled into the template
        5. Download the final CSV ready for GFS
        
        ### 🔄 Data Mapping:
        
        - Data mapping is done automatically by matching template columns with PO fields
        - If you need specific mappings, edit the `COLUMN_MAPPING` dictionary in the code
        - The CSV is generated 100% in memory, without writing temporary files
        
        ### 📝 Notes:
        
        - **Template CSV**: Must have headers (first row with column names)
        - **PO Search**: The search is case-insensitive (does not distinguish uppercase/lowercase)
        - **Validation**: The system validates that the PO exists before generating the CSV
        """)

