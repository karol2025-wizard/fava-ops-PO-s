from datetime import datetime, timedelta, date
from typing import Dict, Any, Union, List, Tuple
import pandas as pd
from decimal import Decimal
from clover_sales_analysis.repository_weekly import SalesRepository
from clover_sales_analysis.models import Order, OrderItem


class SalesAnalyzer:
    def __init__(self):
        self.repository = SalesRepository()
        self.z_score_threshold = 2
        self.lookback_days = 60

    def analyze_week(self, start_date: Union[datetime, date], end_date: Union[datetime, date]) -> Dict[str, Any]:
        """Perform complete analysis for a given week"""
        # Ensure we're working with datetime objects
        if isinstance(start_date, date):
            start_date = datetime.combine(start_date, datetime.min.time())
        if isinstance(end_date, date):
            end_date = datetime.combine(end_date, datetime.max.time())

        # Calculate the start date for historical data
        historical_start = end_date - timedelta(days=self.lookback_days)

        # Get historical data
        orders_df = self.repository.get_historical_orders(historical_start, end_date)
        items_df = self.repository.get_item_sales(historical_start, end_date)

        if orders_df.empty or items_df.empty:
            return {
                'success': False,
                'message': 'No data available for the selected period.'
            }

        # Convert datetime to date for comparison
        orders_df['date'] = orders_df['created_time'].dt.date
        items_df['date'] = items_df['created_time'].dt.date

        # Get weekly summary and historical averages
        weekly_summary, historical_summary = self._calculate_weekly_metrics(
            orders_df,
            start_date.date(),
            end_date.date()
        )

        # Detect outliers and gather detailed analysis
        results = {
            'success': True,
            'weekly_summary': weekly_summary,
            'historical_summary': historical_summary,
            'order_outliers': self._detect_order_outliers(orders_df, start_date.date(), end_date.date()),
            'item_outliers': self._detect_item_outliers(items_df, start_date.date(), end_date.date()),
            'category_outliers': self._detect_category_outliers(items_df, start_date.date(), end_date.date()),
            'tip_outliers': self._detect_tip_outliers(orders_df, start_date.date(), end_date.date()),
            'daily_breakdown': self._get_daily_breakdown(orders_df, start_date.date(), end_date.date())
        }

        return results

    def _calculate_weekly_metrics(
            self,
            df: pd.DataFrame,
            start_date: date,
            end_date: date
    ) -> Tuple[Dict, Dict]:
        """Calculate weekly metrics and historical averages"""
        # Filter for current week
        current_week_mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        current_week_df = df[current_week_mask]

        # Get modifications data
        daily_mods = self._get_modifications_totals(start_date, end_date)
        historical_mods = self._get_historical_modifications_averages(start_date)

        # Calculate weekly metrics
        weekly_summary = {
            'total_sales': float(current_week_df['total'].sum()),
            'total_tips': float(current_week_df['tip_amount'].sum()),
            'total_mods': float(daily_mods.get('total_mods', 0)),
            'order_discounts': float(daily_mods.get('order_discounts', 0)),
            'item_discounts': float(daily_mods.get('item_discounts', 0))
        }

        # Calculate historical weekly averages
        historical_df = df[df['date'] < start_date]

        # Group historical data by week
        historical_df['year_week'] = historical_df['created_time'].dt.strftime('%Y-%U')
        historical_weekly = historical_df.groupby('year_week').agg({
            'total': 'sum',
            'tip_amount': 'sum'
        })

        historical_summary = {
            'avg_total_sales': float(historical_weekly['total'].mean()),
            'avg_total_tips': float(historical_weekly['tip_amount'].mean()),
            'avg_total_mods': float(historical_mods.get('avg_total_mods', 0)),
            'avg_order_discounts': float(historical_mods.get('avg_order_discounts', 0)),
            'avg_item_discounts': float(historical_mods.get('avg_item_discounts', 0))
        }

        return weekly_summary, historical_summary

    def _detect_order_outliers(self, df: pd.DataFrame, start_date: date, end_date: date) -> List[Dict]:
        """Detect orders with unusual totals in the week"""
        current_week_mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        current_week_orders = df[current_week_mask]
        historical_orders = df[df['date'] < start_date]

        # Calculate historical statistics
        hist_mean = historical_orders['total'].mean()
        hist_std = historical_orders['total'].std()

        if hist_std == 0:
            return []

        outliers = []
        for _, order in current_week_orders.iterrows():
            z_score = (float(order['total']) - hist_mean) / hist_std
            if abs(z_score) > self.z_score_threshold:
                # Get detailed order information
                order_details = self.repository.get_order_by_id(order['order_id'])
                if order_details:
                    outliers.append({
                        'order_id': order['order_id'],
                        'total': float(order['total']),
                        'created_time': order['created_time'],
                        'z_score': z_score,
                        'historical_mean': hist_mean,
                        'deviation_percentage': ((float(order['total']) - hist_mean) / hist_mean) * 100,
                        'delivery_method': order['delivery_method'],
                        'delivery_platform': order['delivery_platform'],
                        'tip_amount': float(order['tip_amount']),
                        'items': order_details.items
                    })

        return outliers

    # analysis/weekly_sales_analyzer.py

    def _detect_item_outliers(self, df: pd.DataFrame, start_date: date, end_date: date) -> List[Dict]:
        """Detect items with unusual sales patterns in the week"""
        if df.empty:
            return []

        # Add year-week column before using it
        df['year_week'] = df['created_time'].dt.strftime('%Y-%U')

        current_week_mask = (df['date'] >= start_date) & (df['date'] <= end_date)

        # Group by item and calculate weekly totals
        current_week_items = df[current_week_mask].groupby(['item_sku', 'item_name']).agg({
            'final_price': 'sum'
        }).reset_index()

        # Historical comparison
        historical_df = df[df['date'] < start_date]
        historical_items = historical_df.groupby(['item_sku', 'year_week']).agg({
            'final_price': 'sum'
        }).reset_index()

        outliers = []
        for _, item in current_week_items.iterrows():
            historical_sales = historical_items[historical_items['item_sku'] == item['item_sku']]

            if not historical_sales.empty:
                hist_mean = historical_sales['final_price'].mean()
                hist_std = historical_sales['final_price'].std()

                if hist_std > 0:
                    z_score = (float(item['final_price']) - hist_mean) / hist_std
                    if abs(z_score) > self.z_score_threshold:
                        outliers.append({
                            'item_sku': item['item_sku'],
                            'item_name': item['item_name'],
                            'total_sales': float(item['final_price']),
                            'historical_mean_sales': float(hist_mean),
                            'z_score': z_score,
                            'deviation_percentage': ((float(item['final_price']) - hist_mean) / hist_mean) * 100
                        })

        return outliers

    # analysis/weekly_sales_analyzer.py

    def _detect_category_outliers(self, df: pd.DataFrame, start_date: date, end_date: date) -> List[Dict]:
        """Detect categories with unusual sales patterns in the week"""
        if df.empty:
            return []

        # Add year-week column before using it
        df['year_week'] = df['created_time'].dt.strftime('%Y-%U')

        current_week_mask = (df['date'] >= start_date) & (df['date'] <= end_date)

        # Group by category and calculate weekly totals
        current_week_categories = df[current_week_mask].groupby('category_name').agg({
            'final_price': 'sum'
        }).reset_index()

        # Historical comparison
        historical_df = df[df['date'] < start_date]
        historical_categories = historical_df.groupby(['category_name', 'year_week']).agg({
            'final_price': 'sum'
        }).reset_index()

        outliers = []
        for _, category in current_week_categories.iterrows():
            if pd.isna(category['category_name']):
                continue

            historical_sales = historical_categories[
                historical_categories['category_name'] == category['category_name']
                ]

            if not historical_sales.empty:
                hist_mean = historical_sales['final_price'].mean()
                hist_std = historical_sales['final_price'].std()

                if hist_std > 0:
                    z_score = (float(category['final_price']) - hist_mean) / hist_std
                    if abs(z_score) > self.z_score_threshold:
                        outliers.append({
                            'category_name': category['category_name'],
                            'total_sales': float(category['final_price']),
                            'historical_mean_sales': float(hist_mean),
                            'z_score': z_score,
                            'deviation_percentage': ((float(category['final_price']) - hist_mean) / hist_mean) * 100
                        })

        return outliers

    def _detect_tip_outliers(self, df: pd.DataFrame, start_date: date, end_date: date) -> List[Dict]:
        """Detect orders with unusual tip amounts in the week"""
        # Calculate tip percentages for all orders
        df = df.copy()  # Create a copy to avoid modifying the original DataFrame
        df['tip_percentage'] = df.apply(
            lambda row: (float(row['tip_amount']) / float(row['total'])) * 100 if float(row['total']) > 0 else 0,
            axis=1
        )

        current_week_mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        current_week_orders = df[current_week_mask]
        historical_orders = df[df['date'] < start_date]

        # Calculate historical statistics
        hist_mean = historical_orders['tip_amount'].mean()
        hist_std = historical_orders['tip_amount'].std()

        if hist_std == 0:
            return []

        outliers = []
        for _, order in current_week_orders.iterrows():
            if float(order['tip_amount']) > 0:  # Only analyze orders with tips
                z_score = (float(order['tip_amount']) - hist_mean) / hist_std
                if abs(z_score) > self.z_score_threshold:
                    # Get detailed order information
                    order_details = self.repository.get_order_by_id(order['order_id'])
                    if order_details:
                        outliers.append({
                            'order_id': order['order_id'],
                            'total': float(order['total']),
                            'tip_amount': float(order['tip_amount']),
                            'tip_percentage': float(order['tip_percentage']),
                            'z_score': z_score,
                            'historical_mean': hist_mean,
                            'deviation_percentage': ((float(order['tip_amount']) - hist_mean) / hist_mean) * 100,
                            'delivery_method': order['delivery_method'],
                            'delivery_platform': order['delivery_platform'],
                            'items': order_details.items
                        })

        return outliers

    def _get_daily_breakdown(self, df: pd.DataFrame, start_date: date, end_date: date) -> List[Dict]:
        """Get daily breakdown of sales metrics within the week"""
        daily_mask = (df['date'] >= start_date) & (df['date'] <= end_date)
        daily_df = df[daily_mask]

        # Group by date and calculate metrics
        daily_stats = daily_df.groupby('date').agg({
            'total': 'sum',
            'tip_amount': 'sum'
        }).reset_index()

        # Get modifications and discounts for each day
        daily_breakdown = []
        for _, row in daily_stats.iterrows():
            current_date = row['date']

            # Get daily modifications and discounts
            day_mods = self._get_modifications_totals(current_date, current_date)

            daily_breakdown.append({
                'date': current_date,
                'total_sales': float(row['total']),
                'total_tips': float(row['tip_amount']),
                'total_mods': float(day_mods.get('total_mods', 0)),
                'order_discounts': float(day_mods.get('order_discounts', 0)),
                'item_discounts': float(day_mods.get('item_discounts', 0))
            })

        return daily_breakdown

    def _get_modifications_totals(self, start_date: date, end_date: date) -> Dict:
        """Helper method to get modifications and discounts totals for a date range"""
        # Convert dates to datetime for database queries
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(end_date, datetime.max.time())

        # Using the repository to fetch the data
        daily_summary, _ = self.repository.get_daily_summary(start_datetime, end_datetime)
        return daily_summary

    def _get_historical_modifications_averages(self, current_date: date) -> Dict:
        """Helper method to get historical averages for modifications and discounts"""
        start_date = current_date - timedelta(days=self.lookback_days)
        start_datetime = datetime.combine(start_date, datetime.min.time())
        end_datetime = datetime.combine(current_date, datetime.min.time())

        # Using the repository to fetch the data
        _, historical_summary = self.repository.get_daily_summary(start_datetime, end_datetime)
        return historical_summary