import streamlit as st
import logging
from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import base64
import tempfile
import json
from io import BytesIO

from shared.api_manager import APIManager
from config import secrets
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.barcode import code128
import requests
from PIL import Image as PILImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BarCode128(Flowable):
    """A custom Flowable for Code 128 barcodes"""

    def __init__(self, value, width=3 * inch, height=0.5 * inch):
        Flowable.__init__(self)
        self.value = value
        self.barWidth = width
        self.barHeight = height

    def wrap(self, availWidth, availHeight):
        """Returns the size this flowable will take up"""
        return self.barWidth, self.barHeight

    def draw(self):
        """Draw the barcode"""
        barcode = code128.Code128(self.value, barWidth=0.01 * inch, barHeight=self.barHeight)
        x = (self.barWidth - barcode.width) / 2  # Center the barcode
        barcode.drawOn(self.canv, x, 0)


@st.cache_data(ttl=3600*6, show_spinner=False)  # 6 hours cache
def fetch_items_cache(api_key: str, api_secret: str) -> List[Dict]:
    """Fetch and cache all items for 6 hours"""
    api = APIManager()
    items = api.fetch_all_products()
    logger.info(f"Items cache initialized with {len(items) if items else 0} items")
    return items if items else []


@st.cache_data(ttl=3600*6, show_spinner=False)  # 6 hours cache
def fetch_units_cache(api_key: str, api_secret: str) -> List[Dict]:
    """Fetch and cache all units for 6 hours"""
    api = APIManager()
    units = api.fetch_units()
    logger.info(f"Units cache initialized with {len(units) if units else 0} units")
    return units if units else []


def get_cache_info() -> Dict[str, Any]:
    """Get cache metadata from session state"""
    if 'cache_metadata' not in st.session_state:
        st.session_state.cache_metadata = {
            'items_loaded': False,
            'units_loaded': False,
            'last_updated': None
        }
    return st.session_state.cache_metadata


def clear_all_caches():
    """Clear all cached data"""
    fetch_items_cache.clear()
    fetch_units_cache.clear()
    st.session_state.cache_metadata = {
        'items_loaded': False,
        'units_loaded': False,
        'last_updated': None
    }
    logger.info("All caches cleared")


def initialize_session_state():
    """Initialize session state variables"""
    if 'selected_team' not in st.session_state:
        st.session_state.selected_team = None
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    if 'selected_item' not in st.session_state:
        st.session_state.selected_item = None
    if 'created_mo_id' not in st.session_state:
        st.session_state.created_mo_id = None
    if 'step' not in st.session_state:
        st.session_state.step = 1


def display_cache_status(items: List[Dict], units: List[Dict]):
    """Display cache status in sidebar"""
    st.sidebar.header("📦 Cache Status")

    cache_info = get_cache_info()
    
    # Display last updated time
    if cache_info['last_updated']:
        last_updated = cache_info['last_updated'].strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.text(f"Last Updated: {last_updated}")

        # Calculate time remaining
        expiry_time = cache_info['last_updated'] + timedelta(hours=6)
        time_remaining = expiry_time - datetime.now()
        hours_remaining = time_remaining.total_seconds() / 3600
        
        if hours_remaining > 0:
            st.sidebar.success(f"Valid for: {hours_remaining:.1f} hours")
        else:
            st.sidebar.warning("Cache expired")

    # Display cache stats
    if items or units:
        st.sidebar.metric("Cached Items", len(items))
        st.sidebar.metric("Cached Units", len(units))

    # Add clear cache button
    if st.sidebar.button("🔄 Clear Cache"):
        clear_all_caches()
        st.sidebar.success("Cache cleared successfully")
        st.rerun()


def get_unit_by_id(unit_id: int, units: List[Dict]) -> str:
    """Get unit name by unit_id"""
    if not units or not unit_id:
        return 'unit'
    
    for unit in units:
        if unit.get('unit_id') == unit_id:
            return unit.get('title', 'unit')
    
    return 'unit'


def get_item_by_article_id(article_id: int, items: List[Dict]) -> Optional[Dict]:
    """Get item details by article_id"""
    if not items:
        return None
    for item in items:
        if item.get('article_id') == article_id:
            return item
    return None


def parse_operation_description(description_str):
    """Parse the JSON string from operation description"""
    try:
        return json.loads(description_str)
    except (json.JSONDecodeError, TypeError):
        return None


def download_image(url, max_size=(100, 100)):
    """Download and resize image from URL"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = PILImage.open(BytesIO(response.content))
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            
            # Save to temporary file
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_img.name, 'PNG')
            return temp_img.name
        return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def generate_mo_recipe_pdf(mo_data, mo_full_data, items_cache, units_cache):
    """Generate PDF from MO data with BOM summary and operations"""
    import os
    
    # Create a temporary file for the PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_filename = temp_pdf.name
    temp_pdf.close()
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, 
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        leading=12
    )
    
    # Add title
    title = Paragraph(mo_data.get('item_title', 'Recipe'), title_style)
    elements.append(title)
    
    # Add expected output
    quantity = mo_data.get('quantity', 0)
    unit = mo_data.get('unit', '')
    expected_output = Paragraph(f'Expected Output: {quantity} {unit}', subtitle_style)
    elements.append(expected_output)
    elements.append(Spacer(1, 0.1*inch))
    
    # Add lot code and barcode if available
    lot_code = mo_data.get('lot_code')
    if lot_code:
        # Create a centered table for lot code and barcode
        lot_code_para = Paragraph(f'<b>Lot Code: {lot_code}</b>', subtitle_style)
        lot_barcode = BarCode128(lot_code, width=2.5*inch, height=0.5*inch)
        
        # Create table to center the barcode
        lot_table_data = [
            [lot_code_para],
            [lot_barcode]
        ]
        lot_table = Table(lot_table_data, colWidths=[7.5*inch])
        lot_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(lot_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Add Recipe Summary section
    recipe_summary_title = Paragraph('Recipe Summary', section_header_style)
    elements.append(recipe_summary_title)
    
    # Build BOM summary table
    bom_table_data = []
    bom_header_row = [
        Paragraph('INGREDIENTS', header_style),
        Paragraph('QUANTITY', header_style),
        Paragraph('UNIT', header_style)
    ]
    bom_table_data.append(bom_header_row)
    
    # Process parts
    parts = mo_full_data.get('parts', [])
    for part in parts:
        article_id = part.get('article_id')
        booked = part.get('booked', 0)
        
        # Get item details
        item = get_item_by_article_id(article_id, items_cache)
        if item:
            item_title = item.get('title', 'Unknown Item')
            unit_id = item.get('unit_id')
            unit = get_unit_by_id(unit_id, units_cache)
            
            # Format quantity
            qty_display = f"{booked:.2f}".rstrip('0').rstrip('.')
            
            row = [
                Paragraph(item_title, cell_style),
                Paragraph(qty_display, cell_style),
                Paragraph(unit, cell_style)
            ]
            bom_table_data.append(row)
    
    # Create BOM table
    bom_col_widths = [4.5*inch, 1.5*inch, 1.5*inch]
    bom_table = Table(bom_table_data, colWidths=bom_col_widths, repeatRows=1)
    
    # Style the BOM table
    bom_table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B7280')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    
    bom_table.setStyle(bom_table_style)
    elements.append(bom_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add Operations/Routing section
    # Prepare operations table data
    table_data = []
    
    # Header row
    header_row = [
        Paragraph('STEP', header_style),
        Paragraph('INGREDIENTS', header_style),
        Paragraph('PROCEDURE', header_style),
        Paragraph('EQUIPMENT', header_style)
    ]
    table_data.append(header_row)
    
    # Process operations
    operations = mo_full_data.get('operations', [])
    temp_image_files = []  # Keep track of temp files to clean up
    
    for operation in operations:
        description_str = operation.get('description', '{}')
        operation_data = parse_operation_description(description_str)
        
        if not operation_data:
            continue
        
        step_name = operation_data.get('step', 'Step')
        name = operation_data.get('name', '')
        step_text = f"{step_name}<br/>{name}" if name else step_name
        
        # Build ingredients text
        ingredients_list = operation_data.get('ingredients', [])
        ingredients_text = ''
        for ing in ingredients_list:
            item = ing.get('item', '')
            amount = ing.get('amount', '')
            ingredients_text += f"• {item} – {amount}<br/>"
        
        # Build procedure text
        procedure_list = operation_data.get('procedure', [])
        procedure_text = ''
        for proc in procedure_list:
            step_num = proc.get('step', '')
            instruction = proc.get('instruction', '')
            procedure_text += f"{step_num}. {instruction}<br/>"
        
        # Handle equipment with image
        equipment_list = operation_data.get('equipment', [])
        equipment_cell_content = []
        
        if equipment_list:
            equipment = equipment_list[0]
            equipment_name = equipment.get('name', '')
            equipment_image_url = equipment.get('image', '')
            
            if equipment_name:
                equipment_cell_content.append(Paragraph(equipment_name, cell_style))
            
            if equipment_image_url:
                # Download and add image
                img_path = download_image(equipment_image_url, max_size=(80, 80))
                if img_path:
                    temp_image_files.append(img_path)
                    try:
                        img = Image(img_path, width=80, height=80)
                        equipment_cell_content.append(Spacer(1, 0.05*inch))
                        equipment_cell_content.append(img)
                    except Exception as e:
                        logger.error(f"Error adding image to PDF: {e}")
        
        # Create row
        row = [
            Paragraph(step_text, cell_style),
            Paragraph(ingredients_text, cell_style),
            Paragraph(procedure_text, cell_style),
            equipment_cell_content if equipment_cell_content else Paragraph('', cell_style)
        ]
        table_data.append(row)
    
    # Create operations table
    col_widths = [1.2*inch, 2.2*inch, 2.8*inch, 1.3*inch]
    operations_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the operations table
    operations_table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    
    operations_table.setStyle(operations_table_style)
    elements.append(operations_table)
    
    # Build PDF
    doc.build(elements)
    
    # Clean up temporary image files
    for img_file in temp_image_files:
        try:
            os.unlink(img_file)
        except Exception:
            pass
    
    return pdf_filename


def main():
    """Main application function"""
    st.title("⚡ Quick Manufacturing Order Creator")
    st.markdown("Create MOs and generate routing PDFs in one streamlined workflow")

    # Initialize session state
    initialize_session_state()

    # Initialize API Manager
    api = APIManager()

    # Get API credentials for cache key
    api_key = secrets.get('MRPEASY_API_KEY', '')
    api_secret = secrets.get('MRPEASY_API_SECRET', '')

    # Load cached data (will use existing cache if valid, otherwise fetch new)
    with st.spinner("Loading data..."):
        all_items = fetch_items_cache(api_key, api_secret)
        all_units = fetch_units_cache(api_key, api_secret)
        
        # Update cache metadata on first load in this session
        cache_info = get_cache_info()
        if not cache_info['items_loaded'] or not cache_info['units_loaded']:
            cache_info['items_loaded'] = True
            cache_info['units_loaded'] = True
            cache_info['last_updated'] = datetime.now()

    # Display cache status in sidebar
    display_cache_status(all_items, all_units)

    # Filter items where is_raw = false
    filtered_items = [item for item in all_items if item.get('is_raw') == False]

    # Extract unique teams (custom_44680)
    teams = sorted(list(set([item.get('custom_44680') for item in filtered_items if item.get('custom_44680')])))

    # Step 1: Select Team
    st.header("Step 1: Select Team")
    
    # Create columns for team buttons (3 per row for better touchscreen UX)
    cols_per_row = 3
    team_cols = st.columns(cols_per_row)
    
    for idx, team in enumerate(teams):
        col_idx = idx % cols_per_row
        with team_cols[col_idx]:
            if st.button(
                team, 
                key=f"team_{team}",
                use_container_width=True,
                type="primary" if st.session_state.selected_team == team else "secondary"
            ):
                st.session_state.selected_team = team
                st.session_state.selected_category = None
                st.session_state.selected_item = None
                st.session_state.step = 2

    # Step 2: Select Category
    if st.session_state.selected_team:
        st.divider()
        st.header("Step 2: Select Category")
        st.info(f"**Selected Team:** {st.session_state.selected_team}")
        
        # Filter items by selected team
        team_items = [item for item in filtered_items if item.get('custom_44680') == st.session_state.selected_team]
        
        # Extract unique categories (group_title)
        categories = sorted(list(set([item.get('group_title') for item in team_items if item.get('group_title')])))
        
        # Create columns for category buttons
        category_cols = st.columns(cols_per_row)
        
        for idx, category in enumerate(categories):
            col_idx = idx % cols_per_row
            with category_cols[col_idx]:
                if st.button(
                    category,
                    key=f"category_{category}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_category == category else "secondary"
                ):
                    st.session_state.selected_category = category
                    st.session_state.selected_item = None
                    st.session_state.step = 3

    # Step 3: Select Item
    if st.session_state.selected_team and st.session_state.selected_category:
        st.divider()
        st.header("Step 3: Select Item")
        st.info(f"**Team:** {st.session_state.selected_team} | **Category:** {st.session_state.selected_category}")
        
        # Filter items by selected team and category
        category_items = [
            item for item in filtered_items 
            if item.get('custom_44680') == st.session_state.selected_team 
            and item.get('group_title') == st.session_state.selected_category
        ]
        
        # Sort by title alphabetically
        category_items = sorted(category_items, key=lambda x: x.get('title', ''))
        
        # Create columns for item buttons
        item_cols = st.columns(cols_per_row)
        
        for idx, item in enumerate(category_items):
            col_idx = idx % cols_per_row
            item_title = item.get('title', 'Unknown')
            item_code = item.get('code', '')
            
            with item_cols[col_idx]:
                if st.button(
                    f"{item_title}\n({item_code})",
                    key=f"item_{item_code}",
                    use_container_width=True,
                    type="primary" if st.session_state.selected_item == item else "secondary"
                ):
                    st.session_state.selected_item = item
                    st.session_state.step = 4

    # Step 4: Enter Quantity and Create MO
    if st.session_state.selected_item:
        st.divider()
        st.header("Step 4: Enter Quantity")
        
        selected_item = st.session_state.selected_item
        st.success(f"**Selected Item:** {selected_item.get('title')} ({selected_item.get('code')})")
        
        # Get unit for the item
        unit_id = selected_item.get('unit_id')
        unit_name = get_unit_by_id(unit_id, all_units)
        
        # Quantity input
        col1, col2 = st.columns([3, 1])
        with col1:
            quantity = st.number_input(
                f"Quantity to Produce ({unit_name})",
                min_value=0.0,
                step=1.0,
                format="%.2f",
                key="quantity_input"
            )
        with col2:
            st.metric("Unit", unit_name)
        
        # Submit button
        if st.button("🚀 Create Manufacturing Order", type="primary", use_container_width=True):
            if quantity <= 0:
                st.error("Please enter a quantity greater than 0")
            else:
                with st.spinner("Creating Manufacturing Order..."):
                    try:
                        # Get current date as Unix timestamp
                        current_date = int(datetime.now().timestamp())
                        
                        # Create the manufacturing order
                        response = api.create_manufacturing_order(
                            item_code=selected_item.get('code'),
                            quantity=float(quantity),
                            assigned_id=1,
                            start_date=current_date
                        )
                        
                        if response.ok:
                            # Handle response - could be int or dict
                            response_data = response.json()
                            logger.info(f"MO Creation Response: {response_data}")
                            logger.info(f"Response type: {type(response_data)}")
                            print(f"MO Creation Response: {response_data}")
                            print(f"Response type: {type(response_data)}")
                            
                            if isinstance(response_data, int):
                                mo_id = response_data
                            elif isinstance(response_data, dict):
                                mo_id = response_data.get('man_ord_id') or response_data.get('id')
                            else:
                                st.error(f"Unexpected response format: {response_data}")
                                return
                            
                            st.session_state.created_mo_id = mo_id
                            
                            st.success(f"✅ Manufacturing Order created successfully! (ID: {mo_id})")
                            
                            # Now generate the PDF
                            with st.spinner("Generating routing PDF..."):
                                # Fetch the MO data (contains both basic and detailed info)
                                mo_data = api.get_manufacturing_order_details(mo_id)
                                
                                if mo_data:
                                    mo_code = mo_data.get('code', 'MO')
                                    
                                    # Generate PDF (mo_data contains all needed info)
                                    pdf_file = generate_mo_recipe_pdf(
                                        mo_data, 
                                        mo_data, 
                                        all_items,
                                        all_units
                                    )
                                    
                                    st.success("🎉 Routing PDF Generated Successfully!")
                                    
                                    # Provide download button
                                    with open(pdf_file, 'rb') as f:
                                        pdf_bytes = f.read()
                                        st.download_button(
                                            label="📥 Download Routing PDF",
                                            data=pdf_bytes,
                                            file_name=f"{selected_item.get('code')}_{mo_code}_routing.pdf",
                                            mime="application/pdf",
                                            type="primary",
                                            use_container_width=True
                                        )
                                    
                                    # Clean up temp file
                                    import os
                                    try:
                                        os.unlink(pdf_file)
                                    except:
                                        pass
                                else:
                                    st.warning("MO created but could not fetch details for PDF generation")
                        else:
                            st.error(f"❌ Failed to create Manufacturing Order: {response.text}")
                    
                    except Exception as e:
                        logger.error(f"Error creating MO: {str(e)}")
                        st.error(f"❌ Error: {str(e)}")
        
        # Reset button
        st.divider()
        if st.button("🔄 Start Over", use_container_width=True):
            st.session_state.selected_team = None
            st.session_state.selected_category = None
            st.session_state.selected_item = None
            st.session_state.created_mo_id = None
            st.session_state.step = 1


if __name__ == "__main__":
    main()

