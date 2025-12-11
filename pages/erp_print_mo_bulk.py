# erp_print_mo.py
import streamlit as st
import logging
import base64
from typing import Optional, List
from enum import Enum

# Import our separated components
from organizer.print_mo.models import ManufacturingOrder, DataValidationError
from organizer.print_mo.pdf_generator_bulk import PDFGenerator
from organizer.print_mo.pdf_generator_bulk_simplified import PDFGenerator as SimplifiedPDFGenerator
from shared.api_manager import APIManager
from organizer.print_mo.cache_manager import CacheManager

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class DisplayText(str, Enum):
    """Enum for display text strings"""
    TITLE = "Manufacturing Order Details"
    NOT_SPECIFIED = "Not specified"
    NO_DATA = "N/A"
    MOS_FOUND = "Manufacturing Orders Found!"
    NO_MOS_FOUND = "No manufacturing orders found with the provided codes."
    ENTER_MOS = "Please enter manufacturing order numbers, one per line."
    LOADING_CACHE = "Loading data... This may take a moment."
    CACHE_SUCCESS = "Data loaded successfully!"
    CACHE_ERROR = "Error loading data. Some information may be missing."
    PDF_SUCCESS = "Successfully generated {} PDF for {} manufacturing orders."
    PDF_ERROR = "Error generating PDF report"
    UNEXPECTED_ERROR = "An unexpected error occurred: {}"
    DEBUG_TITLE = "Debug Information"
    DEBUG_RAW_DATA = "Raw API Response Data"
    DEBUG_PROCESSED = "Processed Manufacturing Orders"
    CACHE_STATUS = "Cache Status"
    CACHE_LAST_UPDATED = "Cache Last Updated: {}"
    CACHE_NEEDS_REFRESH = "Cache needs refresh"
    CACHE_CLEARED = "Cache cleared successfully"
    CLEAR_CACHE = "Clear Cache"

def initialize_session_state():
    """Initialize session state variables"""
    if 'mo_data_list' not in st.session_state:
        st.session_state.mo_data_list = []
    if 'cache_initialized' not in st.session_state:
        st.session_state.cache_initialized = False
    if 'debug_data' not in st.session_state:
        st.session_state.debug_data = []
    if 'debug_processed_data' not in st.session_state:
        st.session_state.debug_processed_data = []


def initialize_cache(api: APIManager) -> bool:
    """Initialize the cache with required data"""
    try:
        cache_manager = CacheManager()

        # Check if cache needs refreshing
        if cache_manager.needs_refresh():
            with st.spinner(DisplayText.LOADING_CACHE):
                cache_manager.initialize_cache(api)
                st.success(DisplayText.CACHE_SUCCESS)
        return True
    except Exception as e:
        logger.error(f"Cache initialization error: {str(e)}")
        st.error(DisplayText.CACHE_ERROR)
        return False

def display_cache_status():
    """Display cache status in sidebar"""
    cache_manager = CacheManager()

    st.sidebar.header(DisplayText.CACHE_STATUS)

    # Display last updated time
    if cache_manager.cache.last_updated:
        last_updated = cache_manager.cache.last_updated.strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.text(DisplayText.CACHE_LAST_UPDATED.format(last_updated))

        if cache_manager.needs_refresh():
            st.sidebar.warning(DisplayText.CACHE_NEEDS_REFRESH)

    # Add clear cache button
    if st.sidebar.button(DisplayText.CLEAR_CACHE):
        cache_manager.clear_cache()
        st.sidebar.success(DisplayText.CACHE_CLEARED)
        st.rerun()


def fetch_mo_data(api: APIManager, mo_code: str) -> Optional[ManufacturingOrder]:
    """Fetch manufacturing order data from API"""
    try:
        # Get basic MO info
        basic_mo_data = api.get_manufacturing_order_by_code(mo_code)
        if not basic_mo_data:
            return None

        # Store raw data in session state for debugging
        if 'debug_data' not in st.session_state:
            st.session_state.debug_data = []

        # Get detailed information using the ID
        man_ord_id = basic_mo_data.get('man_ord_id')
        detailed_mo_data = api.get_manufacturing_order_details(man_ord_id)

        # Store both basic and detailed data for debugging
        debug_entry = {
            'mo_code': mo_code,
            'basic_data': basic_mo_data,
            'detailed_data': detailed_mo_data
        }
        st.session_state.debug_data.append(debug_entry)

        # Convert raw data to ManufacturingOrder object
        mo = ManufacturingOrder.from_dict(basic_mo_data, detailed_mo_data, api)

        # Store processed data for debugging
        if mo:
            if 'debug_processed_data' not in st.session_state:
                st.session_state.debug_processed_data = []
            st.session_state.debug_processed_data.append({
                'mo_code': mo_code,
                'processed_data': {
                    'code': mo.code,
                    'item_code': mo.item_code,
                    'item_title': mo.item_title,
                    'quantity': mo.quantity,
                    'unit': mo.unit,
                    'target_lots': [{'lot_id': lot.lot_id, 'code': lot.code, 'location': lot.location}
                                  for lot in mo.target_lots],
                    'parts': [{
                        'lots': [{
                            'lot_id': lot.lot_id,
                            'code': lot.code,
                            'item_code': lot.item_code,
                            'item_title': lot.item_title,
                            'location': lot.location,
                            'booked': lot.booked
                        } for lot in part.lots]
                    } for part in mo.parts],
                    'notes': [{'note_id': note.note_id, 'author': note.author, 'text': note.text}
                             for note in mo.notes]
                }
            })

        return mo

    except Exception as e:
        logger.error(f"Error fetching MO data: {str(e)}")
        return None


def fetch_multiple_mos(api: APIManager, mo_codes: List[str]) -> List[ManufacturingOrder]:
    """Fetch multiple manufacturing orders"""
    valid_mos = []

    # Initialize cache first
    if not initialize_cache(api):
        return valid_mos

    # Now process the manufacturing orders
    progress_bar = st.progress(0)
    total_mos = len([code for code in mo_codes if code.strip()])

    for i, mo_code in enumerate(mo_codes, 1):
        mo_code = mo_code.strip()
        if mo_code:  # Skip empty lines
            mo = fetch_mo_data(api, mo_code)
            if mo:
                valid_mos.append(mo)
            progress_bar.progress(i / total_mos)

    progress_bar.empty()
    return valid_mos


def create_combined_pdf(mos: List[ManufacturingOrder], simplified: bool = False) -> bytes:
    """Generate a combined PDF for multiple manufacturing orders"""
    if simplified:
        pdf_generator = SimplifiedPDFGenerator()
    else:
        pdf_generator = PDFGenerator()
    return pdf_generator.create_combined_pdf(mos)


def create_pdf_viewer(pdf_buffer: bytes, pdf_type: str) -> None:
    """Create and display PDF viewer component"""
    pdf_base64 = base64.b64encode(pdf_buffer).decode('utf-8')

    # Create a unique function name for each PDF viewer
    function_name = f"openPDF_{pdf_type}"
    button_text = f"View {pdf_type} PDF"

    html_code = f"""
        <script>
        function {function_name}() {{
            const base64pdf = "{pdf_base64}";
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
            onclick="{function_name}()" 
            style="
                background-color: #FF4B4B;
                color: white;
                padding: 0.5rem 1rem;
                border-radius: 0.3rem;
                border: none;
                cursor: pointer;
                width: 100%;
            "
        >
            {button_text}
        </button>
    """
    st.components.v1.html(html_code, height=50)


def display_debug_info():
    """Display debug information in collapsible sections"""
    with st.expander(DisplayText.DEBUG_TITLE, expanded=False):
        # Display Raw API Response Data
        st.subheader(DisplayText.DEBUG_RAW_DATA)
        if hasattr(st.session_state, 'debug_data') and st.session_state.debug_data:
            for entry in st.session_state.debug_data:
                st.markdown(f"### Manufacturing Order: {entry['mo_code']}")
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown("#### Basic Data")
                    st.json(entry['basic_data'])
                with col2:
                    st.markdown("#### Detailed Data")
                    st.json(entry['detailed_data'])
                st.markdown("---")
        else:
            st.write("No raw data available")

        # Display Processed Manufacturing Orders
        st.subheader(DisplayText.DEBUG_PROCESSED)
        if hasattr(st.session_state, 'debug_processed_data') and st.session_state.debug_processed_data:
            for entry in st.session_state.debug_processed_data:
                st.markdown(f"### Manufacturing Order: {entry['mo_code']}")
                st.json(entry['processed_data'])
                st.markdown("---")
        else:
            st.write("No processed data available")

def main() -> None:
    """Main application function"""
    try:
        st.title(DisplayText.TITLE)

        # Initialize session state
        initialize_session_state()

        # Initialize API Manager
        api = APIManager()

        # Display cache status and controls in sidebar
        display_cache_status()

        # Create text area for multiple MO codes
        mo_codes_input = st.text_area(
            "Enter Manufacturing Order Numbers (one per line):",
            help="Enter each manufacturing order number on a new line"
        )

        # Create columns for buttons
        col1, col2 = st.columns(2)

        # Add buttons in separate columns
        with col1:
            get_details = st.button("Generate Detailed PDF")
        with col2:
            get_simplified = st.button("Generate Simplified PDF")

        if (get_details or get_simplified) and mo_codes_input:
            # Clear previous debug data
            st.session_state.debug_data = []
            st.session_state.debug_processed_data = []

            # Split input into list of MO codes and clean them
            mo_codes = [code.strip() for code in mo_codes_input.split('\n')]
            mo_codes = [code for code in mo_codes if code]  # Remove empty lines

            if mo_codes:
                # Fetch all valid MOs
                mos = fetch_multiple_mos(api, mo_codes)

                if mos:
                    st.session_state.mo_data_list = mos

                    # Generate combined PDF
                    try:
                        if get_details:
                            with st.spinner("Generating Detailed PDF..."):
                                pdf_buffer = create_combined_pdf(mos, simplified=False)
                                create_pdf_viewer(pdf_buffer, "Detailed")
                                st.success(DisplayText.PDF_SUCCESS.format("Detailed", len(mos)))

                        if get_simplified:
                            with st.spinner("Generating Simplified PDF..."):
                                pdf_buffer = create_combined_pdf(mos, simplified=True)
                                create_pdf_viewer(pdf_buffer, "Simplified")
                                st.success(DisplayText.PDF_SUCCESS.format("Simplified", len(mos)))

                    except Exception as e:
                        logger.error(f"PDF generation error: {str(e)}")
                        st.error(DisplayText.PDF_ERROR)
                else:
                    st.error(DisplayText.NO_MOS_FOUND)
            else:
                st.warning(DisplayText.ENTER_MOS)

            # Display debug information after PDF generation
            display_debug_info()

        elif get_details or get_simplified:
            st.warning(DisplayText.ENTER_MOS)

    except DataValidationError as e:
        logger.error(f"Data validation error: {str(e)}")
        st.error(f"Data validation error: {str(e)}")
    except Exception as e:
        logger.error(f"Application error: {str(e)}")
        st.error(DisplayText.UNEXPECTED_ERROR.format(str(e)))


if __name__ == "__main__":
    main()