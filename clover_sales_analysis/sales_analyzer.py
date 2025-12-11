from datetime import datetime, timedelta
from typing import List, Dict, Tuple, Any
import pandas as pd
from clover_sales_analysis.repository import SalesRepository


class SalesAnalyzer:
    def __init__(self):
        self.repository = SalesRepository()
        self.z_score_threshold = 2
        self.lookback_days = 60

    def analyze_date(self, analysis_date: datetime) -> Dict[str, Any]:
        """Perform complete analysis for a given date"""
        start_date = analysis_date - timedelta(days=self.lookback_days)
        end_date = analysis_date + timedelta(days=1)

        orders_df = self.repository.get_historical_orders(start_date, end_date)
        items_df = self.repository.get_item_sales(start_date, end_date)

        if orders_df.empty or items_df.empty:
            return {
                'success': False,
                'message': 'No data available for the selected date.'
            }

        results = {
            'success': True,
            'order_outliers': self.detect_order_outliers(orders_df, analysis_date),
            'item_outliers': self.detect_item_outliers(items_df, analysis_date),
            'category_outliers': self.detect_category_outliers(items_df, analysis_date),
            'tip_outliers': self.detect_tip_outliers(orders_df, analysis_date)
        }

        daily_summary, historical_summary = self.repository.get_daily_summary(start_date, end_date)
        results['daily_summary'] = daily_summary
        results['historical_summary'] = historical_summary

        return results

    def detect_order_outliers(self, df: pd.DataFrame, analysis_date: datetime) -> List[Dict]:
        """Detect order outliers with a higher z-score threshold"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()
        order_z_threshold = 3  # Specific threshold for orders

        analysis_df = df[df['created_time'].dt.date == analysis_date.date()]
        historical_df = df[
            (df['created_time'].dt.date < analysis_date.date()) &
            (df['weekday'] == weekday)
            ]

        if historical_df.empty or analysis_df.empty:
            return []

        mean_total = historical_df['total'].astype(float).mean()
        std_total = historical_df['total'].astype(float).std()

        if std_total == 0:
            return []

        outliers = []
        for _, row in analysis_df.iterrows():
            total = float(row['total'])
            z_score = (total - mean_total) / std_total
            if abs(z_score) > order_z_threshold:
                order_items = self.repository.get_order_items(row['order_id'])

                outliers.append({
                    'order_id': row['order_id'],
                    'total': total,
                    'created_time': row['created_time'],
                    'z_score': z_score,
                    'historical_mean': mean_total,
                    'deviation_percentage': ((total - mean_total) / mean_total) * 100,
                    'delivery_method': row['delivery_method'],
                    'delivery_platform': row['delivery_platform'],
                    'tip_amount': row['tip_amount'],
                    'items': order_items
                })

        return outliers

    def detect_item_outliers(self, df: pd.DataFrame, analysis_date: datetime) -> List[Dict]:
        """Detect items with unusual sales patterns"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        # Group by item and date
        df['date'] = df['created_time'].dt.date
        df['final_price'] = df['final_price'].astype(float)

        price_outliers = []

        for item_sku in df['item_sku'].unique():
            if pd.isna(item_sku):
                continue

            item_df = df[df['item_sku'] == item_sku]

            # Daily aggregations
            daily_stats = item_df.groupby(['date', 'weekday']).agg({
                'final_price': ['sum', 'count'],
                'item_name': 'first'
            }).reset_index()

            daily_stats.columns = ['date', 'weekday', 'total_sales', 'quantity', 'item_name']

            # Filter for same weekday
            historical = daily_stats[
                (daily_stats['date'] < analysis_date.date()) &
                (daily_stats['weekday'] == weekday)
                ]
            current = daily_stats[daily_stats['date'] == analysis_date.date()]

            if len(historical) < 2 or historical.empty or current.empty:
                continue

            # Check sales amount
            sales_mean = historical['total_sales'].astype(float).mean()
            sales_std = historical['total_sales'].astype(float).std()

            if sales_std == 0:
                continue

            for _, row in current.iterrows():
                total_sales = float(row['total_sales'])
                sales_z_score = (total_sales - sales_mean) / sales_std
                if abs(sales_z_score) > self.z_score_threshold:
                    price_outliers.append({
                        'item_sku': item_sku,
                        'item_name': row['item_name'],
                        'total_sales': total_sales,
                        'historical_mean_sales': sales_mean,
                        'z_score': sales_z_score,
                        'deviation_percentage': ((total_sales - sales_mean) / sales_mean) * 100
                    })

        return price_outliers

    def detect_category_outliers(self, df: pd.DataFrame, analysis_date: datetime) -> List[Dict]:
        """Detect categories with unusual sales patterns"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        # Group by category and date
        df['date'] = df['created_time'].dt.date
        df['final_price'] = df['final_price'].astype(float)

        category_outliers = []

        for category in df['category_name'].unique():
            if pd.isna(category):
                continue

            cat_df = df[df['category_name'] == category]

            # Daily aggregations
            daily_stats = cat_df.groupby(['date', 'weekday']).agg({
                'final_price': ['sum', 'count'],
                'category_name': 'first'
            }).reset_index()

            daily_stats.columns = ['date', 'weekday', 'total_sales', 'quantity', 'category_name']

            # Filter for same weekday
            historical = daily_stats[
                (daily_stats['date'] < analysis_date.date()) &
                (daily_stats['weekday'] == weekday)
                ]
            current = daily_stats[daily_stats['date'] == analysis_date.date()]

            if historical.empty or current.empty:
                continue

            # Calculate statistics
            sales_mean = historical['total_sales'].astype(float).mean()
            sales_std = historical['total_sales'].astype(float).std()

            if sales_std == 0:
                continue

            for _, row in current.iterrows():
                total_sales = float(row['total_sales'])
                sales_z_score = (total_sales - sales_mean) / sales_std
                if abs(sales_z_score) > self.z_score_threshold:
                    category_outliers.append({
                        'category_name': category,
                        'total_sales': total_sales,
                        'historical_mean_sales': sales_mean,
                        'z_score': sales_z_score,
                        'deviation_percentage': ((total_sales - sales_mean) / sales_mean) * 100
                    })

        return category_outliers

    def detect_tip_outliers(self, df: pd.DataFrame, analysis_date: datetime) -> List[Dict]:
        """Detect orders with unusual tip amounts"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        # Calculate tip percentage
        df['tip_percentage'] = df.apply(
            lambda row: (float(row['tip_amount']) / float(row['total'])) * 100 if float(row['total']) > 0 else 0,
            axis=1
        )

        # Filter for orders with positive tips
        analysis_df = df[
            (df['created_time'].dt.date == analysis_date.date()) &
            (df['tip_amount'] > 0)
        ]

        historical_df = df[
            (df['created_time'].dt.date < analysis_date.date()) &
            (df['weekday'] == weekday) &
            (df['tip_amount'] > 0)
        ]

        if historical_df.empty or analysis_df.empty:
            return []

        mean_tip = historical_df['tip_amount'].astype(float).mean()
        std_tip = historical_df['tip_amount'].astype(float).std()

        if std_tip == 0:
            return []

        outliers = []
        for _, row in analysis_df.iterrows():
            tip = float(row['tip_amount'])
            if tip > 0:  # Only analyze orders with tips
                z_score = (tip - mean_tip) / std_tip
                if abs(z_score) > self.z_score_threshold:
                    order_items = self.repository.get_order_items(row['order_id'])

                    outliers.append({
                        'order_id': row['order_id'],
                        'total': row['total'],
                        'tip_amount': tip,
                        'tip_percentage': row['tip_percentage'],
                        'z_score': z_score,
                        'historical_mean': mean_tip,
                        'deviation_percentage': ((tip - mean_tip) / mean_tip) * 100,
                        'delivery_method': row['delivery_method'],
                        'delivery_platform': row['delivery_platform'],
                        'items': order_items
                    })

        return outliers