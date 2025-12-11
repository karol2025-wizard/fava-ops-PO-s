from datetime import datetime, timedelta
import pandas as pd
from silverware_sales_analysis.repository import SalesRepository

class SalesAnalyzer:
    def __init__(self):
        self.repository = SalesRepository()
        self.z_score_threshold = 2
        self.lookback_days = 60

    def analyze_date(self, analysis_date: datetime):
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

    def detect_order_outliers(self, df: pd.DataFrame, analysis_date: datetime):
        """Detect order outliers"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        analysis_df = df[df['start_date'].dt.date == analysis_date.date()]
        historical_df = df[
            (df['start_date'].dt.date < analysis_date.date()) &
            (df['weekday'] == weekday)
        ]

        if historical_df.empty or analysis_df.empty:
            return []

        mean_total = historical_df['total'].mean()
        std_total = historical_df['total'].std()

        if std_total == 0:
            return []

        outliers = []
        for _, row in analysis_df.iterrows():
            total = row['total']
            z_score = (total - mean_total) / std_total
            if abs(z_score) > self.z_score_threshold:
                outliers.append({
                    'order_id': row['check_number'],
                    'total': total,
                    'z_score': z_score,
                    'historical_mean': mean_total,
                    'deviation_percentage': ((total - mean_total) / mean_total) * 100
                })

        return outliers

    def detect_item_outliers(self, df: pd.DataFrame, analysis_date: datetime):
        """Detect items with unusual sales patterns"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        df['date'] = df['start_date'].dt.date
        df['price'] = df['price'].astype(float)

        outliers = []

        for item_sku in df['item_sku'].unique():
            item_df = df[df['item_sku'] == item_sku]

            # Get item name once for this SKU
            item_name = item_df['item_name'].iloc[0] if not item_df.empty else item_sku

            historical = item_df[
                (item_df['date'] < analysis_date.date()) &
                (item_df['weekday'] == weekday)
                ]

            current = item_df[item_df['date'] == analysis_date.date()]

            if historical.empty or current.empty:
                continue

            # Calculate daily totals
            historical_daily = historical.groupby('date')['price'].sum()
            current_daily = current.groupby('date')['price'].sum()

            sales_mean = historical_daily.mean()
            sales_std = historical_daily.std()

            if sales_std == 0:
                continue

            current_total = current_daily.iloc[0] if not current_daily.empty else 0
            z_score = (current_total - sales_mean) / sales_std

            if abs(z_score) > self.z_score_threshold:
                outliers.append({
                    'item_sku': item_sku,
                    'item_name': item_name,  # Include item name
                    'total_sales': current_total,  # Use total sales instead of individual price
                    'z_score': z_score,
                    'historical_mean': sales_mean,
                    'deviation_percentage': ((current_total - sales_mean) / sales_mean) * 100
                })

        return outliers

    def detect_category_outliers(self, df: pd.DataFrame, analysis_date: datetime):
        """Detect categories with unusual sales patterns"""
        if df.empty:
            return []

        weekday = analysis_date.weekday()

        df['date'] = df['start_date'].dt.date
        df['price'] = df['price'].astype(float)

        outliers = []

        for category in df['category_name'].unique():
            if pd.isna(category):  # Skip if category is None/NaN
                continue

            category_df = df[df['category_name'] == category]

            historical = category_df[
                (category_df['date'] < analysis_date.date()) &
                (category_df['weekday'] == weekday)
                ]

            current = category_df[category_df['date'] == analysis_date.date()]

            if historical.empty or current.empty:
                continue

            # Calculate daily totals
            historical_daily = historical.groupby('date')['price'].sum()
            current_daily = current.groupby('date')['price'].sum()

            sales_mean = historical_daily.mean()
            sales_std = historical_daily.std()

            if sales_std == 0:
                continue

            current_total = current_daily.iloc[0] if not current_daily.empty else 0
            z_score = (current_total - sales_mean) / sales_std

            if abs(z_score) > self.z_score_threshold:
                outliers.append({
                    'category_name': category,
                    'total_sales': current_total,  # Use total sales instead of individual price
                    'z_score': z_score,
                    'historical_mean': sales_mean,
                    'deviation_percentage': ((current_total - sales_mean) / sales_mean) * 100
                })

        return outliers

    def detect_tip_outliers(self, df: pd.DataFrame, analysis_date: datetime):
        """Detect orders with unusual tip amounts"""
        if df.empty:
            return []

        df['tip_percentage'] = df.apply(
            lambda row: (row['tip_amount'] / row['total']) * 100 if row['total'] > 0 else 0,
            axis=1
        )

        weekday = analysis_date.weekday()

        historical = df[
            (df['start_date'].dt.date < analysis_date.date()) &
            (df['weekday'] == weekday) &
            (df['tip_amount'] > 0)
        ]

        current = df[
            (df['start_date'].dt.date == analysis_date.date()) &
            (df['tip_amount'] > 0)
        ]

        if historical.empty or current.empty:
            return []

        mean_tip = historical['tip_amount'].mean()
        std_tip = historical['tip_amount'].std()

        if std_tip == 0:
            return []

        outliers = []
        for _, row in current.iterrows():
            z_score = (row['tip_amount'] - mean_tip) / std_tip
            if abs(z_score) > self.z_score_threshold:
                outliers.append({
                    'order_id': row['check_number'],
                    'tip_amount': row['tip_amount'],
                    'z_score': z_score,
                    'historical_mean': mean_tip,
                    'deviation_percentage': ((row['tip_amount'] - mean_tip) / mean_tip) * 100
                })

        return outliers
