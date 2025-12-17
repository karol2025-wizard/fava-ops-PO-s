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
from shared.gdocs_manager import GDocsManager
from config import secrets
from reportlab.lib import colors
import os
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
    if 'show_recipe' not in st.session_state:
        st.session_state.show_recipe = False
    if 'current_recipe' not in st.session_state:
        st.session_state.current_recipe = None
    if 'gdocs_manager' not in st.session_state:
        st.session_state.gdocs_manager = None


# Team name mapping: original_name -> display_name
TEAM_NAME_MAPPING = {
    'Alejandro Team': 'Dips and Sauces',
    'Assembly Team': 'Kits',
    'Butcher Team': 'Raw proteins',
    'Grill Team': 'To re heat',
    'Theadora Team': 'Appetizers',
    'Samia Team': 'Dessert',
    'Jorge Team': 'Preparation Bases',
    'Rawad': 'Others',
    'Bread Team': 'Bread'
}

# Expected items by team (for validation)
EXPECTED_ITEMS_BY_TEAM = {
    'Jorge Team': [
        'A1233', 'A1635', 'A1615', 'A1619', 'A1861', 'A1639', 'A1574', 'A1490',
        'A1634', 'A1600', 'A1942', 'A1631', 'A1315', 'A1691', 'A1693', 'A1696',
        'A1646', 'A1640', 'A1176', 'A1903', 'A1011', 'A1650', 'A1641'
    ],
    'Alejandro Team': [
        'A1564', 'A1563', 'A1566', 'A1549', 'A1280', 'A1612', 'A1545', 'A1575',
        'A1550', 'A1565', 'A1616', 'A1649', 'A1544', 'A1871'
    ],
    'Assembly Team': [
        'A1689', 'A1684', 'A1685', 'A1026', 'A1688', 'A1737', 'A1686', 'A1629',
        'A1385', 'A1678'
    ],
    'Samia Team': [
        'A1567', 'A1568', 'A1606', 'A1652', 'A1604', 'A1017', 'A1015', 'A1602',
        'A1603', 'A1633'
    ],
    'Rawad': [
        'A1876', 'A1935', 'A1925', 'A1628', 'A1553', 'A1907'
    ],
    'Theadora Team': [
        'A1632', 'A1613', 'A1607'
    ],
    'Butcher Team': [
        'A1499', 'A1614', 'A1547', 'A1543', 'A1647'
    ],
    'Grill Team': [
        'A1049', 'A1653', 'A1697', 'A1720', 'A1452', 'A1698', 'A1694', 'A1692',
        'A1690', 'A1551', 'A1643'
    ],
    'Bread Team': [
        'A1558', 'A1561'
    ]
}

# Reverse mapping: display_name -> original_name
TEAM_NAME_REVERSE_MAPPING = {v: k for k, v in TEAM_NAME_MAPPING.items()}


def get_display_team_name(original_name: str) -> str:
    """Convert original team name to display name"""
    return TEAM_NAME_MAPPING.get(original_name, original_name)


def get_original_team_name(display_name: str) -> str:
    """Convert display team name back to original name"""
    return TEAM_NAME_REVERSE_MAPPING.get(display_name, display_name)


def validate_items_for_team(team_name: str, items: List[Dict]) -> Dict[str, Any]:
    """Validate that expected items are present for a team"""
    expected_codes = EXPECTED_ITEMS_BY_TEAM.get(team_name, [])
    if not expected_codes:
        return {
            'has_validation': False,
            'found': [],
            'missing': [],
            'extra': []
        }
    
    # Get item codes from actual items
    actual_codes = [item.get('code', '') for item in items if item.get('code')]
    
    # Find matches
    found = [code for code in expected_codes if code in actual_codes]
    missing = [code for code in expected_codes if code not in actual_codes]
    extra = [code for code in actual_codes if code not in expected_codes]
    
    return {
        'has_validation': True,
        'found': found,
        'missing': missing,
        'extra': extra,
        'total_expected': len(expected_codes),
        'total_found': len(found),
        'coverage': (len(found) / len(expected_codes) * 100) if expected_codes else 0
    }


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


def get_gdocs_manager():
    """Initialize and return GDocsManager instance"""
    if 'gdocs_manager' not in st.session_state or st.session_state.gdocs_manager is None:
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
        if not creds_path:
            return None
        
        # Convert relative path to absolute path
        if not os.path.isabs(creds_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            logger.error(f"Credentials file not found at: {creds_path}")
            return None
        
        try:
            gdocs_manager = GDocsManager(credentials_path=creds_path)
            gdocs_manager.authenticate()
            st.session_state.gdocs_manager = gdocs_manager
            return gdocs_manager
        except Exception as e:
            logger.error(f"Error authenticating with Google Docs: {e}")
            return None
    
    return st.session_state.gdocs_manager


def find_recipe_by_item_code(item_code, item_title, doc_url):
    """Find recipe in Google Docs by item code or title"""
    gdocs_manager = get_gdocs_manager()
    if not gdocs_manager:
        return None
    
    try:
        text_content, document = gdocs_manager.get_document_content(doc_url)
        lines = text_content.split('\n')
        
        # Search for recipe by code or title
        current_recipe = None
        found_recipe = False
        in_recipe = False
        
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            
            # Check if this line matches the item code or title
            if item_code.lower() in line_stripped.lower() or item_title.lower() in line_stripped.lower():
                # Check if it looks like a recipe title
                if gdocs_manager._is_recipe_title(line_stripped) or line_stripped.endswith(':'):
                    found_recipe = True
                    in_recipe = True
                    current_recipe = {
                        'name': line_stripped.replace(':', '').strip(),
                        'ingredients': [],
                        'instructions': [],
                        'full_text': []
                    }
                    continue
            
            # If we're in a recipe section, collect content
            if in_recipe:
                # Stop if we hit another recipe title
                if line_stripped and gdocs_manager._is_recipe_title(line_stripped) and current_recipe['name'] not in line_stripped:
                    break
                
                if line_stripped:
                    current_recipe['full_text'].append(line_stripped)
                    
                    # Try to categorize as ingredient or instruction
                    if gdocs_manager._is_ingredient_line(line_stripped):
                        current_recipe['ingredients'].append(line_stripped)
                    elif gdocs_manager._is_instruction_line(line_stripped):
                        current_recipe['instructions'].append(line_stripped)
                    else:
                        # Default: add to instructions if it looks like a sentence
                        if line_stripped.endswith('.') or len(line_stripped) > 50:
                            current_recipe['instructions'].append(line_stripped)
                        else:
                            current_recipe['ingredients'].append(line_stripped)
        
        if found_recipe and current_recipe:
            return current_recipe
        
        return None
    except Exception as e:
        logger.error(f"Error finding recipe: {e}")
        return None


def generate_recipe_pdf_from_gdocs(recipe_data, item_code, item_title):
    """Generate PDF from Google Docs recipe data"""
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
        'RecipeTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=12,
        spaceBefore=16,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=8
    )
    
    # Add title
    title = Paragraph(item_title, title_style)
    elements.append(title)
    
    # Add item code
    code_para = Paragraph(f'<b>Item Code:</b> {item_code}', body_style)
    elements.append(code_para)
    elements.append(Spacer(1, 0.2*inch))
    
    # Add ingredients section
    if recipe_data.get('ingredients'):
        ingredients_title = Paragraph('INGREDIENTS', section_style)
        elements.append(ingredients_title)
        
        for ingredient in recipe_data['ingredients']:
            ing_para = Paragraph(f"• {ingredient}", body_style)
            elements.append(ing_para)
        
        elements.append(Spacer(1, 0.2*inch))
    
    # Add instructions section
    if recipe_data.get('instructions'):
        instructions_title = Paragraph('INSTRUCTIONS', section_style)
        elements.append(instructions_title)
        
        for i, instruction in enumerate(recipe_data['instructions'], 1):
            inst_para = Paragraph(f"{i}. {instruction}", body_style)
            elements.append(inst_para)
    
    # If no structured data, use full text
    if not recipe_data.get('ingredients') and not recipe_data.get('instructions'):
        if recipe_data.get('full_text'):
            for line in recipe_data['full_text']:
                para = Paragraph(line, body_style)
                elements.append(para)
    
    # Build PDF
    doc.build(elements)
    return pdf_filename


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
    
    # Add validation info in sidebar if a team is selected
    if st.session_state.selected_team:
        team_items = [item for item in filtered_items if item.get('custom_44680') == st.session_state.selected_team]
        validation = validate_items_for_team(st.session_state.selected_team, team_items)
        
        if validation['has_validation']:
            st.sidebar.divider()
            st.sidebar.header("📊 Item Validation")
            st.sidebar.metric("Items Found", f"{validation['total_found']}/{validation['total_expected']}")
            st.sidebar.metric("Coverage", f"{validation['coverage']:.1f}%")
            
            if validation['missing']:
                with st.sidebar.expander("⚠️ Missing Items"):
                    for code in validation['missing']:
                        st.sidebar.text(f"• {code}")
            
            if validation['extra']:
                with st.sidebar.expander("ℹ️ Extra Items"):
                    for code in validation['extra'][:10]:  # Show first 10
                        st.sidebar.text(f"• {code}")
                    if len(validation['extra']) > 10:
                        st.sidebar.text(f"... and {len(validation['extra']) - 10} more")

    # Filter items where is_raw = false
    filtered_items = [item for item in all_items if item.get('is_raw') == False]

    # Extract unique teams (custom_44680)
    teams = sorted(list(set([item.get('custom_44680') for item in filtered_items if item.get('custom_44680')])))
    
    # Sort teams by display name for better organization
    teams = sorted(teams, key=lambda t: get_display_team_name(t))

    # Step 1: Select Area
    st.header("Step 1: Select Area")
    
    # Create columns for team buttons (3 per row for better touchscreen UX)
    cols_per_row = 3
    team_cols = st.columns(cols_per_row)
    
    for idx, team in enumerate(teams):
        col_idx = idx % cols_per_row
        display_name = get_display_team_name(team)
        with team_cols[col_idx]:
            if st.button(
                display_name, 
                key=f"team_{team}",
                use_container_width=True,
                type="primary" if st.session_state.selected_team == team else "secondary"
            ):
                st.session_state.selected_team = team  # Store original name for filtering
                st.session_state.selected_category = None
                st.session_state.selected_item = None
                st.session_state.step = 2

    # Step 2: Select Category
    if st.session_state.selected_team:
        st.divider()
        st.header("Step 2: Select Category")
        display_team_name = get_display_team_name(st.session_state.selected_team)
        st.info(f"**Selected Area:** {display_team_name}")
        
        # Filter items by selected team (use original name for filtering)
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
        display_team_name = get_display_team_name(st.session_state.selected_team)
        st.info(f"**Area:** {display_team_name} | **Category:** {st.session_state.selected_category}")
        
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
        
        # Google Docs Recipe Integration - Print Recipe Button (prominent)
        recipes_doc_url = secrets.get('RECIPES_DOCS_URL', '')
        use_google_docs_recipes = secrets.get('USE_GOOGLE_DOCS_RECIPES', False)
        
        if use_google_docs_recipes and recipes_doc_url:
            # Print Recipe Button - Always visible and prominent
            if st.button("🖨️ Print Recipe PDF", type="primary", use_container_width=True, key="print_recipe_main"):
                with st.spinner("Generating recipe PDF..."):
                    recipe = find_recipe_by_item_code(
                        selected_item.get('code'),
                        selected_item.get('title'),
                        recipes_doc_url
                    )
                    
                    if recipe:
                        try:
                            pdf_file = generate_recipe_pdf_from_gdocs(
                                recipe,
                                selected_item.get('code'),
                                selected_item.get('title')
                            )
                            
                            with open(pdf_file, 'rb') as f:
                                pdf_bytes = f.read()
                                st.download_button(
                                    label="📥 Download Recipe PDF",
                                    data=pdf_bytes,
                                    file_name=f"{selected_item.get('code')}_recipe.pdf",
                                    mime="application/pdf",
                                    type="primary",
                                    use_container_width=True
                                )
                            
                            # Clean up temp file
                            try:
                                os.unlink(pdf_file)
                            except:
                                pass
                        except Exception as e:
                            st.error(f"Error generating PDF: {str(e)}")
                    else:
                        st.warning(f"Recipe not found for item: {selected_item.get('code')} ({selected_item.get('title')})")
                        st.info("💡 Make sure the recipe title in Google Docs matches the item code or item name")
            
            # View Recipe Button (secondary option)
            if st.button("📄 View Recipe from Google Docs", use_container_width=True, key="view_recipe_main"):
                with st.spinner("Loading recipe from Google Docs..."):
                    recipe = find_recipe_by_item_code(
                        selected_item.get('code'),
                        selected_item.get('title'),
                        recipes_doc_url
                    )
                    
                    if recipe:
                        st.session_state.current_recipe = recipe
                        st.session_state.show_recipe = True
                        st.rerun()
                    else:
                        st.warning(f"Recipe not found for item: {selected_item.get('code')} ({selected_item.get('title')})")
                        st.info("💡 Make sure the recipe title in Google Docs matches the item code or item name")
        
        # Display recipe if available
        if st.session_state.get('show_recipe') and st.session_state.get('current_recipe'):
            st.divider()
            st.header("📋 Recipe from Google Docs")
            recipe = st.session_state.current_recipe
            
            if recipe.get('ingredients'):
                st.subheader("Ingredients")
                for ingredient in recipe['ingredients']:
                    st.write(f"• {ingredient}")
            
            if recipe.get('instructions'):
                st.subheader("Instructions")
                for i, instruction in enumerate(recipe['instructions'], 1):
                    st.write(f"{i}. {instruction}")
            
            if recipe.get('full_text') and not recipe.get('ingredients') and not recipe.get('instructions'):
                st.subheader("Recipe")
                for line in recipe['full_text']:
                    st.write(line)
            
            if st.button("❌ Close Recipe"):
                st.session_state.show_recipe = False
                st.session_state.current_recipe = None
                st.rerun()
        
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

