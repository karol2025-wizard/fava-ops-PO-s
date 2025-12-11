# db/repository.py
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional
import pandas as pd
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
        """
        Retrieve historical orders within the specified date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            DataFrame containing order data with processed numeric columns
        """
        results = self.db.fetch_all(SalesQueries.GET_HISTORICAL_ORDERS, (start_date, end_date))
        df = pd.DataFrame(results)
        return self._process_dataframe(df, numeric_columns=['total', 'tip_amount'])

    def get_item_sales(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Retrieve item sales data within the specified date range.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            DataFrame containing item sales data with processed numeric columns
        """
        results = self.db.fetch_all(SalesQueries.GET_ITEM_SALES, (start_date, end_date))
        df = pd.DataFrame(results)
        return self._process_dataframe(df, numeric_columns=['final_price'])

    def get_order_items(self, order_id: str) -> List[OrderItem]:
        """
        Retrieve items for a specific order.

        Args:
            order_id: The ID of the order

        Returns:
            List of OrderItem objects containing item details
        """
        results = self.db.fetch_all(SalesQueries.GET_ORDER_ITEMS, (order_id,))
        return [
            OrderItem(
                clover_name=item['clover_name'],
                quantity=item['quantity'],
                total_price=Decimal(str(item['total_price']))
            ) for item in results
        ]

    def get_daily_summary(self, start_date: datetime, end_date: datetime) -> Tuple[Dict, Dict]:
        """
        Get daily sales summary and historical averages.

        Args:
            start_date: Start of the date range
            end_date: End of the date range

        Returns:
            Tuple containing (current_day_summary, historical_summary)
        """
        params = (start_date, end_date)

        # Fetch all required data
        sales_df = self._fetch_and_process_summary(
            SalesQueries.GET_DAILY_SALES,
            params,
            'total_sales'
        )

        tips_df = self._fetch_and_process_summary(
            SalesQueries.GET_DAILY_TIPS,
            params,
            'total_tips'
        )

        mods_df = self._fetch_and_process_summary(
            SalesQueries.GET_DAILY_MODIFICATIONS,
            params,
            'total_mods'
        )

        order_discounts_df = self._fetch_and_process_summary(
            SalesQueries.GET_ORDER_DISCOUNTS,
            params,
            'total_order_discounts'
        )

        item_discounts_df = self._fetch_and_process_summary(
            SalesQueries.GET_ITEM_DISCOUNTS,
            params,
            'total_item_discounts'
        )

        # Initialize summaries
        current_day = {}
        historical_summary = {}

        # Process each metric
        metric_dfs = {
            'total_sales': sales_df,
            'total_tips': tips_df,
            'total_mods': mods_df,
            'order_discounts': order_discounts_df,
            'item_discounts': item_discounts_df
        }

        analysis_date = end_date.date() - pd.Timedelta(days=1)

        for metric_name, df in metric_dfs.items():
            if not df.empty:
                # Get current day value
                current_day_data = df[df['date'] == analysis_date]
                if not current_day_data.empty:
                    value_col = df.columns[2]  # The value column is always the third column
                    current_day[metric_name] = float(current_day_data[value_col].iloc[0])

                # Get historical average
                historical_data = df[
                    (df['date'] < analysis_date) &
                    (df['weekday'] == analysis_date.weekday())
                    ]
                if not historical_data.empty:
                    value_col = df.columns[2]  # The value column is always the third column
                    historical_summary[f'avg_{metric_name}'] = float(historical_data[value_col].mean())

        return current_day, historical_summary

    def _fetch_and_process_summary(self, query: str, params: Tuple, value_column: str) -> pd.DataFrame:
        """
        Helper method to fetch and process summary data.

        Args:
            query: SQL query to execute
            params: Query parameters
            value_column: Name of the value column to process

        Returns:
            Processed DataFrame
        """
        results = self.db.fetch_all(query, params)
        df = pd.DataFrame(results)
        if not df.empty:
            df[value_column] = df[value_column].apply(self._decimal_to_float)
        return df

    def get_order_by_id(self, order_id: str) -> Optional[Order]:
        """
        Retrieve a specific order by ID with all its items.

        Args:
            order_id: The ID of the order to retrieve

        Returns:
            Order object if found, None otherwise
        """
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

        result = self.db.fetch_one(query, (order_id,))
        if not result:
            return None

        items = self.get_order_items(order_id)

        return Order(
            order_id=result['order_id'],
            created_time=result['created_time'],
            total=Decimal(str(result['total'])),
            delivery_method=result['delivery_method'],
            delivery_platform=result['delivery_platform'],
            tip_amount=Decimal(str(result['tip_amount'])),
            items=items
        )