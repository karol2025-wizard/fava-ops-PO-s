import streamlit as st
from shared.api_manager import APIManager
from datetime import datetime

# Page configuration
st.set_page_config(
    page_title="Batch Order Creation",
    page_icon="📦",
    layout="wide"
)

st.header("Batch Order Creation")
api_manager = APIManager()

st.write("Enter orders, one per line, in the format: item_code, quantity, start_date (MM/DD/YYYY)")
orders_input = st.text_area("Example: A1642,400,1/21/2025", height=150)

# Initialize session state to track button clicks
if 'button_clicked' not in st.session_state:
    st.session_state.button_clicked = False

def parse_date_to_unix_timestamp(date_str):
    try:
        # Parse the date string to datetime object
        dt = datetime.strptime(date_str.strip(), '%m/%d/%Y')
        # Convert to Unix timestamp (seconds since epoch)
        return int(dt.timestamp())
    except ValueError as e:
        raise ValueError(f"Invalid date format. Please use MM/DD/YYYY format. Error: {str(e)}")

# Define a function to handle order creation
def create_orders():
    st.session_state.button_clicked = True
    results = []
    # Get orders from the text area input
    orders = orders_input.split('\n')
    for order in orders:
        if order.strip():
            try:
                # Split the input line and handle potential extra whitespace
                parts = [part.strip() for part in order.split(',')]

                if len(parts) != 3:
                    raise ValueError("Each line must contain item_code, quantity, and start_date separated by commas")

                item_code, quantity, start_date = parts

                # Parse and validate the date, converting to Unix timestamp
                unix_timestamp = parse_date_to_unix_timestamp(start_date)

                # Create the order with the Unix timestamp using item_code instead of article_id
                response = api_manager.create_manufacturing_order(
                    item_code=item_code,
                    quantity=float(quantity),
                    assigned_id=1,
                    start_date=unix_timestamp
                )

                if response.ok:
                    results.append(f"Order for Item Code {item_code} succeeded.")
                else:
                    results.append(f"Order for Item Code {item_code} failed: {response.text}")
            except ValueError as e:
                results.append(f"Failed to process line '{order}': {str(e)}")
            except Exception as e:
                results.append(f"Unexpected error processing line '{order}': {str(e)}")

    if results:
        for result in results:
            st.write(result)


    st.session_state.button_clicked = False

# Disable the button if it's already clicked
st.button("Create Manufacturing Orders", on_click=create_orders, disabled=st.session_state.button_clicked)
