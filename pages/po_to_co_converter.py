import streamlit as st
from shared.api_manager import APIManager
import json

def _format_quantity_display(value):
    try:
        num = float(value)
    except (TypeError, ValueError):
        return str(value) if value is not None else ''
    if num.is_integer():
        return str(int(num))
    return f"{num:.10f}".rstrip('0').rstrip('.')

st.header("Purchase Order to Customer Order Converter")

# Configuration - Markup variable at the top
st.subheader("Configuration")
markup = st.number_input("Markup Multiplier", min_value=1.0, max_value=5.0, value=1.1, step=0.1, 
                         help="Multiplier applied to PO prices when creating CO (e.g., 1.1 = 10% markup)")

st.divider()

# Initialize API manager
api_manager = APIManager()

# Initialize session state
if 'po_data' not in st.session_state:
    st.session_state.po_data = None
if 'processing' not in st.session_state:
    st.session_state.processing = False

# Form for PO Code input
st.subheader("Step 1: Enter Purchase Order Code")
po_code = st.text_input("PO Code", placeholder="e.g., PO01957", help="Enter the Purchase Order code to convert")

if st.button("Fetch Purchase Order", disabled=st.session_state.processing):
    if not po_code.strip():
        st.error("Please enter a PO Code")
    else:
        st.session_state.processing = True
        
        with st.spinner("Fetching Purchase Order details..."):
            # Fetch PO data using the API
            po_data = api_manager.fetch_single_purchase_order(po_code.strip())
            
            if po_data:
                st.session_state.po_data = po_data
                st.success(f"✅ Purchase Order {po_code} fetched successfully!")
                
                # Display PO summary
                st.subheader("Purchase Order Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("PO Code", po_data.get('code', 'N/A'))
                    st.metric("Vendor", po_data.get('vendor_title', 'N/A'))
                
                with col2:
                    st.metric("Total Price", f"${po_data.get('total_price', 0):,.2f}")
                    st.metric("Status", po_data.get('status', 'N/A'))
                
                with col3:
                    st.metric("Products Count", len(po_data.get('products', [])))
                    st.metric("Customer ID", po_data.get('custom_120112', 'N/A'))
                
                # Display products table
                if po_data.get('products'):
                    st.subheader("Products in Purchase Order")
                    products_data = []
                    
                    for product in po_data['products']:
                        products_data.append({
                            'Item Code': product.get('item_code', 'N/A'),
                            'Item Title': product.get('item_title', 'N/A'),
                            'Quantity': f"{product.get('quantity', 0)} {product.get('unit', '')}",
                            'Vendor Quantity': f"{product.get('vendor_quantity', 0)} {product.get('vendor_unit', '')}",
                            'Unit Price': f"${float(product.get('item_price', 0)):,.2f}",
                            'Total Price': f"${float(product.get('total_price', 0)):,.2f}"
                        })
                    
                    st.dataframe(products_data, use_container_width=True)
                
            else:
                st.error(f"❌ Purchase Order '{po_code}' not found. Please check the PO Code and try again.")
        
        st.session_state.processing = False

# Step 2: Create Customer Order (only show if PO data is available)
if st.session_state.po_data:
    st.divider()
    st.subheader("Step 2: Create Customer Order")
    
    po_data = st.session_state.po_data
    
    # Show what will be created
    st.info(f"""
    **Customer Order will be created with:**
    - Customer ID: {po_data.get('custom_120112', 'N/A')}
    - Status: 30 (Active)
    - Vendor: {po_data.get('vendor_title', 'N/A')}
    - Reference: {po_data.get('code', 'N/A')}
    - Notes: {po_data.get('custom_120110', 'N/A')} - {po_data.get('custom_120111', 'N/A')}
    - Markup: {markup}x
    """)
    
    if st.button("Create Customer Order", type="primary", disabled=st.session_state.processing):
        st.session_state.processing = True
        
        with st.spinner("Creating Customer Order..."):
            try:
                # Prepare customer order data
                products_list = []
                
                for product in po_data.get('products', []):
                    quantity = float(product.get('quantity', 0))
                    total_price_cur = float(product.get('total_price_cur', 0))
                    
                    # Calculate total price with markup (system will calculate item_price_cur automatically)
                    total_price_with_markup = round(total_price_cur * markup, 2)
                    
                    # Format description
                    vendor_quantity = _format_quantity_display(product.get('vendor_quantity', ''))
                    vendor_unit = product.get('vendor_unit', '')
                    description = f">>>>>>>>   {vendor_quantity} {vendor_unit}   <<<<<<<<"
                    
                    product_data = {
                        "article_id": product.get('article_id'),
                        "quantity": quantity,
                        "total_price_cur": total_price_with_markup,
                        "description": description
                    }
                    
                    products_list.append(product_data)
                
                # Prepare customer order payload
                # Handle customer_id conversion from decimal string format
                customer_id_raw = po_data.get('custom_120112', '1')
                try:
                    customer_id = int(float(customer_id_raw))  # Convert to float first, then int
                except (ValueError, TypeError):
                    customer_id = 1  # Default fallback
                
                customer_order_data = {
                    "customer_id": customer_id,
                    "status": 30,
                    "custom_89189": po_data.get('vendor_title', ''),
                    "notes": " - ".join([
                        part for part in [
                            po_data.get('custom_120110', ''),
                            po_data.get('custom_120111', '')
                        ] if part
                    ]),
                    "reference": po_data.get('code', ''),
                    "products": products_list
                }
                
                # Create the customer order
                response = api_manager.create_customer_order(customer_order_data)
                
                if response.status_code == 201:
                    try:
                        # Parse response to get the created order details
                        try:
                            created_order = response.json()
                            co_code = created_order.get('code', 'Unknown') if isinstance(created_order, dict) else 'Unknown'
                        except Exception as e:
                            st.warning(f"Could not parse response JSON, but order was created successfully: {e}")
                            co_code = 'Successfully Created'
                        
                        st.success(f"🎉 **Customer Order Created Successfully!**")
                        st.success(f"**Customer Order Code: {co_code}**")
                        
                        # Display creation summary
                        st.subheader("Creation Summary")
                        col1, col2 = st.columns(2)
                        
                        with col1:
                            st.metric("Original PO Total", f"${po_data.get('total_price', 0):,.2f}")
                            st.metric("Products Converted", len(products_list))
                        
                        with col2:
                            total_co_price = sum(float(p.get('total_price_cur', 0)) for p in products_list if isinstance(p, dict))
                            st.metric("New CO Total", f"${total_co_price:,.2f}")
                            st.metric("Markup Applied", f"{markup}x")
                        
                        # Show detailed product conversion
                        st.subheader("Product Conversion Details")
                        conversion_data = []
                        
                        for i, (original, converted) in enumerate(zip(po_data.get('products', []), products_list)):
                            if isinstance(converted, dict) and isinstance(original, dict):
                                conversion_data.append({
                                    'Item Code': original.get('item_code', 'N/A'),
                                    'Quantity': converted.get('quantity', 0),
                                    'Original Total': f"${float(original.get('total_price', 0)):,.2f}",
                                    'New Total': f"${converted.get('total_price_cur', 0):,.2f}",
                                    'Description': converted.get('description', 'N/A')
                                })
                        
                        if conversion_data:  # Only show dataframe if we have data
                            st.dataframe(conversion_data, use_container_width=True)
                        
                        # Reset session state for new conversion
                        if st.button("Convert Another PO"):
                            st.session_state.po_data = None
                            st.rerun()
                            
                    except Exception as success_error:
                        st.success(f"🎉 **Customer Order Created Successfully!**")
                        st.warning(f"Order was created but there was an issue displaying details: {success_error}")
                        st.info("The Customer Order has been successfully created in MRPEasy system.")
                
                else:
                    st.error(f"❌ Failed to create Customer Order")
                    st.error(f"Status Code: {response.status_code}")
                    st.error(f"Error: {response.text}")
                    
                    # Show debug information
                    with st.expander("Debug Information"):
                        st.json(customer_order_data)
                
            except Exception as e:
                st.error(f"❌ An error occurred while creating the Customer Order: {str(e)}")
                
                # Show debug information
                with st.expander("Debug Information"):
                    st.write("Exception:", str(e))
                    if 'customer_order_data' in locals():
                        st.json(customer_order_data)
        
        st.session_state.processing = False

# Help section
st.divider()
with st.expander("ℹ️ How to Use This Tool"):
    st.markdown("""
    ### Steps to Convert PO to CO:
    
    1. **Set Markup**: Adjust the markup multiplier at the top (default 1.1 = 10% markup)
    2. **Enter PO Code**: Input the Purchase Order code you want to convert
    3. **Fetch PO**: Click "Fetch Purchase Order" to retrieve PO details
    4. **Review**: Check the PO summary and products list
    5. **Create CO**: Click "Create Customer Order" to generate the new Customer Order
    
    ### Data Mapping:
    - **Customer ID**: Taken from PO custom field `custom_120112`
    - **Status**: Always set to 30 (Active)
    - **Vendor**: Copied from PO `vendor_title` to CO `custom_89189`
    - **Notes**: `custom_120110` - `custom_120111` (from PO)
    - **Reference**: Copied from PO `code`
    - **Product Prices**: Original PO prices multiplied by markup factor
    - **Description**: Formatted as ">>>>>>>>   [vendor_quantity] [vendor_unit]   <<<<<<<<"
    
    ### Requirements:
    - PO must exist in MRPEasy system
    - PO must have valid `custom_120112` (Customer ID)
    - PO must contain products to convert
    """)
