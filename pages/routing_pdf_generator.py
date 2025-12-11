import streamlit as st
from shared.api_manager import APIManager
import json
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image
from reportlab.lib.enums import TA_LEFT, TA_CENTER
import tempfile
import os
from io import BytesIO
import requests
from PIL import Image as PILImage

st.header("Manufacturing Order Recipe PDF Generator")

# Initialize API manager
api_manager = APIManager()

# Initialize session state
if 'mo_data' not in st.session_state:
    st.session_state.mo_data = None
if 'mo_full_data' not in st.session_state:
    st.session_state.mo_full_data = None
if 'pdf_file' not in st.session_state:
    st.session_state.pdf_file = None
if 'items_cache' not in st.session_state:
    st.session_state.items_cache = None
if 'units_cache' not in st.session_state:
    st.session_state.units_cache = None

# Form for MO Code input
st.subheader("Enter Manufacturing Order Code")
mo_code = st.text_input("MO Code", placeholder="e.g., MO05696", help="Enter the Manufacturing Order code to fetch and generate recipe PDF")

if st.button("Fetch Manufacturing Order"):
    if not mo_code.strip():
        st.error("Please enter an MO Code")
    else:
        with st.spinner("Fetching Manufacturing Order details..."):
            # Fetch MO basic info
            mo_data = api_manager.get_manufacturing_order_by_code(mo_code.strip())
            
            if mo_data:
                st.session_state.mo_data = mo_data
                
                # Fetch full MO details
                mo_id = mo_data.get('man_ord_id')
                mo_full_data = api_manager.get_manufacturing_order_details(mo_id)
                st.session_state.mo_full_data = mo_full_data
                
                # Cache items and units if not already cached
                if not st.session_state.items_cache:
                    with st.spinner("Loading items database..."):
                        st.session_state.items_cache = api_manager.fetch_all_products()
                
                if not st.session_state.units_cache:
                    with st.spinner("Loading units database..."):
                        st.session_state.units_cache = api_manager.fetch_units()
                
                st.success(f"✅ Manufacturing Order {mo_code} fetched successfully!")
                
                # Display MO summary
                st.subheader("Manufacturing Order Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("MO Code", mo_data.get('code', 'N/A'))
                    st.metric("Item", mo_data.get('item_title', 'N/A'))
                
                with col2:
                    st.metric("Quantity", f"{mo_data.get('quantity', 0)} {mo_data.get('unit', '')}")
                    st.metric("Status", mo_data.get('status', 'N/A'))
                
                with col3:
                    st.metric("Parts Count", len(mo_full_data.get('parts', [])))
                    st.metric("Operations Count", len(mo_full_data.get('operations', [])))
                
            else:
                st.error(f"❌ Manufacturing Order '{mo_code}' not found. Please check the MO Code and try again.")

# Helper functions
def get_item_by_article_id(article_id, items_cache):
    """Get item details by article_id from cached items"""
    if not items_cache:
        return None
    for item in items_cache:
        if item.get('article_id') == article_id:
            return item
    return None

def get_unit_by_id(unit_id, units_cache):
    """Get unit name by unit_id from cached units"""
    if not units_cache or not unit_id:
        return 'kg'  # default
    
    for unit in units_cache:
        if unit.get('unit_id') == unit_id:
            return unit.get('title', 'kg')  # units API returns 'title' not 'unit'
    
    return 'kg'

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
        print(f"Error downloading image: {e}")
        return None

def generate_mo_recipe_pdf(mo_data, mo_full_data, items_cache, units_cache):
    """Generate PDF from MO data with BOM summary and operations"""
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
                        print(f"Error adding image to PDF: {e}")
        
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

# Generate PDF button (only show if MO data is available)
if st.session_state.mo_data and st.session_state.mo_full_data:
    st.divider()
    st.subheader("Generate Recipe PDF")
    
    mo_data = st.session_state.mo_data
    mo_full_data = st.session_state.mo_full_data
    
    st.info(f"""
    **PDF will be generated with:**
    - Item: {mo_data.get('item_title', 'N/A')}
    - MO Code: {mo_data.get('code', 'N/A')}
    - Quantity: {mo_data.get('quantity', 0)} {mo_data.get('unit', '')}
    - Parts/Ingredients: {len(mo_full_data.get('parts', []))}
    - Operations: {len(mo_full_data.get('operations', []))}
    """)
    
    if st.button("Generate PDF", type="primary"):
        with st.spinner("Generating PDF..."):
            try:
                pdf_file = generate_mo_recipe_pdf(
                    mo_data, 
                    mo_full_data, 
                    st.session_state.items_cache,
                    st.session_state.units_cache
                )
                st.session_state.pdf_file = pdf_file
                st.success("🎉 **Recipe PDF Generated Successfully!**")
                
                # Provide download button
                with open(pdf_file, 'rb') as f:
                    pdf_bytes = f.read()
                    st.download_button(
                        label="📥 Download Recipe PDF",
                        data=pdf_bytes,
                        file_name=f"{mo_data.get('item_code', 'recipe')}_{mo_data.get('code', 'recipe')}.pdf",
                        mime="application/pdf",
                        type="primary"
                    )
                
                # Display parts details
                st.subheader("Bill of Materials (Parts)")
                parts_display = []
                for part in mo_full_data.get('parts', []):
                    article_id = part.get('article_id')
                    item = get_item_by_article_id(article_id, st.session_state.items_cache)
                    if item:
                        unit_id = item.get('unit_id')
                        unit = get_unit_by_id(unit_id, st.session_state.units_cache)
                        parts_display.append({
                            'Item Code': item.get('code', 'N/A'),
                            'Item Title': item.get('title', 'N/A'),
                            'Quantity': part.get('booked', 0),
                            'Unit': unit
                        })
                if parts_display:
                    st.dataframe(parts_display, use_container_width=True)
                
                # Display operations details
                st.subheader("Operations Details")
                for i, operation in enumerate(mo_full_data.get('operations', [])):
                    with st.expander(f"Operation {i+1} - {operation.get('ord', 'N/A')}"):
                        operation_data = parse_operation_description(operation.get('description', '{}'))
                        if operation_data:
                            st.json(operation_data)
                        else:
                            st.write("No data available")
                
                # Reset button
                if st.button("Generate Another PDF"):
                    st.session_state.mo_data = None
                    st.session_state.mo_full_data = None
                    st.session_state.pdf_file = None
                    st.rerun()
                    
            except Exception as e:
                st.error(f"❌ An error occurred while generating the PDF: {str(e)}")
                st.exception(e)

# Help section
st.divider()
with st.expander("ℹ️ How to Use This Tool"):
    st.markdown("""
    ### Steps to Generate Recipe PDF:
    
    1. **Enter MO Code**: Input the Manufacturing Order code (e.g., MO05696)
    2. **Fetch MO**: Click "Fetch Manufacturing Order" to retrieve MO details
    3. **Review**: Check the MO summary, parts, and operations
    4. **Generate PDF**: Click "Generate PDF" to create the formatted document
    5. **Download**: Use the download button to save the PDF
    
    ### PDF Format:
    - **Title**: Item/Product name at the top
    - **Recipe Summary**: Table with ingredients, quantities, and units (from BOM/Parts)
    - **Operations Table**: Four columns (STEP, INGREDIENTS, PROCEDURE, EQUIPMENT)
    - **Images**: Equipment images included when available
    
    ### Data Sources:
    - **MO Basic Info**: From `/manufacturing-orders?code={code}`
    - **MO Full Details**: From `/manufacturing-orders/{id}`
    - **Items Database**: Cached from `/items` endpoint
    - **Units Database**: Cached from `/units` endpoint
    
    ### Requirements:
    - Manufacturing Order must exist in MRPEasy system
    - MO must have parts (BOM) and operations (routing)
    - Operations must have JSON-formatted descriptions
    """)
