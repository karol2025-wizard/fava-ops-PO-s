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
from shared.production_workflow import ProductionWorkflow

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

def process_selected_orders(selected_orders, server_url=None, processing_mode="Batch Processing (Recommended)"):
    """Process the selected orders using ProductionWorkflow to update MRPeasy."""
    
    try:
        # Initialize ProductionWorkflow
        workflow = ProductionWorkflow()
        
        if processing_mode == "Batch Processing (Recommended)":
            # Batch processing using ProductionWorkflow
            st.subheader("🔄 Processing Orders in Batch...")
            
            successful_order_ids = []
            failed_orders_data = []
            results = []
            
            with st.spinner("Processing batch request..."):
                for order in selected_orders:
                    lot_code = order['lot_code']
                    quantity = float(order['quantity'])
                    uom = order.get('uom')
                    
                    # Process using ProductionWorkflow
                    success, result_data, message = workflow.process_production_completion(
                        lot_code=lot_code,
                        produced_quantity=quantity,
                        uom=uom,
                        item_code=None  # Will be retrieved from MO lookup
                    )
                    
                    results.append({
                        'lot_number': lot_code,
                        'success': success,
                        'message': message,
                        'result_data': result_data
                    })
                    
                    if success:
                        successful_order_ids.append(order['id'])
                        st.write(f"✅ {lot_code}: {message}")
                    else:
                        failed_orders_data.append({
                            'lot_number': lot_code,
                            'error': message
                        })
                        st.write(f"❌ {lot_code}: Failed - {message}")

            # Update database based on results
            st.write("### Processing Results:")
            
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
                st.warning("⚠️ No results to process")

            # Display batch results
            display_batch_results_local(results, selected_orders)

        else:
            # Individual processing using ProductionWorkflow
            st.subheader("🔄 Processing Orders Individually...")

            results = []
            progress_bar = st.progress(0)
            processed_order_ids = []
            failed_orders_data = []

            for i, order in enumerate(selected_orders):
                lot_code = order['lot_code']
                quantity = float(order['quantity'])
                uom = order.get('uom')
                
                st.write(f"Processing order {i + 1}/{len(selected_orders)}: {lot_code}")

                try:
                    with st.spinner(f"Processing {lot_code}..."):
                        # Process using ProductionWorkflow
                        success, result_data, message = workflow.process_production_completion(
                            lot_code=lot_code,
                            produced_quantity=quantity,
                            uom=uom,
                            item_code=None  # Will be retrieved from MO lookup
                        )

                    results.append({
                        "order": {
                            "lot_number": lot_code,
                            "quantity": quantity
                        },
                        "success": success,
                        "message": message,
                        "result_data": result_data
                    })

                    # If successful, add to list for database update
                    if success:
                        processed_order_ids.append(order['id'])
                        st.write(f"✅ {lot_code}: {message}")
                    else:
                        failed_orders_data.append({
                            'lot_number': lot_code,
                            'error': message
                        })
                        st.write(f"❌ {lot_code}: Failed - {message}")

                except Exception as e:
                    error_msg = str(e)
                    results.append({
                        "order": {
                            "lot_number": lot_code,
                            "quantity": quantity
                        },
                        "success": False,
                        "error": error_msg,
                        "message": error_msg
                    })
                    
                    # Add to failed orders for database update
                    failed_orders_data.append({
                        'lot_number': lot_code,
                        'error': error_msg
                    })
                    st.write(f"❌ {lot_code}: Error - {error_msg}")

                progress_bar.progress((i + 1) / len(selected_orders))

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

def display_batch_results_local(results, orders):
    """Display results from batch processing using local ProductionWorkflow."""

    st.subheader("📊 Batch Processing Results")

    # Add timestamp
    st.write(f"**Processed at:** {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

    if results:
        # Summary metrics
        total = len(results)
        successful = sum(1 for r in results if r.get('success', False))
        failed = total - successful
        
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("Total Orders", total)
        with col2:
            st.metric("Successful", successful)
        with col3:
            st.metric("Failed", failed)
        with col4:
            success_rate = (successful / max(total, 1)) * 100
            st.metric("Success Rate", f"{success_rate:.1f}%")

        # Overall status
        if successful == total:
            st.success("✅ All orders processed successfully!")
        elif successful > 0:
            st.warning("⚠️ Some orders failed to process")
        else:
            st.error("❌ All orders failed")

        # Detailed results
        st.subheader("Detailed Results")

        for i, result in enumerate(results):
            lot_number = result.get('lot_number', 'Unknown')
            success = result.get('success', False)
            message = result.get('message', '')
            result_data = result.get('result_data')
            
            with st.expander(
                    f"Order {i + 1}: {lot_number} - {'✅ Success' if success else '❌ Failed'}"):
                st.write(f"**Lot Code:** {lot_number}")
                st.write(f"**Status:** {'✅ Success' if success else '❌ Failed'}")
                st.write(f"**Message:** {message}")
                
                if result_data and success:
                    st.write("**MO Details:**")
                    mo_lookup = result_data.get('mo_lookup', {})
                    mo_update = result_data.get('mo_update', {})
                    st.write(f"- MO Number: {mo_lookup.get('mo_number', 'N/A')}")
                    st.write(f"- Item Code: {mo_lookup.get('item_code', 'N/A')}")
                    st.write(f"- Actual Quantity: {mo_update.get('actual_quantity', 'N/A')}")
                    st.write(f"- Status: {mo_update.get('status', 'N/A')}")
                    
                    # Show summary PDF if available
                    summary_pdf = result_data.get('summary_pdf')
                    if summary_pdf:
                        st.download_button(
                            label="📥 Download Production Summary PDF",
                            data=summary_pdf.getvalue(),
                            file_name=f"production_summary_{lot_number}.pdf",
                            mime="application/pdf"
                        )
                elif not success:
                    st.error(f"**Error:** {message}")
    else:
        st.warning("⚠️ No results to display")

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
st.markdown("Process manufacturing orders from database and update MRPeasy with actual production quantities")

# Info sidebar
st.sidebar.header("ℹ️ Information")
st.sidebar.info("""
This page processes production entries from the Lot App and updates MRPeasy:
- Looks up MO by Lot Code
- Updates actual produced quantity
- Changes status to Done
- Closes the manufacturing order automatically
- Generates production summary
""")

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
                process_selected_orders(selected_orders, None, processing_mode)
        else:
            st.info("Select orders from the left panel to process them")
    else:
        st.info("Click 'Fetch Orders from Database' to load available orders")

# Footer
st.markdown("---")
st.markdown("**MRP Easy Manufacturing Order Processor** - Database-driven Interface")