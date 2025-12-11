import streamlit as st
from reportlab.lib.pagesizes import inch
from reportlab.pdfgen import canvas
from barcode import Code128
from barcode.writer import ImageWriter
import io
from PIL import Image
from datetime import datetime, date, timedelta
import math
from PyPDF2 import PdfReader, PdfWriter
import base64
from shared.api_manager import APIManager
from streamlit.components.v1 import html
from reportlab.lib.utils import ImageReader
import time

# Get today's date
current_datetime = datetime.now().strftime('%Y%m%d_%H%M%S')

# Initialize API Manager (this is lightweight without any API calls)
api_manager = APIManager()

# Initialize cache timestamps in session state
if 'cache_last_updated' not in st.session_state:
    st.session_state.cache_last_updated = {
        'stock_lots': None,
        'products': None
    }


# Define cache functions with Streamlit's built-in cache decorators
# TTL (Time To Live) set to 1 hour (3600 seconds)
@st.cache_data(ttl=3600)
def fetch_stock_lots():
    """Fetch stock lots with Streamlit's caching"""
    with st.spinner('Loading stock lots data...'):
        data = api_manager.fetch_stock_lots()
        # Update the timestamp when this cache was last refreshed
        st.session_state.cache_last_updated['stock_lots'] = datetime.now()
        return data


@st.cache_data(ttl=3600)
def fetch_all_products():
    """Fetch all products with Streamlit's caching"""
    with st.spinner('Loading product data...'):
        data = api_manager.fetch_all_products()
        # Update the timestamp when this cache was last refreshed
        st.session_state.cache_last_updated['products'] = datetime.now()
        return data


def clear_cache():
    """Clear all Streamlit caches and reset timestamps"""
    # Clear Streamlit's cache
    st.cache_data.clear()
    # Reset our timestamps
    st.session_state.cache_last_updated['stock_lots'] = None
    st.session_state.cache_last_updated['products'] = None
    st.success("Cache cleared successfully!")


def format_time_ago(timestamp):
    """Format how long ago a timestamp was, or 'Not loaded' if None"""
    if timestamp is None:
        return "Not loaded"

    now = datetime.now()
    delta = now - timestamp

    if delta.days > 0:
        return f"{delta.days} day{'s' if delta.days > 1 else ''} ago"
    elif delta.seconds >= 3600:
        hours = delta.seconds // 3600
        return f"{hours} hour{'s' if hours > 1 else ''} ago"
    elif delta.seconds >= 60:
        minutes = delta.seconds // 60
        return f"{minutes} minute{'s' if minutes > 1 else ''} ago"
    else:
        return "Just now"


def get_item_from_cache(item_code: str) -> dict:
    """Get item details from cache"""
    items = fetch_all_products()
    if items:
        return next((item for item in items if item.get('code') == item_code), None)
    return None


def get_lots_from_cache(item_code: str, po_id: int) -> list:
    """Get lots from cache filtered by item_code and po_id"""
    lots = fetch_stock_lots()
    if lots:
        return [lot for lot in lots
                if lot.get('item_code') == item_code
                and str(lot.get('pur_ord_id', '')) == str(po_id)]
    return []


class NoTextImageWriter(ImageWriter):
    def _init(self, code):
        options = super()._init(code)
        self.text = ''  # Disable text
        return options


def get_lot_and_expiry(item_code: str, po_id: int, receiving_date: date) -> tuple:
    lot_number = None
    expiry_date = None

    # Get matching lots from cache
    matching_lots = get_lots_from_cache(item_code, po_id)

    if matching_lots:
        lot = matching_lots[0]
        lot_number = lot.get('code')
        if lot.get('expiry'):
            expiry_date = datetime.fromtimestamp(lot['expiry']).strftime("%d/%m/%Y")

    if not expiry_date:
        # Get item details from cache
        item = get_item_from_cache(item_code)
        if item and item.get('shelf_life'):
            shelf_life = int(item['shelf_life'])
            expiry_date = (receiving_date + timedelta(days=shelf_life)).strftime("%d/%m/%Y")
        else:
            expiry_date = receiving_date.strftime("%d/%m/%Y")

    return lot_number, expiry_date


def parse_vendor_uom(vendor_uom):
    """
    Parse vendor UOM to extract case and container information
    Returns tuple of (is_case_of_containers, case_quantity, display_text)
    """
    if not vendor_uom or not isinstance(vendor_uom, str):
        return False, 1, vendor_uom

    # Check if starts with "Case of x containers of y"
    if vendor_uom.lower().startswith('case of '):
        try:
            # Split the string to extract numbers
            parts = vendor_uom.lower().split()
            if len(parts) >= 7 and parts[0] == 'case' and parts[1] == 'of' and parts[3] == 'containers' and parts[
                4] == 'of':
                case_quantity = int(parts[2])
                unit_info = ' '.join(parts[5:])  # Get the "y unit" part
                display_text = f"(Container of {unit_info})"
                return True, case_quantity, display_text
        except (ValueError, IndexError):
            pass

    return False, 1, vendor_uom


def generate_pdf(lot_number, sku, title, vendor_unit, quantity, vendor_quantity, uom, expiry_date):
    buffer = io.BytesIO()

    # Parse vendor unit information
    is_case_of_containers, case_quantity, display_unit = parse_vendor_uom(vendor_unit)

    # Calculate per-unit quantity
    if is_case_of_containers:
        per_unit_quantity = (quantity / vendor_quantity) / case_quantity
    else:
        per_unit_quantity = quantity / vendor_quantity if vendor_quantity != 0 else quantity

    try:
        # Create canvas with specific size
        c = canvas.Canvas(buffer, pagesize=(3 * inch, 1 * inch))

        # Generate barcode image
        barcode = Code128(lot_number, writer=NoTextImageWriter())

        # Create a BytesIO buffer for the barcode image
        barcode_buffer = io.BytesIO()
        barcode.write(barcode_buffer)
        barcode_buffer.seek(0)

        # Convert to PIL Image
        barcode_image = Image.open(barcode_buffer)

        # Create ImageReader object directly from PIL Image
        image_reader = ImageReader(barcode_image)

        # Draw content on PDF
        # Set default font sizes
        default_large_size = 20
        default_normal_size = 12
        max_text_width = 1.75 * inch

        # Draw lot number and expiry
        c.setFont("Helvetica", default_large_size)
        c.drawString(0.05 * inch, 0.5 * inch, f"{lot_number}")
        # c.drawString(0.05 * inch, 0.01 * inch, f"Exp: {expiry_date}")

        # Draw title with adjusted size
        title_font_size = min(default_normal_size,
                              default_normal_size * (
                                          max_text_width / c.stringWidth(title, "Helvetica", default_normal_size)))
        c.setFont("Helvetica", title_font_size)
        c.drawString(1.25 * inch, 0.75 * inch, f"{title}")

        # Draw vendor unit
        display_text = display_unit if is_case_of_containers else vendor_unit
        vendor_unit_font_size = min(default_normal_size,
                                    default_normal_size * (max_text_width / c.stringWidth(display_text, "Helvetica",
                                                                                          default_normal_size)))
        c.setFont("Helvetica", vendor_unit_font_size)
        c.drawString(1.25 * inch, 0.5 * inch, f"{display_text}")

        # Draw quantity and SKU
        c.setFont("Helvetica", default_normal_size)
        c.drawString(1.25 * inch, 0.25 * inch, f"≈{per_unit_quantity:.2f} {uom}")
        c.drawString(2.2 * inch, 0.05 * inch, f"{sku}")

        # Draw barcode using ImageReader
        c.drawImage(image_reader, 0 * inch, 0.70 * inch, width=1.27 * inch, height=0.30 * inch)

        # Finish the page and save
        c.showPage()
        c.save()

        # Clean up buffers
        barcode_buffer.close()

        # Reset main buffer position
        buffer.seek(0)
        return buffer

    except Exception as e:
        # Clean up in case of error
        buffer.close()
        raise e


def combine_pdfs(buffers):
    try:
        combined_buffer = io.BytesIO()
        pdf_writer = PdfWriter()

        # Create a list to store individual PDFReader objects
        readers = []

        # First pass: create all PDF readers
        for buffer in buffers:
            buffer.seek(0)
            reader = PdfReader(buffer)
            readers.append(reader)

        # Second pass: add pages from readers
        for reader in readers:
            for page in reader.pages:
                pdf_writer.add_page(page)

        # Write the combined PDF
        pdf_writer.write(combined_buffer)
        combined_buffer.seek(0)

        return combined_buffer

    except Exception as e:
        combined_buffer.close()
        raise e
    finally:
        # Clean up individual buffers
        for buffer in buffers:
            buffer.close()


def display_pdf(pdf_bytes):
    """Display PDF with preview button and download option"""
    # Create columns for the buttons
    st.write("PDF Actions:")
    button_cols = st.columns(2)

    with button_cols[0]:
        # Create preview button with JavaScript
        base64_pdf = base64.b64encode(pdf_bytes.read()).decode('utf-8')
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
                Preview Labels
            </button>
        """
        st.components.v1.html(js_code, height=50)

    with button_cols[1]:
        # Reset buffer position for download
        pdf_bytes.seek(0)
        st.download_button(
            label="Download PDF",
            data=pdf_bytes,
            file_name=f"generated_labels_{current_datetime}.pdf",
            mime="application/pdf",
            use_container_width=True
        )


st.title("PO Barcode Generator")

# Add cache status and refresh controls in an expander
with st.expander("Cache Status & Controls"):
    # Display cache status
    st.write("### Cache Status")

    # Create columns for status display
    col1, col2 = st.columns(2)

    with col1:
        st.write("**Products Data:**")
        products_status = format_time_ago(st.session_state.cache_last_updated['products'])
        if products_status == "Not loaded":
            st.info("Products cache not loaded yet")
        else:
            st.success(f"Last updated: {products_status}")

    with col2:
        st.write("**Stock Lots Data:**")
        lots_status = format_time_ago(st.session_state.cache_last_updated['stock_lots'])
        if lots_status == "Not loaded":
            st.info("Stock lots cache not loaded yet")
        else:
            st.success(f"Last updated: {lots_status}")

    # Add refresh button
    if st.button("Refresh All Caches"):
        clear_cache()
        # Force cache refresh by making the calls
        with st.spinner("Refreshing products cache..."):
            fetch_all_products()
        with st.spinner("Refreshing stock lots cache..."):
            fetch_stock_lots()
        st.success("All caches refreshed successfully!")
        st.rerun()  # Rerun the app to show updated timestamps

# Initialize session state for PDF display
if 'pdf_generated' not in st.session_state:
    st.session_state.pdf_generated = False
if 'pdf_buffer' not in st.session_state:
    st.session_state.pdf_buffer = None

try:
    # Add text input for PO number
    po_number = st.text_input("Enter PO Number")

    # Add receiving date picker
    receiving_date = st.date_input("Select Receiving Date", min_value=date.today())

    if st.button("Generate Labels"):
        if po_number and receiving_date:
            # Fetch the specific PO using the API Manager
            selected_po = api_manager.fetch_single_purchase_order(po_number)

            if selected_po and 'products' in selected_po:
                # The fetch_stock_lots() and fetch_all_products() functions
                # will be called on-demand by the helper functions when needed

                pdf_buffers = []
                processed_items = []  # Keep track of processed items for summary

                try:
                    for item in selected_po['products']:
                        try:
                            # Extract and validate vendor quantity
                            vendor_quantity = float(item.get('vendor_quantity', 1))
                            if vendor_quantity <= 0:
                                vendor_quantity = 1
                                st.warning(f"Invalid vendor quantity for {item.get('item_code')}. Using 1 as default.")

                            # Get lot number and expiry date
                            lot_number, expiry_date = get_lot_and_expiry(
                                item.get('item_code'),
                                selected_po.get('pur_ord_id'),
                                receiving_date
                            )

                            if not lot_number:
                                st.error(
                                    f"No lot number found for item {item.get('item_code')}. Skipping label generation for this item.")
                                continue

                            # Parse vendor unit information
                            is_case_of_containers, case_quantity, _ = parse_vendor_uom(item.get('vendor_unit', ''))

                            # Calculate total labels needed
                            if is_case_of_containers:
                                total_labels = vendor_quantity * case_quantity
                            else:
                                total_labels = vendor_quantity

                            # Apply maximum label limit
                            max_labels = 50  # Maximum labels per item
                            original_label_count = total_labels
                            total_labels = min(total_labels, max_labels)
                            ceiling_quantity = math.ceil(total_labels)

                            if original_label_count > max_labels:
                                st.warning(
                                    f"Label count for {item.get('item_code')} reduced from {original_label_count} to {max_labels} (maximum limit).")

                            # Generate labels for this item
                            successful_labels = 0
                            for i in range(int(ceiling_quantity)):
                                try:
                                    pdf_buffer = generate_pdf(
                                        lot_number=lot_number,
                                        sku=item.get('item_code', ''),
                                        title=item.get('item_title', ''),
                                        vendor_unit=item.get('vendor_unit', ''),
                                        quantity=float(item.get('quantity', 0)),
                                        vendor_quantity=vendor_quantity,
                                        uom=item.get('unit', ''),
                                        expiry_date=expiry_date
                                    )
                                    pdf_buffers.append(pdf_buffer)
                                    successful_labels += 1

                                except Exception as label_error:
                                    st.error(
                                        f"Error generating label {i + 1} for {item.get('item_code')}: {str(label_error)}")
                                    continue

                            # Record processed item information
                            processed_items.append({
                                'item_code': item.get('item_code', ''),
                                'requested_labels': original_label_count,
                                'generated_labels': successful_labels
                            })

                            # Show rounding information if applicable
                            if abs(total_labels - ceiling_quantity) > 0:
                                st.info(
                                    f"Rounded up from {total_labels:.1f} to {ceiling_quantity} labels for {item.get('item_code')}")

                        except Exception as item_error:
                            st.error(f"Error processing item {item.get('item_code')}: {str(item_error)}")
                            continue

                    # After processing all items, combine PDFs if we have any
                    if pdf_buffers:
                        try:
                            # Combine all generated PDFs
                            pdf_buffer_combined = combine_pdfs(pdf_buffers)
                            st.session_state.pdf_buffer = pdf_buffer_combined
                            st.session_state.pdf_generated = True

                            # Display success message and summary
                            st.success("Labels generated successfully!")

                            # Show summary of processed items
                            st.write("### Generation Summary")
                            for item in processed_items:
                                st.write(f"- {item['item_code']}: Generated {item['generated_labels']} labels" +
                                         (f" (reduced from {item['requested_labels']})"
                                          if item['requested_labels'] > item['generated_labels'] else ""))

                            # Display the PDF
                            display_pdf(st.session_state.pdf_buffer)

                        except Exception as combine_error:
                            st.error(f"Error combining PDFs: {str(combine_error)}")
                    else:
                        st.error("No valid items found for label generation.")

                except Exception as e:
                    st.error(f"An unexpected error occurred during label generation: {str(e)}")
                    import traceback

                    st.error(f"Traceback: {traceback.format_exc()}")

                finally:
                    # Clean up any remaining buffers
                    for buffer in pdf_buffers:
                        try:
                            buffer.close()
                        except:
                            pass  # Ignore errors during cleanup

            else:
                st.error("No items found for this PO.")
        else:
            st.error("Please select a PO Number and Receiving Date.")

except Exception as e:
    st.error(f"An error occurred: {str(e)}")
    import traceback

    st.error(f"Traceback: {traceback.format_exc()}")