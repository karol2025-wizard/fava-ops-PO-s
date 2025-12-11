from datetime import datetime
from typing import List, Dict, Tuple
import pandas as pd
from decimal import Decimal
from shared.database_manager import DatabaseManager
from silverware_sales_analysis.queries import SalesQueries

class SalesRepository:
    """Repository for handling database interactions related to Silverware sales data"""

    def __init__(self):
        self.db = DatabaseManager()

    def _decimal_to_float(self, value):
        """Convert Decimal types to float"""
        if isinstance(value, Decimal):
            return float(value)
        return value

    def _process_dataframe(self, df: pd.DataFrame, date_column: str = 'start_date', numeric_columns: List[str] = None):
        """Process a dataframe to ensure consistent data types and add weekday"""
        if df.empty:
            return df

        if numeric_columns:
            for col in numeric_columns:
                if col in df.columns:
                    df[col] = df[col].apply(self._decimal_to_float)

        if date_column in df.columns:
            df['weekday'] = pd.to_datetime(df[date_column]).dt.weekday

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

    def get_order_items(self, check_number: str) -> List[Dict]:
        """Retrieve items for a specific order."""
        results = self.db.fetch_all(SalesQueries.GET_ORDER_ITEMS, (check_number,))
        return [
            {
                'item_sku': item['item_sku'],
                'quantity': item['quantity'],
                'total_price': self._decimal_to_float(item['total_price'])
            } for item in results
        ]

    def get_daily_summary(self, start_date: datetime, end_date: datetime) -> Tuple[Dict, Dict]:
        """Get daily sales summary and historical averages."""
        params = (start_date, end_date)

        sales_df = self._fetch_and_process_summary(SalesQueries.GET_DAILY_SALES, params, 'total_sales')
        tips_df = self._fetch_and_process_summary(SalesQueries.GET_DAILY_TIPS, params, 'total_tips')
        discounts_df = self._fetch_and_process_summary(SalesQueries.GET_DAILY_DISCOUNTS, params, 'total_discounts')

        current_day = {}
        historical_summary = {}

        analysis_date = end_date.date() - pd.Timedelta(days=1)

        for metric_name, df in {'total_sales': sales_df, 'total_tips': tips_df, 'total_discounts': discounts_df}.items():
            if not df.empty:
                current_day_data = df[df['date'] == analysis_date]
                if not current_day_data.empty:
                    current_day[metric_name] = current_day_data.iloc[0][metric_name]

                historical_data = df[(df['date'] < analysis_date) & (df['weekday'] == analysis_date.weekday())]
                if not historical_data.empty:
                    historical_summary[f'avg_{metric_name}'] = historical_data[metric_name].mean()

        return current_day, historical_summary

    def _fetch_and_process_summary(self, query: str, params: Tuple, value_column: str) -> pd.DataFrame:
        """Helper method to fetch and process summary data."""
        results = self.db.fetch_all(query, params)
        df = pd.DataFrame(results)
        if not df.empty:
            df[value_column] = df[value_column].apply(self._decimal_to_float)
        return df


