from datetime import datetime, timedelta
from typing import List, Dict, Any, Tuple
import streamlit as st
from shared.database_manager import DatabaseManager
from shared.database_schema import SCHEMAS

class DatabaseOperations:
    def __init__(self):
        self.db = DatabaseManager()
        self._create_tables()
        self._init_queries()

    def _create_tables(self):
        for schema in SCHEMAS.values():
            self.db.execute_query(schema)

    def _init_queries(self):
        self.order_query = """
        INSERT INTO clover_orders (
            order_id, created_time, delivery_note, delivery_platform, delivery_method, 
            delivery_time, currency, total, external_reference_id, employee_id,
            order_level_discount_name, order_level_discount_percentage, order_level_discount_amount,
            order_raw_json, lineitems_raw_json
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        created_time = VALUES(created_time),
        delivery_note = VALUES(delivery_note),
        delivery_platform = VALUES(delivery_platform),
        delivery_method = VALUES(delivery_method),
        delivery_time = VALUES(delivery_time),
        currency = VALUES(currency),
        total = VALUES(total),
        external_reference_id = VALUES(external_reference_id),
        employee_id = VALUES(employee_id),
        order_level_discount_name = VALUES(order_level_discount_name),
        order_level_discount_percentage = VALUES(order_level_discount_percentage),
        order_level_discount_amount = VALUES(order_level_discount_amount),
        order_raw_json = VALUES(order_raw_json),
        lineitems_raw_json = VALUES(lineitems_raw_json)
        """

        self.item_query = """
        INSERT INTO clover_orders_items (
            item_id, order_id, clover_name, price, price_with_mod, final_price,
            item_level_discount_name, item_level_discount_percentage, item_level_discount_amount,
            item_sku, item_code, item_note
        )
        VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
        ON DUPLICATE KEY UPDATE
        order_id = VALUES(order_id),
        clover_name = VALUES(clover_name),
        price = VALUES(price),
        price_with_mod = VALUES(price_with_mod),
        final_price = VALUES(final_price),
        item_level_discount_name = VALUES(item_level_discount_name),
        item_level_discount_percentage = VALUES(item_level_discount_percentage),
        item_level_discount_amount = VALUES(item_level_discount_amount),
        item_sku = VALUES(item_sku),
        item_code = VALUES(item_code),
        item_note = VALUES(item_note)
        """

        self.mod_query = """
        INSERT INTO clover_orders_items_modifications (item_id, modifier_name, price)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
        modifier_name = VALUES(modifier_name),
        price = VALUES(price)
        """

        self.payment_query = """
        INSERT INTO clover_orders_payments (order_id, tip_amount, tax_amount)
        VALUES (%s, %s, %s)
        ON DUPLICATE KEY UPDATE
        tip_amount = VALUES(tip_amount),
        tax_amount = VALUES(tax_amount)
        """

    def get_latest_order_date(self) -> datetime:
        """Fetch the most recent order date from the database."""
        result = self.db.fetch_one("SELECT MAX(created_time) FROM clover_orders")
        return result[0] if result and result[0] else datetime.now() - timedelta(days=1)

    def save_orders(self, orders: List[Any]):
        """
        Save all order data to the database.
        Expects orders to be a list of CloverOrder objects.
        """
        try:
            order_batch, item_batch, mod_batch, payment_batch = self._prepare_batches(orders)

            with st.spinner('Saving data to database...'):
                self._save_order_batch(order_batch)
                self._save_item_batches(item_batch)
                self._save_modification_batch(mod_batch)
                self._save_payment_batch(payment_batch)

        except Exception as e:
            st.error(f"Database save error: {str(e)}")
            raise

    def _prepare_batches(self, orders: List[Any]) -> Tuple[List, List, List, List]:
        """
        Prepare data batches for database insertion.
        Expects orders to be a list of CloverOrder objects.
        """
        order_batch = []
        item_batch = []
        mod_batch = []
        payment_batch = []

        total_orders = len(orders)
        progress_bar = st.progress(0)

        for i, order in enumerate(orders):
            order_batch.append(order.get_order_details())
            item_batch.extend(order.get_items())
            mod_batch.extend(order.get_modifications())
            payment_batch.extend(order.get_payments())

            progress = (i + 1) / total_orders
            progress_bar.progress(progress)

        progress_bar.empty()
        st.write(f"Prepared batches - Orders: {len(order_batch)}, Items: {len(item_batch)}, "
                 f"Mods: {len(mod_batch)}, Payments: {len(payment_batch)}")

        return order_batch, item_batch, mod_batch, payment_batch

    def _save_order_batch(self, batch: List[tuple]):
        """Save order batch to database."""
        if batch:
            self.db.execute_batch_insert(self.order_query, batch)

    def _save_item_batches(self, items: List[tuple]):
        """Save items to database in chunks."""
        if items:
            chunk_size = 1000
            for i in range(0, len(items), chunk_size):
                chunk = items[i:i + chunk_size]
                self.db.execute_batch_insert(self.item_query, chunk)
                st.write(f"Saved items chunk {i//chunk_size + 1}")

    def _save_modification_batch(self, batch: List[tuple]):
        """Save modifications batch to database."""
        if batch:
            self.db.execute_batch_insert(self.mod_query, batch)

    def _save_payment_batch(self, batch: List[tuple]):
        """Save payments batch to database."""
        if batch:
            self.db.execute_batch_insert(self.payment_query, batch)

    def get_summary(self, start_date: datetime) -> List[Dict]:
        """Get summary of imported orders."""
        query = """
        SELECT 
            DATE(created_time) as date,
            COUNT(*) as orders,
            SUM(total) as total
        FROM clover_orders
        WHERE created_time >= %s
        GROUP BY DATE(created_time)
        ORDER BY date DESC
        """
        return self.db.fetch_all(query, (start_date,))