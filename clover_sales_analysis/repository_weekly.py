# db/repository.py
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
import streamlit as st
from decimal import Decimal
from shared.database_manager import DatabaseManager
from clover_sales_analysis.queries import SalesQueries
from clover_sales_analysis.models import Order, OrderItem


class SalesRepository:
    """Repository for handling all database interactions related to sales data"""

    def __init__(self):
        self.db = DatabaseManager()

    def _decimal_to_float(self, value: Any) -> float:
        """Convert Decimal types to float"""
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _process_dataframe(self, df: pd.DataFrame, date_column: str = 'created_time',
                           numeric_columns: List[str] = None) -> pd.DataFrame:
        """Process a dataframe to ensure consistent data types and add weekday"""
        if df.empty:
            return df

        if numeric_columns:
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self._decimal_to_float)

        if date_column in df.columns:
            df['weekday'] = df[date_column].dt.weekday

        return df

    def get_historical_orders(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Retrieve historical orders within the specified date range."""
        results = self.db.fetch_all(SalesQueries.GET_HISTORICAL_ORDERS, (start_date, end_date))
        df = pd.DataFrame(results)
        return self._process_dataframe(df, numeric_columns=['total', 'tip_amount'])

    def get_item_sales(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """Retrieve item sales data within the specified date range."""
        results = self.db.fetch_all(SalesQueries.GET_ITEM_SALES, (start_date, end_date))
        df = pd.DataFrame(results)
        return self._process_dataframe(df, numeric_columns=['final_price'])

    def get_order_items(self, order_id: str, connection=None) -> List[OrderItem]:
        """Retrieve items for a specific order."""
        if connection:
            # Use existing connection
            with connection.cursor(dictionary=True) as cursor:
                cursor.execute(SalesQueries.GET_ORDER_ITEMS, (order_id,))
                results = cursor.fetchall()
        else:
            # Create new connection
            with self.db.pool.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(SalesQueries.GET_ORDER_ITEMS, (order_id,))
                    results = cursor.fetchall()

        return [
            OrderItem(
                clover_name=item['clover_name'],
                quantity=item['quantity'],
                total_price=Decimal(str(item['total_price']))
            ) for item in results
        ]

    def get_daily_summary(self, start_date: datetime, end_date: datetime) -> Tuple[Dict, Dict]:
        """Get daily sales summary and historical averages."""
        daily_mods = self._get_daily_modifications_totals((start_date, end_date))
        return daily_mods, daily_mods

    def _get_daily_modifications_totals(self, params: tuple) -> Dict:
        """Get daily modifications and discounts totals."""
        return {
            'total_mods': 0,
            'order_discounts': 0,
            'item_discounts': 0
        }

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """Retrieve a specific order by ID with all its items."""
        query = """
        SELECT 
            o.order_id, 
            o.created_time, 
            o.total,
            o.delivery_method,
            o.delivery_platform,
            COALESCE(p.tip_amount, 0) as tip_amount
        FROM clover_orders o
        LEFT JOIN clover_orders_payments p ON o.order_id = p.order_id
        WHERE o.order_id = %s
        """

        try:
            with self.db.pool.get_connection() as connection:
                with connection.cursor(dictionary=True) as cursor:
                    cursor.execute(query, (order_id,))
                    result = cursor.fetchone()
                    cursor.fetchall()  # Consume any remaining results

                    if not result:
                        return None

                    # Use the same connection for getting order items
                    items = self.get_order_items(order_id, connection)

                    return Order(
                        order_id=result['order_id'],
                        created_time=result['created_time'],
                        total=Decimal(str(result['total'])),
                        delivery_method=result['delivery_method'],
                        delivery_platform=result['delivery_platform'],
                        tip_amount=Decimal(str(result['tip_amount'])),
                        items=items
                    )
        except Exception as e:
            st.error(f"Error fetching order: {e}")
            return None