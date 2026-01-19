"""
Generate CSV for GFS Platform
==============================

This Streamlit application generates a CSV file in GFS format directly from a MRPeasy PO number.

Required Dependencies:
- streamlit
- pandas
- shared.api_manager.APIManager (from your project)
- config.secrets (from your project)

Configuration:
Add to `.streamlit/secrets.toml`:
    MRPEASY_API_KEY = "your_api_key"
    MRPEASY_API_SECRET = "your_api_secret"
"""

import streamlit as st
import pandas as pd
import io
from shared.api_manager import APIManager
from config import secrets
import logging
import re

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def get_api_manager():
    """Gets or initializes the APIManager"""
    if 'api_manager' not in st.session_state:
        st.session_state.api_manager = APIManager()
    return st.session_state.api_manager


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
        variations.append(original_code)  # Original as-is
        
        # Remove "PO" prefix if present
        if original_code.upper().startswith('PO'):
            variations.append(original_code[2:].strip())
        
        # Add "PO" prefix if not present
        if not original_code.upper().startswith('PO'):
            variations.append(f"PO{original_code}")
        
        # Try with leading zeros (if it's a number)
        numeric_part = ''.join(filter(str.isdigit, original_code))
        if numeric_part:
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
        tried_variations = ', '.join([f"'{v}'" for v in unique_variations[:5]])
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
        return None, (
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


def get_vendor_part_number(product, po_data=None):
    """
    Gets the vendor part number for a product, trying multiple sources.
    Priority: product fields → purchase terms → custom fields
    
    Args:
        product: Dictionary with product data from PO
        po_data: Optional PO data dictionary (needed to match vendor_id in purchase terms)
    
    Returns:
        str: Vendor part number or empty string if not found
    """
    vendor_part_no = ''
    
    # Try product fields first
    vendor_part_no = (
        product.get('vendor_product_code') or
        product.get('vendor_item_code') or 
        product.get('vendor_part_no') or 
        product.get('vendor_part_number') or
        ''
    )
    
    if vendor_part_no:
        logger.info(f"Found vendor part number directly in product: {vendor_part_no}")
        return vendor_part_no
    
    # Try purchase terms (most reliable source)
    item_code = product.get('item_code')
    if item_code:
        try:
            api_manager = get_api_manager()
            item_details = api_manager.get_item_details(item_code)
            if item_details:
                purchase_terms = item_details.get('purchase_terms', [])
                if purchase_terms:
                    po_vendor_id = po_data.get('vendor_id') if po_data else None
                    
                    # Try to match by vendor_id first
                    if po_vendor_id:
                        for term in purchase_terms:
                            if term.get('vendor_id') == po_vendor_id:
                                vendor_part_no = (
                                    term.get('vendor_product_code') or
                                    term.get('vendor_item_code') or 
                                    term.get('vendor_part_no') or
                                    term.get('vendor_part_number') or
                                    term.get('item_code') or
                                    term.get('code') or
                                    ''
                                )
                                if vendor_part_no and str(vendor_part_no).strip():
                                    logger.info(f"Found vendor part number in purchase terms (matched by vendor_id): {vendor_part_no}")
                                    return vendor_part_no
                    
                    # If no match by vendor_id, use first available term
                    for term in purchase_terms:
                        vendor_part_no = (
                            term.get('vendor_product_code') or
                            term.get('vendor_item_code') or 
                            term.get('vendor_part_no') or
                            term.get('vendor_part_number') or
                            term.get('item_code') or
                            term.get('code') or
                            ''
                        )
                        if vendor_part_no and str(vendor_part_no).strip():
                            logger.info(f"Found vendor part number in purchase terms (using first available): {vendor_part_no}")
                            return vendor_part_no
        except Exception as e:
            logger.warning(f"Error fetching item details for {item_code}: {str(e)}")
    
    # Try custom fields as last resort
    for key, value in product.items():
        if key.startswith('custom_') and value:
            value_str = str(value).strip()
            if value_str.isdigit() and 6 <= len(value_str) <= 10:
                try:
                    num_value = int(value_str)
                    if num_value < 1000000000:  # Exclude timestamps
                        vendor_part_no = value_str
                        logger.info(f"Found vendor part number in custom field '{key}': {vendor_part_no}")
                        return vendor_part_no
                except:
                    pass
    
    return vendor_part_no


def extract_quantity(vendor_quantity_raw):
    """
    Extracts numeric quantity from vendor_quantity field.
    Handles both numeric values and strings like "35 Box of 20 kg".
    
    Args:
        vendor_quantity_raw: Quantity value (int, float, or string)
    
    Returns:
        str: Extracted quantity as string, or empty string if not found
    """
    if not vendor_quantity_raw:
        return ''
    
    if isinstance(vendor_quantity_raw, (int, float)):
        qty_value = float(vendor_quantity_raw)
        return str(int(qty_value)) if qty_value.is_integer() else str(qty_value)
    
    # Extract number from string (e.g., "35 Box of 20 kg" -> "35")
    vendor_quantity_str = str(vendor_quantity_raw).strip()
    match = re.search(r'^(\d+(?:\.\d+)?)', vendor_quantity_str)
    
    if match:
        qty_value = float(match.group(1))
        return str(int(qty_value)) if qty_value.is_integer() else str(qty_value)
    
    # Try to parse the whole string
    try:
        qty_value = float(vendor_quantity_str)
        return str(int(qty_value)) if qty_value.is_integer() else str(qty_value)
    except ValueError:
        logger.warning(f"Could not extract quantity from: {vendor_quantity_str}")
        return ''


def generate_gfs_csv_from_po(po_data):
    """
    Generates a GFS CSV DataFrame directly from PO data.
    
    Args:
        po_data: Dictionary with PO data from MRPeasy
    
    Returns:
        tuple: (pd.DataFrame, str) - DataFrame with columns: Item #, Case QTY, or error message
    """
    try:
        products = po_data.get('products', [])
        
        if not products:
            return None, "No products found in the Purchase Order"
        
        rows = []
        
        for product in products:
            # Get vendor part number
            item_number = get_vendor_part_number(product, po_data)
            
            # Get Case QTY - try multiple fields
            vendor_quantity_raw = (
                product.get('vendor_quantity') or 
                product.get('quantity') or 
                product.get('ordered_quantity') or
                product.get('qty') or
                0
            )
            
            case_qty = extract_quantity(vendor_quantity_raw)
            
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
            error_details = []
            error_details.append("No products with vendor part numbers found in the Purchase Order.\n\n")
            error_details.append(f"**Total products in PO:** {len(products)}\n\n")
            error_details.append("**Products checked:**\n")
            for idx, product in enumerate(products[:5], 1):
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
        
        result_df = pd.DataFrame(rows)
        logger.info(f"Successfully generated {len(result_df)} rows from PO")
        return result_df, None
        
    except Exception as e:
        return None, f"Error generating CSV from PO: {str(e)}"


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

# Initialize session state
if 'csv_generated' not in st.session_state:
    st.session_state.csv_generated = None
if 'po_data' not in st.session_state:
    st.session_state.po_data = None

# ============================================================================
# MAIN WORKFLOW
# ============================================================================
st.divider()
st.subheader("◆ Step 1: Enter PO Number")

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
                                    
                                    vendor_part = get_vendor_part_number(product, po_data)
                                    if vendor_part:
                                        st.success(f"✅ Vendor part number: {vendor_part}")
                                    else:
                                        st.warning(f"⚠️ No vendor part number found")
                                        
                                        st.write("**Available fields in product:**")
                                        vendor_fields = ['vendor_item_code', 'vendor_part_no', 'vendor_part_number', 'vendor_product_code', 'item_code', 'code']
                                        for field in vendor_fields:
                                            value = product.get(field)
                                            if value:
                                                st.write(f"- `{field}`: {value}")
                                        
                                        st.write("**Quantity fields:**")
                                        qty_fields = ['vendor_quantity', 'quantity', 'ordered_quantity', 'qty', 'booked', 'received']
                                        for field in qty_fields:
                                            value = product.get(field)
                                            if value is not None:
                                                st.write(f"- `{field}`: {value}")
                                        
                                        # Show purchase terms info
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
                                                                term.get('vendor_product_code') or
                                                                term.get('vendor_item_code') or 
                                                                term.get('vendor_part_no') or
                                                                term.get('vendor_part_number') or
                                                                term.get('item_code') or
                                                                term.get('code') or
                                                                'None'
                                                            )
                                                            match = "✅" if po_vendor_id and term_vendor_id == po_vendor_id else "❌"
                                                            st.write(f"{match} Term {term_idx}: vendor_id={term_vendor_id}, vendor_item_code={term_vendor_item}")
                                                            if term_vendor_id == po_vendor_id:
                                                                st.write(f"   **All fields in matching term:**")
                                                                for key, val in term.items():
                                                                    if val:
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

# Step 3: Download CSV
if st.session_state.csv_generated is not None:
    st.divider()
    st.subheader("◆ Step 3: Download CSV for GFS Platform")
    
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
    existing_columns = [col for col in required_columns if col in gfs_df.columns]
    if len(existing_columns) == 2:
        gfs_df = gfs_df[required_columns]
    else:
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
    st.subheader("◆ Step 3: Download CSV")
    st.info("⏳ Waiting for CSV to be processed...")

# Help information
st.divider()
with st.expander("ℹ️ Information and Usage Guide"):
    st.markdown("""
    ### 📖 Workflow:
    
    1. **Enter the PO number** (example: PO02680)
    2. The application fetches the PO directly from MRPeasy API
    3. The PO data is automatically converted to CSV format
    4. Download the CSV file ready for GFS
    
    ### 🔄 How it works:
    
    - The system fetches the PO directly from MRPeasy API
    - Each product in the PO is converted to a row in the CSV
    - MRPeasy fields are automatically mapped to GFS format:
      - Vendor part number → Item #
      - Vendor quantity → Case QTY
    - The CSV is generated in the exact format GFS requires
    
    ### 📝 Notes:
    
    - **MRPeasy API**: PO data is fetched directly from MRPeasy (no Google Sheets needed)
    - **Multiple Products**: Each product in the PO becomes a separate row in the CSV
    - **GFS Format**: The output CSV follows the exact format required by GFS platform
    
    ### ⚙️ Configuration Required:
    
    Add to `.streamlit/secrets.toml`:
    ```toml
    MRPEASY_API_KEY = "your_api_key"
    MRPEASY_API_SECRET = "your_api_secret"
    ```
    """)
