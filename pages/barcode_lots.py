import streamlit as st
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from barcode import Code128
from barcode.writer import ImageWriter
import io
from PIL import Image
import os
from datetime import datetime
import base64
from shared.api_manager import APIManager

# Initialize API manager
api = APIManager()

# Initialize session state for caching
if 'containers_cache' not in st.session_state:
    st.session_state.containers_cache = None
if 'item_details_cache' not in st.session_state:
    st.session_state.item_details_cache = {}

class NoTextImageWriter(ImageWriter):
    """Custom barcode writer that omits text below the barcode"""
    def _init(self, code):
        options = super()._init(code)
        self.text = ''  # Disable text
        return options

def is_weight_uom(uom: str) -> bool:
    """Check if the UOM is weight-based"""
    return uom.lower() in ['kg', 'gr', 'lb']

def convert_weight(value: float, from_uom: str, to_uom: str) -> float:
    """Convert weight between different units"""
    if not is_weight_uom(from_uom) or not is_weight_uom(to_uom):
        return float(value)

    # Convert everything to grams first
    gram_conversions = {
        'gr': 1.0,
        'kg': 1000.0,
        'lb': 453.592
    }

    # Convert to grams - ensure we're working with float
    grams = float(value) * gram_conversions[from_uom.lower()]

    # Convert to target unit
    return grams / gram_conversions[to_uom.lower()]

def get_cached_containers():
    """Get containers with caching"""
    if st.session_state.containers_cache is None:
        st.session_state.containers_cache = api.get_containers()
    return st.session_state.containers_cache

def get_cached_item_details(lot_number: str):
    """Get item details with caching"""
    if lot_number not in st.session_state.item_details_cache:
        st.session_state.item_details_cache[lot_number] = api.get_complete_lot_details(lot_number)
    return st.session_state.item_details_cache[lot_number]

def generate_label_pdf(lot_number: str, item_name: str, item_code: str,
                      net_weight: float, uom: str, expiry_timestamp: int = None) -> io.BytesIO:
    """Generate a PDF label with barcode and item information"""
    buffer = io.BytesIO()

    # Create canvas for PDF
    c = canvas.Canvas(buffer, pagesize=(3 * inch, 1 * inch))

    # Generate barcode without text
    barcode_buffer = io.BytesIO()
    barcode = Code128(lot_number, writer=NoTextImageWriter())
    barcode.write(barcode_buffer)
    barcode_buffer.seek(0)

    # Load and save barcode image temporarily
    barcode_image = Image.open(barcode_buffer)
    barcode_image = barcode_image.convert('L')  # Convert to grayscale
    temp_path = f"{lot_number}_barcode.png"
    barcode_image.save(temp_path)

    # Format expiry date if timestamp exists
    expiry_date = ""
    if expiry_timestamp:
        expiry_date = datetime.fromtimestamp(expiry_timestamp).strftime("%d/%m/%Y")

    # Draw content on PDF
    c.setFont("Helvetica", 20)
    c.drawString(0.05 * inch, 0.45 * inch, f"{lot_number}")

    # Draw expiry date if available
    '''
    if expiry_date:
        c.setFont("Helvetica", 18)
        c.drawString(0.05 * inch, 0.1 * inch, f"Exp: {expiry_date}")
        '''

    c.setFont("Helvetica", 12)
    # Adjust font size if item name is too long
    text_width = c.stringWidth(item_name, "Helvetica", 12)
    if text_width > 1.5 * inch:
        font_size = 12 * (1.5 * inch / text_width)
        c.setFont("Helvetica", font_size)
    c.drawString(1.5 * inch, 0.75 * inch, f"{item_name}")

    c.setFont("Helvetica", 12)
    if net_weight == 0:
        # If weight is zero, only display the UOM
        c.drawString(1.5 * inch, 0.35 * inch, f"{uom}")
    else:
        # If weight is non-zero, display both weight and UOM
        c.drawString(1.5 * inch, 0.35 * inch, f"{net_weight:.2f} {uom}")

    # Draw item code
    c.setFont("Helvetica", 12)
    c.drawString(2.2 * inch, 0.05 * inch, f"{item_code}")

    # Draw barcode
    c.drawImage(temp_path, 0 * inch, 0.70 * inch, width=1.5 * inch, height=0.30 * inch)

    c.showPage()
    c.save()

    # Clean up temporary file
    if os.path.exists(temp_path):
        os.remove(temp_path)

    buffer.seek(0)
    return buffer

def clear_cache():
    """Clear the session state cache"""
    st.session_state.containers_cache = None
    st.session_state.item_details_cache = {}

def main():
    st.title("Barcode Generator")

    # Add cache clear button in sidebar
    with st.sidebar:
        if st.button("Clear Cache"):
            clear_cache()
            st.success("Cache cleared!")

    # Lot number input
    lot_number = st.text_input("Enter Lot Number").strip()

    if lot_number:
        # Get item details using cache
        item_details = get_cached_item_details(lot_number)

        if item_details:
            # Display item details
            st.subheader(item_details['item_name'])
            if item_details['icon']:
                st.image(item_details['icon'], width=200)

            # Weight input and UOM display
            col1, col2 = st.columns(2)
            with col1:
                weight = st.number_input("Weight", min_value=0.0, step=0.1)
            with col2:
                unit_options = {f"{unit['unit']} ({unit['source']})": unit['unit']
                              for unit in item_details['available_units']}

                # Find default unit in options
                default_index = 0
                for i, (label, unit) in enumerate(unit_options.items()):
                    if unit == item_details['default_unit']:
                        default_index = i
                        break

                selected_unit_label = st.selectbox(
                    "UOM",
                    options=list(unit_options.keys()),
                    index=default_index
                )
                selected_unit = unit_options[selected_unit_label]

            # Initialize net_weight to gross weight
            net_weight = float(weight)

            # Container selection and weight calculation only for weight-based UOMs
            if is_weight_uom(selected_unit):
                # Get containers from cache
                containers = get_cached_containers()

                container_options = {
                    f"{c['container_name']} - {c['container_code']} - {c['weight']} {c['weight_uom']}": c
                    for c in containers
                }

                if container_options:
                    default_index = 0
                    for i, c in enumerate(containers):
                        if c['container_id'] == item_details.get('default_container_id'):
                            default_index = i
                            break

                    selected_container = st.selectbox(
                        "Select Container",
                        options=list(container_options.keys()),
                        index=default_index,
                        key="container_selector"
                    )

                    # Display container image
                    container = container_options[selected_container]
                    if container['image']:
                        st.image(container['image'], width=200)

                    # Calculate net weight
                    container_weight = convert_weight(
                        float(container['weight']),
                        container['weight_uom'],
                        selected_unit  # Use selected_unit instead of item_details['uom']
                    )
                    net_weight = float(weight) - container_weight
                else:
                    st.error("No container options available")

            # Display net weight with selected unit
            st.write(f"Net Weight: {net_weight:.2f} {selected_unit}")

            # Barcode generation section
            if st.button("Generate Barcode"):
                try:
                    pdf_buffer = generate_label_pdf(
                        lot_number,
                        item_details['item_name'],
                        item_details['item_code'],
                        net_weight,
                        selected_unit,
                        item_details.get('mrpeasy_expiry_timestamp')
                    )

                    # Create columns for the buttons
                    st.write("PDF Actions:")
                    button_cols = st.columns(2)

                    with button_cols[0]:
                        # Create a button that looks native to Streamlit
                        base64_pdf = base64.b64encode(pdf_buffer.getvalue()).decode('utf-8')
                        js_code = f"""
                            <script>
                            function openPDF() {{
                                const base64pdf = "{base64_pdf}";
                                const byteCharacters = atob(base64pdf);
                                const byteNumbers = new Array(byteCharacters.length);
                                for (let i = 0; i < byteCharacters.length; i++) {{
                                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                                }}
                                const byteArray = new Uint8Array(byteNumbers);
                                const file = new Blob([byteArray], {{type: 'application/pdf'}});
                                const fileURL = URL.createObjectURL(file);
                                window.open(fileURL);
                            }}
                            </script>
                            <button 
                                onclick="openPDF()" 
                                style="
                                    background-color: #FF4B4B;
                                    color: white;
                                    padding: 0.5rem 1rem;
                                    border-radius: 0.3rem;
                                    border: none;
                                    cursor: pointer;
                                "
                            >
                                Preview Label
                            </button>
                        """
                        st.components.v1.html(js_code, height=50)

                    with button_cols[1]:
                        # Reset buffer position for download
                        pdf_buffer.seek(0)
                        st.download_button(
                            label="Download PDF",
                            data=pdf_buffer,
                            file_name=f"barcode_{lot_number}.pdf",
                            mime="application/pdf",
                            use_container_width=True
                        )

                except Exception as e:
                    st.error(f"Error generating barcode: {str(e)}")

if __name__ == "__main__":
    main()