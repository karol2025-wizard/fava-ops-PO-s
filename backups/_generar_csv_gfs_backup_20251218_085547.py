import streamlit as st
import pandas as pd
import io
from shared.api_manager import APIManager
from config import secrets
import os
from datetime import datetime
import logging
import re
import gspread
from oauth2client.service_account import ServiceAccountCredentials

# Try to import PDF parsing libraries
PDF_PARSING_AVAILABLE = False
PDF_LIBRARY = None

try:
    import pdfplumber
    PDF_PARSING_AVAILABLE = True
    PDF_LIBRARY = 'pdfplumber'
except ImportError:
    try:
        import PyPDF2
        PDF_PARSING_AVAILABLE = True
        PDF_LIBRARY = 'PyPDF2'
    except ImportError:
        PDF_PARSING_AVAILABLE = False
        PDF_LIBRARY = None

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# ============================================================================
# CONFIGURATION
# ============================================================================
# Template CSV/Excel path - can be configured in secrets.toml or will use default
# Default: media/gfs-order-template.xlsx in project root
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
default_template = os.path.join(project_root, 'media', 'gfs-order-template.xlsx')

# Check if default template exists, if not try CSV version
if not os.path.exists(default_template):
    default_template_csv = os.path.join(project_root, 'media', 'gfs-order-template.csv')
    if os.path.exists(default_template_csv):
        default_template = default_template_csv
    else:
        default_template = None

TEMPLATE_CSV_PATH = secrets.get('GFS_TEMPLATE_CSV_PATH', default_template)

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

def get_api_manager():
    """Gets or initializes the APIManager"""
    if 'api_manager' not in st.session_state:
        st.session_state.api_manager = APIManager()
    return st.session_state.api_manager


def get_gsheets_client():
    """Gets or initializes the Google Sheets client"""
    if 'gsheets_client' not in st.session_state:
        scope = [
            "https://spreadsheets.google.com/feeds",
            'https://www.googleapis.com/auth/spreadsheets',
            "https://www.googleapis.com/auth/drive.file",
            "https://www.googleapis.com/auth/drive"
        ]
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
        if not creds_path:
            logger.warning("GOOGLE_CREDENTIALS_PATH not configured in secrets")
            return None
        try:
            creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
            st.session_state.gsheets_client = gspread.authorize(creds)
        except Exception as e:
            logger.error(f"Error authenticating with Google Sheets: {str(e)}")
            return None
    return st.session_state.gsheets_client


def get_vendor_part_from_gsheets(item_code):
    """
    Searches for the vendor part number (Part #) in Google Sheets using the item_code.
    
    Args:
        item_code: The item code to search for (e.g., 'A1667')
    
    Returns:
        str: The Part # if found, empty string otherwise
    """
    # Google Sheet URL for products database
    PRODUCTS_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1PKEY_ofj9dUxuvV1v9yaR81AcOS-2ghragW_pw6_EgI'
    
    try:
        client = get_gsheets_client()
        if not client:
            return ''
        
        # Open the sheet
        sheet = client.open_by_url(PRODUCTS_SHEET_URL)
        
        # Try to get the first worksheet (or you can specify a sheet name)
        worksheet = sheet.sheet1  # or sheet.worksheet('Sheet1')
        
        # Get all records (gspread.get_all_records() returns list of dicts with column names as keys)
        records = worksheet.get_all_records()
        
        if not records:
            logger.warning("No records found in Google Sheet")
            return ''
        
        # Get headers to understand column structure (for logging)
        headers = worksheet.row_values(1)
        logger.info(f"Google Sheet headers: {headers}")
        
        # Search for the item_code in the records
        # gspread.get_all_records() returns dictionaries where keys are column names from first row
        for record in records:
            # Try multiple possible column names for item code
            record_item_code = (
                record.get('Item Code') or 
                record.get('Item') or 
                record.get('Code') or
                record.get('item_code') or
                record.get('Item #') or
                record.get('ITEM CODE') or
                ''
            )
            
            # Clean and compare item codes (case-insensitive, strip whitespace)
            if record_item_code:
                record_item_code = str(record_item_code).strip().upper()
                search_item_code = str(item_code).strip().upper()
                
                if record_item_code == search_item_code:
                    # Found the item, get the Part #
                    part_number = (
                        record.get('Part #') or 
                        record.get('Part') or 
                        record.get('part_number') or
                        record.get('Vendor Part #') or
                        record.get('Vendor Part') or
                        record.get('PART #') or
                        record.get('PART') or
                        ''
                    )
                    
                    if part_number:
                        part_number = str(part_number).strip()
                        logger.info(f"✅ Found Part # '{part_number}' in Google Sheets for item '{item_code}'")
                        return part_number
                    else:
                        logger.warning(f"Item '{item_code}' found in Google Sheets but Part # is empty")
        
        logger.warning(f"Item code '{item_code}' not found in Google Sheets")
        return ''
        
    except Exception as e:
        logger.warning(f"Error searching Google Sheets for item '{item_code}': {str(e)}")
        return ''


def format_date_for_gfs(timestamp):
    """Convert Unix timestamp to MM/DD/YYYY format for GFS"""
    if not timestamp:
        return ""
    try:
        if isinstance(timestamp, (int, float)):
            dt = datetime.fromtimestamp(timestamp)
            return dt.strftime('%m/%d/%Y')
        return str(timestamp)
    except:
        return ""


def get_po_data_from_mrpeasy(po_code):
    """
    Fetches the PO from MRPeasy API and returns the data.
    Tries multiple variations of the PO code to find a match.
    
    Args:
        po_code: PO code to search for (e.g.: "PO02680", "02680", "2695")
    
    Returns:
        tuple: (dict, str) - Dictionary with PO data or None, Error message if there are problems
    """
    try:
        api_manager = get_api_manager()
        original_code = po_code.strip()
        
        # Generate variations of the PO code to try
        variations = []
        
        # 1. Original code as-is
        variations.append(original_code)
        
        # 2. Remove "PO" prefix if present
        if original_code.upper().startswith('PO'):
            variations.append(original_code[2:].strip())
        
        # 3. Add "PO" prefix if not present
        if not original_code.upper().startswith('PO'):
            variations.append(f"PO{original_code}")
        
        # 4. Try with leading zeros (if it's a number)
        numeric_part = ''.join(filter(str.isdigit, original_code))
        if numeric_part:
            # Try with different zero padding
            for padding in [5, 6, 7]:
                padded = numeric_part.zfill(padding)
                variations.append(f"PO{padded}")
                variations.append(padded)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for var in variations:
            if var and var not in seen:
                seen.add(var)
                unique_variations.append(var)
        
        # Try each variation
        for variation in unique_variations:
            po_data = api_manager.fetch_single_purchase_order(variation)
            if po_data:
                logger.info(f"Found PO using variation: '{variation}' (original: '{original_code}')")
            return po_data, None
    
        # If none found, return error with tried variations
        tried_variations = ', '.join([f"'{v}'" for v in unique_variations[:5]])  # Show first 5
        return None, (
            f"PO not found. Searched for: '{original_code}'\n\n"
            f"**Tried variations:** {tried_variations}\n\n"
            f"**Please verify:**\n"
            f"- The PO code is correct\n"
            f"- The PO exists in MRPeasy\n"
            f"- You have access to this PO"
        )
    
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        
        error_msg = (
            f"❌ Error fetching PO from MRPeasy: {error_type}\n\n"
            f"**Details:** {error_message}\n\n"
            f"**Possible causes:**\n"
            f"- Connection problem with MRPeasy API\n"
            f"- Invalid PO code\n"
            f"- API credentials issue\n\n"
            f"**Solution:**\n"
            f"- Verify that the PO code is correct\n"
            f"- Check MRPEASY_API_KEY and MRPEASY_API_SECRET in `.streamlit/secrets.toml`\n"
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
    
    # If template path is configured, use it
    if TEMPLATE_CSV_PATH:
        # 1. The configured path (absolute or relative)
        possible_paths.append(TEMPLATE_CSV_PATH)
        
        # 2. Relative to project root
        if not os.path.isabs(TEMPLATE_CSV_PATH):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            possible_paths.append(os.path.join(project_root, TEMPLATE_CSV_PATH))
        
        # 3. In the pages directory
        pages_dir = os.path.dirname(os.path.abspath(__file__))
        possible_paths.append(os.path.join(pages_dir, TEMPLATE_CSV_PATH))
    
    # 4. Check media folder in project root (default location)
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    media_folder = os.path.join(project_root, 'media')
    if os.path.exists(media_folder):
        # Try gfs-order-template with different extensions
        for ext in ['.xlsx', '.xls', '.csv']:
            template_name = f"gfs-order-template{ext}"
            media_template = os.path.join(media_folder, template_name)
            if os.path.exists(media_template):
                possible_paths.append(media_template)
    
    # Check each path
    for path in possible_paths:
        if path and os.path.exists(path) and os.path.isfile(path):
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
        # Check if template path is configured
        if not TEMPLATE_CSV_PATH:
            error_msg = (
                f"❌ GFS Template CSV path not configured.\n\n"
                f"**Please configure the template path:**\n"
                f"1. Add `GFS_TEMPLATE_CSV_PATH` to `.streamlit/secrets.toml`\n"
                f"2. Set it to the path of your new GFS template CSV file\n"
                f"3. Example: `GFS_TEMPLATE_CSV_PATH = \"media/new_gfs_template.csv\"`\n\n"
                f"**Template Requirements:**\n"
                f"- Must be a CSV file with headers\n"
                f"- Headers should match GFS format (Item #, Case QTY, Unit Qty, etc.)\n"
                f"- The system will map PO data to these columns automatically"
            )
            return None, error_msg
        
        # Find the template file
        template_path = find_template_file()
        
        if not template_path:
            # Check media folder as fallback
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            media_folder = os.path.join(project_root, 'media')
            media_file = None
            if os.path.exists(media_folder):
                for ext in ['.xlsx', '.xls', '.csv']:
                    test_path = os.path.join(media_folder, f"gfs-order-template{ext}")
                    if os.path.exists(test_path):
                        media_file = test_path
                        break
            
            if media_file:
                template_path = media_file
            else:
                error_msg = (
                    f"❌ Template file not found.\n\n"
                    f"**Searched for:**\n"
                    f"- Configured path: `{TEMPLATE_CSV_PATH or 'Not configured'}`\n"
                    f"- Media folder: `media/gfs-order-template.xlsx` or `.csv`\n\n"
                    f"**Please do one of the following:**\n"
                    f"1. Place 'gfs-order-template.xlsx' in the 'media' folder\n"
                    f"2. Configure 'GFS_TEMPLATE_CSV_PATH' in `.streamlit/secrets.toml` with the full path\n"
                    f"3. Make sure the file exists and the path is correct"
                )
                return None, error_msg
        
        # Load the template (support both CSV and Excel)
        if template_path.endswith('.csv'):
            template_df = pd.read_csv(template_path)
        elif template_path.endswith(('.xlsx', '.xls')):
            try:
                template_df = pd.read_excel(template_path, engine='openpyxl')
            except ImportError:
                return None, (
                    "❌ Missing dependency: openpyxl\n\n"
                    "**To fix this, run:**\n"
                    "```bash\n"
                    "pip install openpyxl\n"
                    "```\n\n"
                    "Then restart the Streamlit application."
                )
        else:
            # Try CSV first, then Excel
            try:
                template_df = pd.read_csv(template_path)
            except:
                try:
                    template_df = pd.read_excel(template_path, engine='openpyxl')
                except ImportError:
                    return None, (
                        "❌ Missing dependency: openpyxl\n\n"
                        "**To fix this, run:**\n"
                        "```bash\n"
                        "pip install openpyxl\n"
                        "```\n\n"
                        "Then restart the Streamlit application."
                    )
                except Exception as e:
                    return None, f"Error reading template file: {str(e)}. Please ensure it's a valid CSV or Excel file."
        
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


def get_vendor_part_number(product, po_data=None):
    """
    Gets the vendor part number for a product, trying multiple sources.
    Priority order:
    1. Google Sheets database (using item_code to find Part #)
    2. Directly from product fields
    3. From purchase terms
    4. From custom fields
    
    Args:
        product: Dictionary with product data from PO
        po_data: Optional PO data dictionary (needed to match vendor_id in purchase terms)
    
    Returns:
        str: Vendor part number or empty string if not found
    """
    vendor_part_no = ''
    
    # FIRST: Try to get it from Google Sheets database using item_code
    item_code = product.get('item_code')
    if item_code:
        vendor_part_no = get_vendor_part_from_gsheets(item_code)
        if vendor_part_no:
            logger.info(f"Found vendor part number in Google Sheets: {vendor_part_no}")
            return vendor_part_no
    
    # SECOND: Try to get it directly from product (may not be available in API response)
    # Check multiple possible field names
    # NOTE: Do NOT use 'vendor_code' - that's the vendor's code (e.g., V00017), not the product part number
    # vendor_product_code is the correct field for the product code from vendor
    vendor_part_no = (
        product.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
        product.get('vendor_item_code') or 
        product.get('vendor_part_no') or 
        product.get('vendor_part_number') or
        ''  # Removed vendor_code - that's the vendor ID, not the product part number
    )
    
    # Log what we found
    if vendor_part_no:
        logger.info(f"Found vendor part number directly in product: {vendor_part_no}")
        return vendor_part_no
    
    # SECOND: If not found in product, try to get it from item's purchase terms
    # This is the most reliable source since the API may not include it in the PO product data
    if not vendor_part_no:
        item_code = product.get('item_code')
        if item_code:
            try:
                api_manager = get_api_manager()
                item_details = api_manager.get_item_details(item_code)
                if item_details:
                    # Check purchase terms for vendor part number
                    purchase_terms = item_details.get('purchase_terms', [])
                    if purchase_terms:
                        # Get vendor_id from PO to match the right purchase term
                        po_vendor_id = po_data.get('vendor_id') if po_data else None
                        # First, try to match by vendor_id
                        matched_by_vendor_id = False
                        if po_vendor_id:
                            for term in purchase_terms:
                                if term.get('vendor_id') == po_vendor_id:
                                    # Try multiple possible field names for vendor part number
                                    # NOTE: Do NOT use 'vendor_code' - that's the vendor's code (e.g., V00017), not the product part number
                                    # vendor_product_code is the correct field for the product code from vendor (e.g., 1493567)
                                    vendor_part_no = (
                                        term.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
                                        term.get('vendor_item_code') or
                                        term.get('vendor_part_no') or
                                        term.get('vendor_part_number') or
                                        term.get('item_code') or  # Sometimes it's just item_code
                                        term.get('code') or  # Or just code
                                        ''  # Removed vendor_code - that's the vendor ID, not the product part number
                                    )
                                    # If we got something that looks like a vendor part number, use it
                                    if vendor_part_no and str(vendor_part_no).strip():
                                        logger.info(f"Found vendor part number in purchase terms (matched by vendor_id): {vendor_part_no}")
                                        matched_by_vendor_id = True
                                        break
                        
                        # If no match by vendor_id, use first available term
                        if not matched_by_vendor_id and not vendor_part_no:
                            for term in purchase_terms:
                                # NOTE: Do NOT use 'vendor_code' - that's the vendor's code, not the product part number
                                # vendor_product_code is the correct field for the product code from vendor
                                vendor_part_no = (
                                    term.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
                                    term.get('vendor_item_code') or
                                    term.get('vendor_part_no') or
                                    term.get('vendor_part_number') or
                                    term.get('item_code') or
                                    term.get('code') or
                                    ''  # Removed vendor_code - that's the vendor ID, not the product part number
                                )
                                if vendor_part_no and str(vendor_part_no).strip():
                                    logger.info(f"Found vendor part number in purchase terms (using first available): {vendor_part_no}")
                                    break
            except Exception as e:
                logger.warning(f"Error fetching item details for {item_code}: {str(e)}")
    
    # FOURTH: If still not found, search in custom fields (custom_*)
    if not vendor_part_no:
        for key, value in product.items():
            if key.startswith('custom_') and value:
                value_str = str(value).strip()
                # Check if it looks like a vendor part number (numeric, 6-10 digits, not a timestamp)
                if value_str.isdigit() and 6 <= len(value_str) <= 10:
                    # Exclude timestamps (usually 10 digits and very large)
                    try:
                        num_value = int(value_str)
                        # Timestamps are usually > 1000000000 (year 2001+)
                        if num_value < 1000000000:
                            vendor_part_no = value_str
                            logger.info(f"Found vendor part number in custom field '{key}': {vendor_part_no}")
                            break
                    except:
                        pass
    
    return vendor_part_no


def generate_gfs_csv_from_po(po_data):
    """
    Generates a GFS CSV DataFrame directly from PO data.
    
    Args:
        po_data: Dictionary with PO data from MRPeasy
    
    Returns:
        pd.DataFrame: DataFrame with columns: Item #, Case QTY
        str: Error message if there are problems
    """
    try:
        products = po_data.get('products', [])
        
        if not products:
            return None, "No products found in the Purchase Order"
        
        # Create list to store rows
        rows = []
        
        for product in products:
            # Get vendor part number using the helper function
            item_number = get_vendor_part_number(product, po_data)
            
            # Get Case QTY - try multiple fields
            # Priority: vendor_quantity > quantity > ordered_quantity > qty
            vendor_quantity_raw = (
                product.get('vendor_quantity') or 
                product.get('quantity') or 
                product.get('ordered_quantity') or
                product.get('qty') or
                0
            )
            
            # Extract numeric value from vendor_quantity if it's a string like "35 Box of 20 kg"
            case_qty = ''
            if vendor_quantity_raw:
                if isinstance(vendor_quantity_raw, (int, float)):
                    # It's already a number
                    qty_value = float(vendor_quantity_raw)
                    if qty_value.is_integer():
                        case_qty = str(int(qty_value))
                    else:
                        case_qty = str(qty_value)
                else:
                    # It's a string, try to extract the number
                    import re
                    vendor_quantity_str = str(vendor_quantity_raw).strip()
                    # Try to extract first number from string (e.g., "35 Box of 20 kg" -> "35")
                    match = re.search(r'^(\d+(?:\.\d+)?)', vendor_quantity_str)
                    if match:
                        qty_value = float(match.group(1))
                        if qty_value.is_integer():
                            case_qty = str(int(qty_value))
                        else:
                            case_qty = str(qty_value)
                    else:
                        # If no number found, try to parse the whole string
                        try:
                            qty_value = float(vendor_quantity_str)
                            if qty_value.is_integer():
                                case_qty = str(int(qty_value))
                            else:
                                case_qty = str(qty_value)
                        except ValueError:
                            logger.warning(f"Could not extract quantity from: {vendor_quantity_str}")
                            case_qty = ''
            
            # Log for debugging
            logger.info(f"Product {product.get('item_code', 'N/A')}: vendor_quantity_raw={vendor_quantity_raw}, case_qty={case_qty}")
            
            # Only add row if we have an item number
            if item_number:
                rows.append({
                    'Item #': str(item_number),
                    'Case QTY': case_qty
                })
            else:
                logger.warning(f"Skipping product {product.get('item_code', 'N/A')} - no vendor part number found")
        
        if not rows:
            # Provide detailed error message with debug info
            error_details = []
            error_details.append("No products with vendor part numbers found in the Purchase Order.\n\n")
            error_details.append(f"**Total products in PO:** {len(products)}\n\n")
            error_details.append("**Products checked:**\n")
            for idx, product in enumerate(products[:5], 1):  # Show first 5
                item_code = product.get('item_code', 'N/A')
                vendor_part = get_vendor_part_number(product, po_data)
                error_details.append(f"{idx}. {item_code}: vendor part = '{vendor_part}'\n")
            if len(products) > 5:
                error_details.append(f"... and {len(products) - 5} more products\n")
            error_details.append("\n**Possible causes:**\n")
            error_details.append("- Vendor part numbers are not configured in purchase terms\n")
            error_details.append("- The vendor_id in the PO doesn't match any purchase terms\n")
            error_details.append("- Purchase terms exist but don't have vendor_item_code field\n")
            return None, ''.join(error_details)
        
        # Create DataFrame
        result_df = pd.DataFrame(rows)
        
        logger.info(f"Successfully generated {len(result_df)} rows from PO")
        return result_df, None
        
    except Exception as e:
        return None, f"Error generating CSV from PO: {str(e)}"


def convert_mrpeasy_po_to_gfs_format(po_data, template_df):
    """
    Converts MRPeasy PO data to GFS template format.
    Each product in the PO becomes a row in the CSV.
    
    Args:
        po_data: Dictionary with PO data from MRPeasy
        template_df: Template DataFrame (empty)
    
    Returns:
        pd.DataFrame: DataFrame filled with PO products in GFS format
        str: Error message if there are problems
    """
    try:
        # Create a copy of the template
        filled_df = template_df.copy()
        
        po_code = po_data.get('code', '')
        products = po_data.get('products', [])
        
        if not products:
            return None, "No products found in the Purchase Order"
        
        # Process each product in the PO
        for product in products:
            # Create a new row for each product
            new_row = {col: '' for col in template_df.columns}
        
            # Debug: Log product data for troubleshooting
            logger.info(f"Processing product: {product.get('item_code', 'N/A')}")
            logger.info(f"Product data keys: {list(product.keys())}")
            logger.info(f"vendor_item_code (Vendor part no.): {product.get('vendor_item_code')}")
            logger.info(f"vendor_quantity (Quantity): {product.get('vendor_quantity')}")
            logger.info(f"quantity: {product.get('quantity')}")
            
            # Map MRPeasy PO fields to GFS template columns
            # Based on the image format shown:
            # Part No. → item_code
            # Part description → item_title
            # Vendor part no. → vendor_item_code (if available)
            # Quantity → vendor_quantity or quantity
            # UoM → vendor_unit or unit
            # Price → item_price
            # Subtotal → total_price
            # Target lot → target_lot (if available)
            # Expected date → expected_date (if available)
            # Arrival date → arrival_date (if available)
            
            # Common mappings (case-insensitive)
            # GFS Format: Item #, Case QTY, Unit Qty
            # Item # = Vendor part no. (e.g., 1442997)
            # Case QTY = Ordered quantity (e.g., 78)
            # Unit = Vendor unit (e.g., "Case of 100 pcs")
            
            # Get vendor part number using the helper function
            # This function tries multiple sources: product fields, purchase terms, custom fields
            vendor_part_no = get_vendor_part_number(product, po_data)
            
            # FOURTH: If still not found, search ALL fields for a number that looks like vendor part
            if not vendor_part_no:
                # First, try to find it in any field that contains the exact number we're looking for
                # This is a more aggressive search
                for key, value in product.items():
                    if value:
                        value_str = str(value).strip()
                        # Remove any non-digit characters and check
                        digits_only = ''.join(filter(str.isdigit, value_str))
                        # Look for numeric values that could be vendor part (6-10 digits, not timestamps)
                        if digits_only and 6 <= len(digits_only) <= 10:
                            try:
                                num_value = int(digits_only)
                                # Exclude timestamps and IDs that are too large
                                # Vendor parts are usually 6-8 digits, sometimes 9-10
                                # Also exclude very small numbers (likely IDs) and very large (timestamps)
                                if 100000 <= num_value < 1000000000:  # Between 100000 and 1 billion
                                    vendor_part_no = digits_only
                                    logger.info(f"Found potential vendor part number in field '{key}': {vendor_part_no} (from value: {value})")
                                    break
                            except:
                                pass
            
            # Log vendor part number for debugging
            if vendor_part_no:
                logger.info(f"✅ Vendor part number found: {vendor_part_no} for product {product.get('item_code', 'N/A')}")
                # Log which field it came from
                if product.get('vendor_item_code'):
                    logger.info(f"   Source: vendor_item_code (from product)")
                elif product.get('vendor_part_no'):
                    logger.info(f"   Source: vendor_part_no (from product)")
                elif product.get('vendor_part_number'):
                    logger.info(f"   Source: vendor_part_number (from product)")
                else:
                    logger.info(f"   Source: purchase_terms or custom fields")
            else:
                # Log all available keys to help debug
                all_keys = list(product.keys())
                logger.warning(f"⚠️ No vendor part number found for product {product.get('item_code', 'N/A')}")
                logger.warning(f"   Available keys: {all_keys}")
                # Try to find any field that might contain a number that looks like a vendor part
                for key in all_keys:
                    value = product.get(key)
                    if value and isinstance(value, (str, int)):
                        value_str = str(value).strip()
                        # Check if it looks like a vendor part number (numeric, 6-10 digits)
                        if value_str.isdigit() and 6 <= len(value_str) <= 10:
                            logger.info(f"   Potential vendor part in '{key}': {value_str}")
            
            # Get ordered quantity - this is the vendor_quantity (ordered quantity)
            # The format might be "35 Box of 20 kg" - we need to extract just the number (35)
            ordered_quantity_raw = (
                product.get('vendor_quantity') or 
                product.get('quantity') or 
                product.get('ordered_quantity') or
                product.get('qty') or
                ''
            )
            
            # Extract numeric value from ordered quantity
            # Handle cases like "35 Box of 20 kg" -> extract "35"
            ordered_quantity = None
            ordered_quantity_str = ''
            
            if ordered_quantity_raw:
                # If it's a number, use it directly
                if isinstance(ordered_quantity_raw, (int, float)):
                    ordered_quantity = float(ordered_quantity_raw)
                else:
                    # If it's a string, try to extract the number
                    ordered_quantity_str_raw = str(ordered_quantity_raw).strip()
                    # Try to parse as float first
                    try:
                        ordered_quantity = float(ordered_quantity_str_raw)
                    except ValueError:
                        # If that fails, try to extract the first number from the string
                        # Example: "35 Box of 20 kg" -> extract "35"
                        import re
                        match = re.search(r'^(\d+(?:\.\d+)?)', ordered_quantity_str_raw)
                        if match:
                            ordered_quantity = float(match.group(1))
                        else:
                            logger.warning(f"Could not extract quantity from: {ordered_quantity_str_raw}")
            
            # Convert to string format
            if ordered_quantity is not None:
                try:
                    if ordered_quantity.is_integer():
                        ordered_quantity_str = str(int(ordered_quantity))
                    else:
                        ordered_quantity_str = str(ordered_quantity)
                except:
                    ordered_quantity_str = str(ordered_quantity) if ordered_quantity else ''
            else:
                ordered_quantity_str = ''
            
            # Get vendor unit - extract unit from "35 Box of 20 kg" -> "Box of 20 kg"
            vendor_unit = product.get('vendor_unit') or product.get('unit') or ''
            
            # If vendor_unit is empty but we have ordered_quantity_raw as string, try to extract unit
            if not vendor_unit and ordered_quantity_raw and isinstance(ordered_quantity_raw, str):
                # Example: "35 Box of 20 kg" -> extract "Box of 20 kg"
                match = re.search(r'\d+(?:\.\d+)?\s+(.+)', ordered_quantity_raw)
                if match:
                    vendor_unit = match.group(1).strip()
                    logger.info(f"Extracted unit from quantity string: {vendor_unit}")
            
            mapping_rules = {
                # GFS Simple Format
                # Item # MUST be vendor_part_no (product code from vendor), NOT vendor_code (vendor's code)
                'item #': str(vendor_part_no) if vendor_part_no else '',  # Use vendor_part_no only, no fallback to vendor_code
                'item#': str(vendor_part_no) if vendor_part_no else '',  # Use vendor_part_no only, no fallback to vendor_code
                '# de produit': str(vendor_part_no) if vendor_part_no else '',  # French version
                'item number': str(vendor_part_no) if vendor_part_no else '',
                'itemno': str(vendor_part_no) if vendor_part_no else '',
                'case qty': ordered_quantity_str,
                'caseqty': ordered_quantity_str,
                'unit qty': vendor_unit,
                'unitqty': vendor_unit,
                'unit': vendor_unit,
                'caisse': ordered_quantity_str,  # French for Case
                # Legacy format support
                'part no.': product.get('item_code', ''),
                'part description': product.get('item_title', ''),
                'vendor part no.': str(vendor_part_no) if vendor_part_no else '',  # Use vendor_part_no ONLY, NOT vendor_code
                'quantity': str(product.get('vendor_quantity', product.get('quantity', ''))),
                'uom': product.get('vendor_unit', product.get('unit', '')),
                'price': str(product.get('item_price', '')),
                'subtotal': str(product.get('total_price', '')),
                'revision': '',
                'target lot': product.get('target_lot', product.get('lot_code', '')),
                'expected date': format_date_for_gfs(product.get('expected_date', product.get('due_date', ''))),
                'arrival date': format_date_for_gfs(product.get('arrival_date', product.get('delivery_date', ''))),
                'po number': po_code,
                'po_number': po_code,
            }
            
            # Apply mappings to template columns
            for col in template_df.columns:
                col_original = col
                col_lower = col.lower().strip().replace('"', '').replace("'", '').replace(' ', '').replace('#', '#')
                
                # Try exact match first
                if col_lower in mapping_rules:
                    new_row[col] = mapping_rules[col_lower]
                # GFS Simple Format - Priority mappings
                elif 'item' in col_lower and ('#' in col_lower or 'no' in col_lower or 'number' in col_lower or 'produit' in col_lower):
                    # Item # / # de produit - MUST be vendor_item_code or vendor_part_no (product code from vendor, NOT vendor_code)
                    # vendor_item_code = product code from vendor (what we need for GFS, e.g., 1493567) - PRIMARY FIELD
                    # vendor_part_no = alternative field name for vendor part number
                    # vendor_code = vendor's code (e.g., V00017) - NOT what we want
                    if vendor_part_no:
                        new_row[col] = str(vendor_part_no)
                        logger.info(f"✅ Mapped Item # column '{col}' to vendor_part_no: {vendor_part_no}")
                    else:
                        # Try to get vendor part number from any available field (NOT vendor_code)
                        # vendor_product_code is the correct field for the product code from vendor
                        specific_vendor_part_no = (
                            product.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
                            product.get('vendor_item_code') or 
                            product.get('vendor_part_no') or 
                            product.get('vendor_part_number')
                        )
                        if specific_vendor_part_no:
                            new_row[col] = str(specific_vendor_part_no)
                            logger.info(f"✅ Found vendor part number directly: {specific_vendor_part_no}")
                        else:
                            # If still not found, leave empty (DO NOT use vendor_code or item_code)
                            logger.warning(f"⚠️ No vendor part number found for product {product.get('item_code', 'N/A')} - Item # will be empty")
                            logger.warning(f"   vendor_product_code value: {product.get('vendor_product_code')}")
                            logger.warning(f"   vendor_item_code value: {product.get('vendor_item_code')}")
                            logger.warning(f"   vendor_part_no value: {product.get('vendor_part_no')}")
                            logger.warning(f"   vendor_code (vendor's code, NOT product code): {product.get('vendor_code')}")
                            new_row[col] = ''  # Leave empty - DO NOT use vendor_code as it's the vendor's code, not the product code
                elif ('case' in col_lower and 'qty' in col_lower) or 'caisse' in col_lower:
                    # Case QTY / Caisse - MUST be ordered quantity (vendor_quantity)
                    # This is CRITICAL - GFS needs this number
                    ordered_qty = (
                        product.get('vendor_quantity') or 
                        product.get('quantity') or 
                        product.get('ordered_quantity') or
                        product.get('qty') or
                        0
                    )
                    # Format as integer if whole number, otherwise keep decimal
                    if ordered_qty:
                        try:
                            qty_float = float(ordered_qty)
                            if qty_float.is_integer():
                                new_row[col] = str(int(qty_float))
                            else:
                                new_row[col] = str(qty_float)
                        except:
                            new_row[col] = str(ordered_qty)
                    else:
                        # If no quantity found, log warning and try to extract from other fields
                        logger.warning(f"No quantity found for product {product.get('item_code', 'N/A')} in column {col}")
                        # Try to get any numeric value that might be quantity
                        for key in ['vendor_quantity', 'quantity', 'ordered_quantity', 'qty', 'booked', 'received']:
                            if product.get(key):
                                try:
                                    val = float(product.get(key))
                                    new_row[col] = str(int(val)) if val.is_integer() else str(val)
                                    logger.info(f"Using {key} = {new_row[col]} for Case QTY")
                                    break
                                except:
                                    pass
                elif 'unit' in col_lower:
                    # Unit / Unit Qty - use vendor unit (e.g., "Case of 100 pcs")
                    vendor_unit = product.get('vendor_unit') or product.get('unit') or ''
                    new_row[col] = vendor_unit
                # Legacy format support
                elif 'part no' in col_lower or 'partno' in col_lower:
                    new_row[col] = product.get('item_code', '')
                elif 'description' in col_lower:
                    new_row[col] = product.get('item_title', '')
                elif 'vendor' in col_lower and 'part' in col_lower:
                    # Use vendor_product_code first (correct field), then fallback to others
                    # Do NOT use vendor_code (vendor_code is the vendor ID, not product part number)
                    new_row[col] = (
                        product.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
                        product.get('vendor_item_code') or 
                        product.get('vendor_part_no') or 
                        product.get('vendor_part_number') or 
                        ''
                    )
                elif 'quantity' in col_lower and 'case' not in col_lower:
                    new_row[col] = str(product.get('vendor_quantity', product.get('quantity', '')))
                elif 'uom' in col_lower or ('unit' in col_lower and 'qty' not in col_lower):
                    new_row[col] = product.get('vendor_unit', product.get('unit', ''))
                elif 'price' in col_lower and 'subtotal' not in col_lower:
                    new_row[col] = str(product.get('item_price', ''))
                elif 'subtotal' in col_lower:
                    new_row[col] = str(product.get('total_price', ''))
                elif 'revision' in col_lower:
                    new_row[col] = ''
                elif 'target lot' in col_lower or ('lot' in col_lower and 'target' in col_lower):
                    new_row[col] = product.get('target_lot', product.get('lot_code', ''))
                elif 'expected date' in col_lower or 'expected' in col_lower:
                    new_row[col] = format_date_for_gfs(product.get('expected_date', product.get('due_date', '')))
                elif 'arrival date' in col_lower or 'arrival' in col_lower:
                    new_row[col] = format_date_for_gfs(product.get('arrival_date', product.get('delivery_date', '')))
                elif 'po' in col_lower and 'number' in col_lower:
                    new_row[col] = po_code
        
        # Add the row to the DataFrame
        filled_df = pd.concat([filled_df, pd.DataFrame([new_row])], ignore_index=True)
        
        return filled_df, None
    
    except Exception as e:
        return None, f"Error converting PO to GFS format: {str(e)}"


def parse_rfq_pdf(pdf_file):
    """
    Parses an RFQ PDF file and extracts vendor part numbers and quantities.
    
    Args:
        pdf_file: Uploaded PDF file object from Streamlit
    
    Returns:
        pd.DataFrame: DataFrame with columns: Item #, Case QTY
        str: Error message if there are problems
    """
    if not PDF_PARSING_AVAILABLE:
        return None, (
            "PDF parsing library not available. Please install one of the following:\n\n"
            "```bash\n"
            "pip install PyPDF2\n"
            "# or\n"
            "pip install pdfplumber\n"
            "```"
        )
    
    try:
        # Read PDF content
        pdf_bytes = pdf_file.read()
        pdf_file.seek(0)  # Reset file pointer
        
        # Extract text using available PDF library
        if PDF_LIBRARY == 'pdfplumber':
            import pdfplumber
            text_content = []
            with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
                for page in pdf.pages:
                    text_content.append(page.extract_text() or '')
            full_text = '\n'.join(text_content)
        elif PDF_LIBRARY == 'PyPDF2':
            import PyPDF2
            pdf_reader = PyPDF2.PdfReader(io.BytesIO(pdf_bytes))
            full_text = ''
            for page in pdf_reader.pages:
                full_text += page.extract_text() + '\n'
        else:
            return None, "No PDF parsing library available. Please install pdfplumber or PyPDF2."
        
        logger.info(f"Extracted text from RFQ PDF ({len(full_text)} characters)")
        
        # Parse the text to find vendor part numbers and quantities
        # The RFQ typically has a table with: Part description | Vendor part no. | Quantity
        
        rows = []
        lines = full_text.split('\n')
        
        # Look for table structure - find header row first
        header_found = False
        table_start_idx = -1
        
        for i, line in enumerate(lines):
            line_lower = line.lower().strip()
            # Look for table header
            if ('vendor part no' in line_lower or 'vendor part' in line_lower) and ('quantity' in line_lower or 'qty' in line_lower):
                header_found = True
                table_start_idx = i + 1
                break
        
        # If we found the header, parse rows after it
        if header_found and table_start_idx > 0:
            for i in range(table_start_idx, min(table_start_idx + 50, len(lines))):  # Check next 50 lines
                line = lines[i].strip()
                if not line:
                    continue
                
                # Look for vendor part number (6-10 digits, usually appears as standalone number)
                vendor_part_match = re.search(r'\b(\d{6,10})\b', line)
                
                # Look for quantity (number followed by unit like "Box", "Case", etc.)
                quantity_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:Box|Case|Unit|kg|lb|pcs|pc|each|ea)', line, re.IGNORECASE)
                
                if vendor_part_match:
                    vendor_part = vendor_part_match.group(1)
                    quantity = quantity_match.group(1) if quantity_match else ''
                    
                    # Only add if we have vendor part number
                    if vendor_part:
                        rows.append({
                            'Item #': vendor_part,
                            'Case QTY': quantity if quantity else ''
                        })
        
        # Alternative: More aggressive search if table parsing didn't work
        if not rows:
            # Look for patterns: vendor part number followed by quantity on same or next line
            for i, line in enumerate(lines):
                # Look for vendor part number
                vendor_part_matches = re.findall(r'\b(\d{6,10})\b', line)
                for vendor_part in vendor_part_matches:
                    # Check current line and next few lines for quantity
                    quantity_found = ''
                    for j in range(i, min(i + 3, len(lines))):
                        qty_match = re.search(r'(\d+(?:\.\d+)?)\s*(?:Box|Case|Unit)', lines[j], re.IGNORECASE)
                        if qty_match:
                            quantity_found = qty_match.group(1)
                            break
                    
                    rows.append({
                        'Item #': vendor_part,
                        'Case QTY': quantity_found
                    })
        
        if not rows:
            return None, (
                "Could not extract vendor part numbers and quantities from RFQ PDF.\n\n"
                "**Please verify:**\n"
                "- The PDF contains a table with 'Vendor part no.' and 'Quantity' columns\n"
                "- The vendor part numbers are 6-10 digit numbers\n"
                "- The quantities are clearly visible in the PDF"
            )
        
        # Create DataFrame
        result_df = pd.DataFrame(rows)
        
        # Remove duplicates
        result_df = result_df.drop_duplicates(subset=['Item #'])
        result_df = result_df.reset_index(drop=True)
        
        logger.info(f"Successfully extracted {len(result_df)} rows from RFQ PDF")
        return result_df, None
        
    except Exception as e:
        return None, f"Error parsing RFQ PDF: {str(e)}"


def parse_mrpeasy_csv(csv_file):
    """
    Parses a CSV file downloaded from MRPeasy and extracts the 3 required fields for GFS.
    
    Args:
        csv_file: Uploaded file object from Streamlit
    
    Returns:
        pd.DataFrame: DataFrame with columns: Item #, Case QTY
        str: Error message if there are problems
    """
    try:
        # Read the CSV file
        df = pd.read_csv(csv_file)
        
        # Log available columns for debugging
        logger.info(f"CSV columns: {list(df.columns)}")
        
        # Find the columns we need (case-insensitive)
        # Item # = Vendor part no.
        # Case QTY = Quantity
        
        item_col = None
        case_qty_col = None
        
        for col in df.columns:
            col_lower = col.lower().strip()
            # Look for Vendor part no. column
            if not item_col and ('vendor' in col_lower and 'part' in col_lower and 'no' in col_lower):
                item_col = col
            # Look for Quantity column
            if not case_qty_col and 'quantity' in col_lower:
                case_qty_col = col
        
        # If not found, try alternative column names
        if not item_col:
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'item' in col_lower and ('#' in col_lower or 'no' in col_lower or 'number' in col_lower):
                    item_col = col
                    break
        
        if not case_qty_col:
            for col in df.columns:
                col_lower = col.lower().strip()
                if 'qty' in col_lower or 'quantity' in col_lower:
                    case_qty_col = col
                    break
        
        # Check if we found required columns
        if not item_col:
            return None, "Could not find 'Vendor part no.' column in CSV. Available columns: " + ", ".join(df.columns)
        if not case_qty_col:
            return None, "Could not find 'Quantity' column in CSV. Available columns: " + ", ".join(df.columns)
        
        # Extract only the 2 required columns (Item # and Case QTY)
        result_df = pd.DataFrame({
            'Item #': df[item_col].astype(str).fillna(''),
            'Case QTY': df[case_qty_col].astype(str).fillna('')
        })
        
        # Remove empty rows
        result_df = result_df[result_df['Item #'].str.strip() != '']
        result_df = result_df.reset_index(drop=True)
        
        logger.info(f"Successfully extracted {len(result_df)} rows from CSV")
        logger.info(f"Columns used: Item #={item_col}, Case QTY={case_qty_col}")
        
        return result_df, None
        
    except pd.errors.EmptyDataError:
        return None, "The CSV file is empty."
    except pd.errors.ParserError as e:
        return None, f"Error parsing CSV file: {str(e)}"
    except Exception as e:
        return None, f"Error processing CSV file: {str(e)}"


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
This tool allows you to generate a CSV file in GFS format directly from a MRPeasy PO number.
Simply enter the PO number and the system will fetch the data and generate the file ready to upload to GFS Platform.
""")

# Show process steps
st.divider()
st.subheader("📋 Process Steps")

steps_col1, steps_col2, steps_col3 = st.columns(3)

with steps_col1:
    st.markdown("""
    **Step 1: Enter PO Number**
    
    Enter the Purchase Order number from MRPeasy (e.g., PO02686).
    """)

with steps_col2:
    st.markdown("""
    **Step 2: Generate CSV**
    
    The system automatically fetches the PO data and extracts the required fields.
    """)

with steps_col3:
    st.markdown("""
    **Step 3: Download GFS CSV**
    
    Download the CSV file with the 2 required fields (Item #, Case QTY) ready for GFS Platform.
    """)

st.divider()

# Inicializar session state
if 'csv_generated' not in st.session_state:
    st.session_state.csv_generated = None
if 'po_data' not in st.session_state:
    st.session_state.po_data = None

# ============================================================================
# CONFIGURATION CHECK (Hidden - not needed for CSV upload workflow)
# ============================================================================
# Configuration check is no longer displayed since we only need CSV upload
# The workflow no longer requires MRPeasy API or template configuration

# ============================================================================
# MAIN WORKFLOW - Enter PO Number to Generate CSV
# ============================================================================
st.divider()

# Main workflow: Enter PO Number
st.subheader("🔹 Step 1: Enter PO Number")

po_input = st.text_input(
    "PO Number",
    placeholder="Example: PO02686",
    help="Enter the Purchase Order number from MRPeasy"
)

if st.button("🔍 Generate CSV", type="primary", use_container_width=True):
    if not po_input or not po_input.strip():
        st.error("❌ Please enter a PO number")
    else:
        with st.spinner("🔍 Fetching PO from MRPeasy..."):
            po_data, error = get_po_data_from_mrpeasy(po_input.strip())
            
            if error:
                st.error(f"❌ {error}")
            else:
                st.success(f"✅ PO {po_input.strip()} found!")
                
                # Generate CSV from PO
                with st.spinner("⚙️ Generating CSV file..."):
                    gfs_df, gen_error = generate_gfs_csv_from_po(po_data)
                    
                    if gen_error:
                        st.error(f"❌ {gen_error}")
                        # Show debug information
                        with st.expander("🔍 Debug: Product Details", expanded=True):
                            if po_data.get('products'):
                                st.write("**Products in PO:**")
                                for idx, product in enumerate(po_data['products'][:10], 1):
                                    st.write(f"**Product {idx}:** {product.get('item_code', 'N/A')}")
                                    
                                    # Show vendor part number search
                                    vendor_part = get_vendor_part_number(product, po_data)
                                    if vendor_part:
                                        st.success(f"✅ Vendor part number: {vendor_part}")
                                    else:
                                        st.warning(f"⚠️ No vendor part number found")
                                        
                                        # Show what fields are available in the product
                                        st.write("**Available fields in product:**")
                                        vendor_fields = ['vendor_item_code', 'vendor_part_no', 'vendor_part_number', 'item_code', 'code']
                                        for field in vendor_fields:
                                            value = product.get(field)
                                            if value:
                                                st.write(f"- `{field}`: {value}")
                                        
                                        # Show quantity fields specifically
                                        st.write("**Quantity fields:**")
                                        qty_fields = ['vendor_quantity', 'quantity', 'ordered_quantity', 'qty', 'booked', 'received']
                                        for field in qty_fields:
                                            value = product.get(field)
                                            if value is not None:
                                                st.write(f"- `{field}`: {value}")
                                        
                                        # Show ALL product fields for debugging
                                        st.write("**All product fields (non-empty):**")
                                        for key, val in product.items():
                                            if val:  # Only show non-empty fields
                                                st.write(f"- `{key}`: {val}")
                                        
                                        # Show if we can get it from purchase terms
                                        item_code = product.get('item_code')
                                        if item_code:
                                            try:
                                                api_manager = get_api_manager()
                                                item_details = api_manager.get_item_details(item_code)
                                                if item_details:
                                                    purchase_terms = item_details.get('purchase_terms', [])
                                                    if purchase_terms:
                                                        st.write(f"**Purchase terms found:** {len(purchase_terms)}")
                                                        po_vendor_id = po_data.get('vendor_id')
                                                        st.write(f"**PO vendor_id:** {po_vendor_id}")
                                                        for term_idx, term in enumerate(purchase_terms[:3], 1):
                                                            term_vendor_id = term.get('vendor_id')
                                                            term_vendor_item = (
                                                                term.get('vendor_product_code') or  # This is the correct field! (e.g., 1493567)
                                                                term.get('vendor_item_code') or 
                                                                term.get('vendor_part_no') or
                                                                term.get('vendor_part_number') or
                                                                term.get('item_code') or
                                                                term.get('code') or
                                                                'None'  # Removed vendor_code - that's the vendor ID, not the product part number
                                                            )
                                                            match = "✅" if po_vendor_id and term_vendor_id == po_vendor_id else "❌"
                                                            st.write(f"{match} Term {term_idx}: vendor_id={term_vendor_id}, vendor_item_code={term_vendor_item}")
                                                            # Show all available fields in the matching term for debugging
                                                            if term_vendor_id == po_vendor_id:
                                                                st.write(f"   **All fields in matching term:**")
                                                                for key, val in term.items():
                                                                    if val:  # Only show non-empty fields
                                                                        st.write(f"   - `{key}`: {val}")
                                                    else:
                                                        st.write("**No purchase terms found for this item**")
                                            except Exception as e:
                                                st.write(f"Error checking purchase terms: {str(e)}")
                                    
                                    st.divider()
                    else:
                        st.session_state.csv_generated = gfs_df
                        st.session_state.po_data = po_data
                        st.success(f"✅ CSV generated successfully! Found {len(gfs_df)} products.")
                        
                        # Show preview
                        with st.expander("👁️ Preview: Generated Data", expanded=True):
                            st.dataframe(gfs_df, use_container_width=True)
                            st.write(f"**Total rows:** {len(gfs_df)}")

# OLD WORKFLOW REMOVED - Now using CSV upload method

if st.session_state.csv_generated is not None:
    st.divider()
    st.subheader("🔹 Step 3: Download CSV for GFS Platform")
    
    # Ensure the DataFrame has the exact column names required by GFS Platform
    # Column Format: Item # | Case QTY
    gfs_df = st.session_state.csv_generated.copy()
    
    # Rename columns to match exact GFS format if needed
    column_mapping = {}
    for col in gfs_df.columns:
        col_clean = col.strip()
        if 'item' in col_clean.lower() and '#' in col_clean:
            column_mapping[col] = 'Item #'
        elif 'case' in col_clean.lower() and 'qty' in col_clean.lower():
            column_mapping[col] = 'Case QTY'
    
    if column_mapping:
        gfs_df = gfs_df.rename(columns=column_mapping)
    
    # Ensure we only have the 2 required columns in the correct order
    required_columns = ['Item #', 'Case QTY']
    # Keep only the columns that exist
    existing_columns = [col for col in required_columns if col in gfs_df.columns]
    if len(existing_columns) == 2:
        gfs_df = gfs_df[required_columns]
    else:
        # If columns don't match, create them with empty values
        for col in required_columns:
            if col not in gfs_df.columns:
                gfs_df[col] = ''
        gfs_df = gfs_df[required_columns]
    
    # Convert DataFrame to CSV in memory
    csv_buffer = io.StringIO()
    gfs_df.to_csv(csv_buffer, index=False)
    csv_string = csv_buffer.getvalue()
    csv_bytes = csv_string.encode('utf-8')
    
    # File name - get from PO data
    if st.session_state.po_data and st.session_state.po_data.get('code'):
        po_number = st.session_state.po_data.get('code', '').strip()
        po_number = re.sub(r'[_\s]+', '_', po_number).strip('_')
    else:
        po_number = "GFS_Order"
    filename = f"GFS_{po_number}.csv"
    
    st.download_button(
        label="📥 Download CSV for GFS Platform",
        data=csv_bytes,
        file_name=filename,
        mime="text/csv",
        type="primary",
        use_container_width=True
    )
    
    st.success("✅ Step 3: CSV file ready to download!")
    st.info("💡 **The CSV file contains the 2 required columns: Item # and Case QTY. You can now upload it to GFS Platform.**")
    st.warning("⚠️ **Important:** GFS Platform only accepts .CSV or .XLS files (not .XLSX). This file is in CSV format and should work correctly.")
else:
    st.divider()
    st.subheader("🔹 Step 3: Download CSV")
    st.info("⏳ Waiting for CSV to be processed...")

    # Help information
    st.divider()
    with st.expander("ℹ️ Information and Usage Guide"):
        st.markdown("""
        ### 📖 Workflow:
        
        1. **Enter the PO number** (example: PO02680)
        2. The application searches for the PO in Google Sheets
        3. The PO data is automatically converted to CSV format
        4. Download the CSV file ready for GFS
        
        ### 🔄 How it works:
        
        - The system fetches the PO directly from MRPeasy API
        - The GFS template CSV is loaded (required format)
        - Each product in the PO is converted to a row in the CSV
        - MRPeasy fields are automatically mapped to GFS template columns:
          - Part No. → Item Code
          - Part description → Item Title
          - Vendor part no. → Vendor Item Code
          - Quantity → Vendor Quantity
          - UoM → Vendor Unit
          - Price → Item Price
          - Subtotal → Total Price
          - Target lot → Lot Code
          - Expected/Arrival dates → Formatted dates
        - The CSV is generated in the exact format GFS requires
        
        ### 📝 Notes:
        
        - **Template Required**: The GFS template CSV must be configured for the system to work
        - **MRPeasy API**: PO data is fetched directly from MRPeasy (no Google Sheets needed)
        - **Multiple Products**: Each product in the PO becomes a separate row in the CSV
        - **PO Number**: The PO number is automatically included in each row
        - **GFS Format**: The output CSV follows the exact format required by GFS platform
        """)

