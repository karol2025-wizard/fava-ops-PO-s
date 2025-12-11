import streamlit as st
import requests
import json
import re
from datetime import datetime
from config import secrets
import sys
import os

# Add the project root to Python path to import shared modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from shared.database_manager import DatabaseManager

# Page configuration
st.set_page_config(
    page_title="MRP Easy - Manufacturing Order Processor",
    page_icon="🏭",
    layout="wide"
)

def fetch_pending_orders():
    """Fetch all pending orders from database (processed_at = NULL)."""
    try:
        db = DatabaseManager()
        query = """
        SELECT id, lot_code, quantity, uom, user_operations, inserted_at, failed_code
        FROM erp_mo_to_import 
        WHERE processed_at IS NULL AND (failed_code IS NULL OR failed_code = '')
        ORDER BY inserted_at DESC
        """
        results = db.fetch_all(query)
        return results if results else []
    except Exception as e:
        st.error(f"Error fetching pending orders: {str(e)}")
        return []

def fetch_failed_orders():
    """Fetch all failed orders from database (failed_code IS NOT NULL AND processed_at = NULL)."""
    try:
        db = DatabaseManager()
        query = """
        SELECT id, lot_code, quantity, uom, user_operations, inserted_at, failed_code
        FROM erp_mo_to_import 
        WHERE processed_at IS NULL AND failed_code IS NOT NULL AND failed_code != ''
        ORDER BY inserted_at DESC
        """
        results = db.fetch_all(query)
        return results if results else []
    except Exception as e:
        st.error(f"Error fetching failed orders: {str(e)}")
        return []

def update_processed_orders(order_ids):
    """Update processed_at timestamp for successfully processed orders. Returns number of rows updated."""
    if not order_ids:
        st.warning("⚠️ No order IDs provided to update")
        return 0
    
    try:
        db = DatabaseManager()
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Create placeholders for the IN clause
        placeholders = ','.join(['%s'] * len(order_ids))
        query = f"""
        UPDATE erp_mo_to_import 
        SET processed_at = %s 
        WHERE id IN ({placeholders}) AND processed_at IS NULL
        """
        
        values = [current_time] + order_ids
        rows_updated = db.execute_query(query, tuple(values))
        
        if rows_updated != len(order_ids):
            st.warning(f"⚠️ Expected to update {len(order_ids)} orders, but only {rows_updated} were updated. Some orders may have already been processed.")
        
        return rows_updated
        
    except Exception as e:
        st.error(f"❌ Error updating processed orders: {str(e)}")
        raise

def update_failed_orders(failed_orders_data):
    """Update failed_code for orders that failed during processing. Returns total rows updated."""
    if not failed_orders_data:
        return 0
    
    try:
        db = DatabaseManager()
        total_updated = 0
        
        for failed_order in failed_orders_data:
            lot_code = failed_order.get('lot_number')
            error_message = failed_order.get('error', 'Unknown error')
            
            if not lot_code:
                st.warning(f"⚠️ Skipping failed order update: missing lot_number")
                continue
            
            query = """
            UPDATE erp_mo_to_import 
            SET failed_code = %s 
            WHERE lot_code = %s AND processed_at IS NULL
            """
            
            rows_updated = db.execute_query(query, (error_message, lot_code))
            total_updated += rows_updated
            
            if rows_updated == 0:
                st.warning(f"⚠️ No rows updated for failed order: {lot_code} (may already be processed)")
        
        return total_updated
        
    except Exception as e:
        st.error(f"❌ Error updating failed orders: {str(e)}")
        raise

def process_selected_orders(selected_orders, server_url, processing_mode):
    """Process the selected orders and display results."""
    
    try:
        # Convert database records to order format expected by the API
        orders = []
        for order in selected_orders:
            orders.append({
                "lot_number": order['lot_code'],
                "quantity": float(order['quantity'])
            })

        if processing_mode == "Batch Processing (Recommended)":
            # Batch processing
            st.subheader("🔄 Processing Orders in Batch...")

            payload = {"orders": orders}

            with st.spinner("Processing batch request..."):
                response = requests.post(
                    f"{server_url}/process_mo",
                    json=payload,
                    headers={'Content-Type': 'application/json'},
                    timeout=600  # 10 minutes timeout
                )

            # Update the database based on results
            # Process results regardless of status code if we have valid JSON response
            try:
                result_data = response.json()
                results = result_data.get('results', [])

                # If we have results, process them regardless of HTTP status
                if results:
                    # Process each result individually
                    successful_order_ids = []
                    failed_orders_data = []

                    # Create a mapping of lot_code to order_id for quick lookup
                    # Use case-insensitive matching by normalizing both keys
                    lot_code_to_order_id = {}
                    lot_code_normalized_to_order = {}
                    for order in selected_orders:
                        lot_code = order['lot_code']
                        lot_code_to_order_id[lot_code] = order['id']
                        # Also create normalized version for case-insensitive matching
                        lot_code_normalized_to_order[lot_code.strip().upper() if lot_code else ''] = {
                            'id': order['id'],
                            'original': lot_code
                        }

                    st.write("### Processing Results:")
                    unmatched_results = []
                    for result in results:
                        lot_number = result.get('lot_number', '')
                        is_success = result.get('success', False)
                        
                        # Try exact match first
                        if lot_number in lot_code_to_order_id:
                            order_id = lot_code_to_order_id[lot_number]
                        # Try case-insensitive match
                        elif lot_number and lot_number.strip().upper() in lot_code_normalized_to_order:
                            order_id = lot_code_normalized_to_order[lot_number.strip().upper()]['id']
                            original_lot_code = lot_code_normalized_to_order[lot_number.strip().upper()]['original']
                            st.warning(f"⚠️ Lot number case mismatch: '{lot_number}' matched '{original_lot_code}'")
                        else:
                            unmatched_results.append(lot_number)
                            st.warning(f"⚠️ Result for lot number '{lot_number}' not found in selected orders")
                            continue
                        
                        if is_success:
                            # Add to successful orders list
                            successful_order_ids.append(order_id)
                            st.write(f"✅ {lot_number}: Success")
                        else:
                            # Add to failed orders list
                            error_message = result.get('error', 'Unknown error')
                            failed_orders_data.append({
                                'lot_number': lot_number,
                                'error': error_message
                            })
                            st.write(f"❌ {lot_number}: Failed - {error_message}")
                    
                    if unmatched_results:
                        st.error(f"❌ {len(unmatched_results)} result(s) could not be matched to selected orders: {unmatched_results}")

                    # Update successful orders
                    if successful_order_ids:
                        try:
                            rows_updated = update_processed_orders(successful_order_ids)
                            if rows_updated > 0:
                                st.success(f"✅ Database updated - {rows_updated} orders marked as processed!")
                            else:
                                st.error(f"❌ Database update failed - 0 rows updated for {len(successful_order_ids)} orders")
                        except Exception as e:
                            st.error(f"❌ Failed to update database: {str(e)}")
                    
                    # Update failed orders
                    if failed_orders_data:
                        try:
                            update_failed_orders(failed_orders_data)
                            st.warning(f"⚠️ Database updated - {len(failed_orders_data)} orders marked as failed!")
                        except Exception as e:
                            st.error(f"❌ Failed to update failed orders in database: {str(e)}")

                    # Summary message
                    if successful_order_ids and failed_orders_data:
                        st.info(f"📊 Mixed results: {len(successful_order_ids)} succeeded, {len(failed_orders_data)} failed")
                    elif successful_order_ids:
                        st.success(f"🎉 All {len(successful_order_ids)} orders processed successfully!")
                    elif failed_orders_data:
                        st.error(f"❌ All {len(failed_orders_data)} orders failed")
                    else:
                        st.warning("⚠️ No results found in response")
                        
                    # Show overall status if not 200
                    if response.status_code != 200:
                        st.warning(f"⚠️ Overall batch status: {response.status_code} - but individual results were processed")

                else:
                    # No results array, treat as complete failure
                    st.error(f"❌ Batch request failed with status {response.status_code}")
                    st.json(result_data)

            except Exception as e:
                # Failed to parse JSON or other error
                st.error(f"❌ Batch request failed with status {response.status_code}")
                st.error(f"Error processing response: {str(e)}")
                try:
                    # Try to show JSON if possible
                    error_data = response.json()
                    st.json(error_data)
                except:
                    # Show raw response
                    st.text("Raw response:")
                    st.code(response.text)

            # Always display results regardless of database update success
            display_batch_results(response, orders)

        else:
            # Individual processing
            st.subheader("🔄 Processing Orders Individually...")

            results = []
            progress_bar = st.progress(0)
            processed_order_ids = []
            failed_orders_data = []

            for i, order in enumerate(orders):
                st.write(f"Processing order {i + 1}/{len(orders)}: {order['lot_number']}")

                try:
                    with st.spinner(f"Processing {order['lot_number']}..."):
                        response = requests.post(
                            f"{server_url}/process_mo",
                            json=order,
                            headers={'Content-Type': 'application/json'},
                            timeout=300  # 5 minutes timeout
                        )

                    success = response.status_code == 200
                    results.append({
                        "order": order,
                        "response": response,
                        "success": success
                    })

                    # If successful, add to list for database update
                    if success:
                        processed_order_ids.append(selected_orders[i]['id'])
                    else:
                        # If failed, extract error message for database update
                        try:
                            error_data = response.json()
                            error_message = error_data.get('error', f'HTTP {response.status_code}')
                        except:
                            error_message = f'HTTP {response.status_code}'
                        
                        failed_orders_data.append({
                            'lot_number': order['lot_number'],
                            'error': error_message
                        })

                except Exception as e:
                    results.append({
                        "order": order,
                        "response": None,
                        "error": str(e),
                        "success": False
                    })
                    
                    # Add to failed orders for database update
                    failed_orders_data.append({
                        'lot_number': order['lot_number'],
                        'error': str(e)
                    })

                progress_bar.progress((i + 1) / len(orders))

            # Update database for successfully processed orders
            if processed_order_ids:
                try:
                    rows_updated = update_processed_orders(processed_order_ids)
                    if rows_updated > 0:
                        st.success(f"✅ Database updated - {rows_updated} orders marked as processed!")
                    else:
                        st.error(f"❌ Database update failed - 0 rows updated for {len(processed_order_ids)} orders")
                except Exception as e:
                    st.error(f"❌ Failed to update database: {str(e)}")
            
            # Update database for failed orders
            if failed_orders_data:
                try:
                    update_failed_orders(failed_orders_data)
                    st.warning(f"⚠️ Database updated - {len(failed_orders_data)} orders marked as failed!")
                except Exception as e:
                    st.error(f"❌ Failed to update failed orders in database: {str(e)}")

            display_individual_results(results)

    except Exception as e:
        st.error(f"Processing failed: {str(e)}")

def display_batch_results(response, orders):
    """Display results from batch processing."""

    st.subheader("📊 Batch Processing Results")

    # Add timestamp
    st.write(f"**Processed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if response.status_code == 200:
        try:
            result_data = response.json()

            # Summary metrics
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Orders", result_data.get('total_processed', 0))
            with col2:
                st.metric("Successful", result_data.get('successful', 0))
            with col3:
                st.metric("Failed", result_data.get('failed', 0))
            with col4:
                success_rate = (result_data.get('successful', 0) / max(result_data.get('total_processed', 1), 1)) * 100
                st.metric("Success Rate", f"{success_rate:.1f}%")

            # Overall status
            if result_data.get('success', False):
                st.success("✅ All orders processed successfully!")
            else:
                st.warning("⚠️ Some orders failed to process")

            # Detailed results
            st.subheader("Detailed Results")

            results = result_data.get('results', [])
            for i, result in enumerate(results):
                with st.expander(
                        f"Order {i + 1}: {result.get('lot_number', 'Unknown')} - {'✅ Success' if result.get('success') else '❌ Failed'}"):
                    st.json(result)

        except Exception as e:
            st.error(f"Error parsing response: {str(e)}")
            st.text("Raw response:")
            st.code(response.text)
    else:
        st.error(f"❌ Request failed with status {response.status_code}")
        try:
            error_data = response.json()
            st.json(error_data)
        except:
            st.text("Raw response:")
            st.code(response.text)

def display_individual_results(results):
    """Display results from individual processing."""

    st.subheader("📊 Individual Processing Results")

    # Add timestamp
    st.write(f"**Processed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    # Summary metrics
    successful = sum(1 for r in results if r['success'])
    failed = len(results) - successful

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.metric("Total Orders", len(results))
    with col2:
        st.metric("Successful", successful)
    with col3:
        st.metric("Failed", failed)
    with col4:
        success_rate = (successful / max(len(results), 1)) * 100
        st.metric("Success Rate", f"{success_rate:.1f}%")

    # Detailed results
    st.subheader("Detailed Results")

    for i, result in enumerate(results):
        order = result['order']
        success = result['success']

        with st.expander(f"Order {i + 1}: {order['lot_number']} - {'✅ Success' if success else '❌ Failed'}"):
            st.write(f"**Lot Number:** {order['lot_number']}")
            st.write(f"**Quantity:** {order['quantity']}")

            if success and result['response']:
                try:
                    response_data = result['response'].json()
                    st.json(response_data)
                except:
                    st.text("Raw response:")
                    st.code(result['response'].text)
            elif 'error' in result:
                st.error(f"Error: {result['error']}")
            else:
                st.error("Unknown error occurred")

# Title and description
st.title("🏭 MRP Easy - Manufacturing Order Processor")
st.markdown("Process manufacturing orders from database")

# Server URL input
st.sidebar.header("Server Configuration")
server_url = st.sidebar.text_input(
    "Server URL",
    value=secrets['mrpeasy-could-run-po-automation-service-url'],
    help="Enter your deployed service URL"
)

# Remove trailing slash if present
server_url = server_url.rstrip('/')

# Test server connection
if st.sidebar.button("Test Server Connection"):
    try:
        with st.spinner("Testing connection..."):
            response = requests.get(f"{server_url}/health", timeout=10)
            if response.status_code == 200:
                health_data = response.json()
                st.sidebar.success("✅ Server is healthy!")
                st.sidebar.json(health_data)
            else:
                st.sidebar.error(f"❌ Server returned status {response.status_code}")
    except Exception as e:
        st.sidebar.error(f"❌ Connection failed: {str(e)}")

# Initialize session state
if 'pending_orders' not in st.session_state:
    st.session_state.pending_orders = []
if 'failed_orders' not in st.session_state:
    st.session_state.failed_orders = []

# Main content area
col1, col2 = st.columns([1, 1])

with col1:
    st.header("📋 Manufacturing Orders from Database")
    
    # Fetch orders button
    if st.button("🔄 Fetch Orders from Database", type="primary"):
        with st.spinner("Fetching orders from database..."):
            st.session_state.pending_orders = fetch_pending_orders()
            st.session_state.failed_orders = fetch_failed_orders()
        
        st.success(f"Fetched {len(st.session_state.pending_orders)} pending orders and {len(st.session_state.failed_orders)} failed orders")
    
    # Display pending orders for selection
    if st.session_state.pending_orders:
        st.subheader("✅ Pending Orders (Ready for Processing)")
        st.markdown(f"**{len(st.session_state.pending_orders)} orders** available for processing")
        
        # Select All / Select None buttons
        col_select1, col_select2 = st.columns(2)
        with col_select1:
            if st.button("✓ Select All Pending"):
                st.session_state.select_all_pending = True
                st.rerun()
        
        with col_select2:
            if st.button("✗ Clear All Pending"):
                st.session_state.clear_all_pending = True
                st.rerun()
        
        # Handle select all / clear all actions
        if st.session_state.get('select_all_pending', False):
            for i in range(len(st.session_state.pending_orders)):
                st.session_state[f"pending_select_{i}"] = True
            st.session_state.select_all_pending = False
        
        if st.session_state.get('clear_all_pending', False):
            for i in range(len(st.session_state.pending_orders)):
                st.session_state[f"pending_select_{i}"] = False
            st.session_state.clear_all_pending = False

        # Orders selection table
        selected_pending = []
        for i, order in enumerate(st.session_state.pending_orders):
            col_check, col_lot, col_qty, col_uom, col_date = st.columns([1, 2, 1, 2, 2])
            
            with col_check:
                selected = st.checkbox(
                    f"Select {order['lot_code']}", 
                    key=f"pending_select_{i}",
                    label_visibility="collapsed"
                )
                if selected:
                    selected_pending.append(order)
            
            with col_lot:
                st.write(f"**{order['lot_code']}**")
            
            with col_qty:
                st.write(f"{order['quantity']}")
            
            with col_uom:
                st.write(f"{order['uom']}")
            
            with col_date:
                st.write(f"{order['inserted_at'].strftime('%Y-%m-%d %H:%M') if order['inserted_at'] else 'N/A'}")
        
        if selected_pending:
            st.success(f"Selected {len(selected_pending)} orders for processing")
        
        # Manual processing button at the bottom (outside of the selected_pending check)
        if st.session_state.pending_orders:
            # Get currently selected orders
            currently_selected = []
            for i, order in enumerate(st.session_state.pending_orders):
                if st.session_state.get(f"pending_select_{i}", False):
                    currently_selected.append(order)
            
            if currently_selected:
                st.markdown("---")
                st.markdown("### ⚠️ Manual Override")
                
                if st.button("⚠️ Manually Mark as Processed", 
                            type="secondary", 
                            help="WARNING: This will mark selected orders as processed WITHOUT actually processing them through the API"):
                    # Get selected order IDs
                    selected_order_ids = [order['id'] for order in currently_selected]
                    
                    # Update database
                    update_processed_orders(selected_order_ids)
                    
                    # Set flag to clear selections on next run
                    st.session_state.clear_all_pending = True
                    
                    # Refresh the orders list
                    st.session_state.pending_orders = fetch_pending_orders()
                    st.session_state.failed_orders = fetch_failed_orders()
                    
                    st.warning(f"⚠️ {len(selected_order_ids)} orders manually marked as processed!")
                    st.rerun()
    
    # Display failed orders
    if st.session_state.failed_orders:
        st.subheader("❌ Failed Orders (Need Attention)")
        st.markdown(f"**{len(st.session_state.failed_orders)} orders** have failed and need attention")
        
        for i, order in enumerate(st.session_state.failed_orders):
            with st.expander(f"❌ {order['lot_code']} - Qty: {order['quantity']} {order['uom']}"):
                st.write(f"**Failure Reason:** {order['failed_code']}")
                st.write(f"**Inserted:** {order['inserted_at'].strftime('%Y-%m-%d %H:%M') if order['inserted_at'] else 'N/A'}")
                st.write(f"**Quantity:** {order['quantity']} {order['uom']}")
                
                st.markdown("---")
                col1, col2 = st.columns([2, 1])
                with col2:
                    if st.button(
                        "⚠️ Mark as Processed", 
                        key=f"failed_mark_{i}",
                        type="secondary",
                        help="WARNING: This will mark this failed order as processed WITHOUT actually processing it through the API"
                    ):
                        # Update database for this single order
                        update_processed_orders([order['id']])
                        
                        # Refresh the orders list
                        st.session_state.pending_orders = fetch_pending_orders()
                        st.session_state.failed_orders = fetch_failed_orders()
                        
                        st.warning(f"⚠️ Order {order['lot_code']} manually marked as processed!")
                        st.rerun()

with col2:
    st.header("🚀 Processing & Results")
    
    # Process orders section
    if st.session_state.pending_orders:
        # Check if any orders are selected
        selected_orders = []
        for i, order in enumerate(st.session_state.pending_orders):
            if st.session_state.get(f"pending_select_{i}", False):
                selected_orders.append(order)
        
        if selected_orders:
            st.subheader(f"Ready to process {len(selected_orders)} selected order(s)")
            
            # Processing mode selection
            processing_mode = st.radio(
                "Processing mode:",
                ["Batch Processing (Recommended)", "Individual Processing"]
            )
            
            if st.button("🚀 Process Selected Orders", type="primary"):
                if not server_url or server_url.strip() == "":
                    st.error("Please configure the server URL in the sidebar")
                else:
                    process_selected_orders(selected_orders, server_url, processing_mode)
        else:
            st.info("Select orders from the left panel to process them")
    else:
        st.info("Click 'Fetch Orders from Database' to load available orders")

# Footer
st.markdown("---")
st.markdown("**MRP Easy Manufacturing Order Processor** - Database-driven Interface")