# to run test: "pytest --cov=. tests/ -v" in terminal

from concurrent.futures import ThreadPoolExecutor, as_completed
from config import secrets
from datetime import datetime
from typing import List, Dict, Any, Tuple, Optional, Set
import streamlit as st
import requests
import pytz
import re
import time
import json
from shared.database_operations import DatabaseOperations
from ratelimit import limits, sleep_and_retry


class Config:
    API_BASE_URL = "https://api.clover.com/v3/merchants"
    
    # API Rate limits
    REQUESTS_PER_MINUTE = 200

    # Batch processing settings
    MAX_WORKERS = 30
    BATCH_SIZE = 100
    
    @staticmethod
    def validate_config() -> None:
        """Validate that required keys exist. Raises KeyError with helpful message if missing."""
        required_keys = ['clover_api_key', 'clover_merchant_id']
        missing_keys = [key for key in required_keys if key not in secrets]
        if missing_keys:
            available_keys = list(secrets.keys())
            error_msg = f"Missing required configuration keys: {', '.join(missing_keys)}"
            if available_keys:
                error_msg += f"\nAvailable keys in secrets: {', '.join(available_keys[:10])}"  # Show first 10
            raise KeyError(error_msg)
    
    @staticmethod
    def get_clover_api_key() -> str:
        """Get Clover API key with validation"""
        # Try different possible key names
        possible_keys = ['clover_api_key', 'CLOVER_API_KEY', 'clover_apikey', 'CLOVER_APIKEY']
        for key in possible_keys:
            if key in secrets:
                return secrets.get(key, '')
        
        # If not found, validate and show error
        Config.validate_config()
        return secrets.get('clover_api_key', '')
    
    @staticmethod
    def get_clover_merchant_id() -> str:
        """Get Clover merchant ID with validation"""
        # Try different possible key names
        possible_keys = ['clover_merchant_id', 'CLOVER_MERCHANT_ID', 'clover_merchantid', 'CLOVER_MERCHANTID']
        for key in possible_keys:
            if key in secrets:
                return secrets.get(key, '')
        
        # If not found, validate and show error
        Config.validate_config()
        return secrets.get('clover_merchant_id', '')


class DeliveryInfo:
    PLATFORMS = {
        'DOORDASH': 'Doordash',
        'UBER EATS': 'UberEats',
        'DEFAULT': 'In-Store'
    }

    @classmethod
    def parse_delivery_info(cls, note: str) -> Tuple[str, str, Optional[str]]:
        platform = next((cls.PLATFORMS[key] for key in cls.PLATFORMS if key in note), cls.PLATFORMS['DEFAULT'])
        method = 'Delivery' if 'DELIVERY' in note else 'Pickup'

        time_match = re.search(r'\b([01]?\d|2[0-3]):[0-5]\d\b', note)
        delivery_time = time_match.group(0) if time_match else None

        return platform, method, delivery_time


class CloverAPI:
    def __init__(self):
        self.config = Config()
        self._setup_session()

    def _setup_session(self):
        adapter = requests.adapters.HTTPAdapter(
            pool_connections=20,
            pool_maxsize=20,
            max_retries=3,
            pool_block=True
        )
        self._session = requests.Session()
        self._session.mount('https://', adapter)
        self._session.headers.update({"Authorization": f"Bearer {self.config.get_clover_api_key()}"})

    def _make_request(self, url: str, params: Dict = None) -> Dict:
        response = self._session.get(url, params=params)
        response.raise_for_status()
        return response.json()

    @sleep_and_retry
    @limits(calls=Config.REQUESTS_PER_MINUTE, period=60)
    def fetch_orders(self, start_date: datetime, offset: int = 0) -> List[Dict[str, Any]]:
        url = f"{self.config.API_BASE_URL}/{self.config.get_clover_merchant_id()}/orders"
        params = {
            "filter": f"createdTime>{int(start_date.timestamp() * 1000)}",
            "expand": "lineItems,lineItems.modifications,payments,discounts",
            "limit": 100,
            "offset": offset
        }
        response = self._make_request(url, params)
        return response.get('elements', [])

    def _fetch_line_items_batch(self, order_ids: Set[str]) -> List[Dict[str, Any]]:
        """Fetch line items for multiple orders concurrently."""
        def fetch_single_order(order_id: str) -> Dict[str, Any]:
            url = f"{self.config.API_BASE_URL}/{self.config.get_clover_merchant_id()}/orders/{order_id}/line_items"
            params = {"expand": "discounts,modifications"}

            for attempt in range(3):
                try:
                    time.sleep(0.25)
                    items = self._make_request(url, params).get('elements', [])
                    return {"order_id": order_id, "items": items}
                except Exception:
                    if attempt == 2:
                        return {"order_id": order_id, "items": []}
                    time.sleep(1)

            return {"order_id": order_id, "items": []}

        with ThreadPoolExecutor(max_workers=4) as executor:
            futures = []
            for order_id in order_ids:
                futures.append(executor.submit(fetch_single_order, order_id))
                time.sleep(0.25)

            return [future.result() for future in as_completed(futures)]

    def fetch_all_orders(self, start_date: datetime) -> List[Dict[str, Any]]:
        all_orders = []
        offset = 0

        while True:
            orders = self.fetch_orders(start_date, offset)
            if not orders:
                break
            all_orders.extend(orders)
            offset += len(orders)

        if not all_orders:
            return []

        order_batches = [all_orders[i:i + self.config.BATCH_SIZE]
                         for i in range(0, len(all_orders), self.config.BATCH_SIZE)]

        for batch in order_batches:
            order_ids = {order['id'] for order in batch}
            line_items_results = self._fetch_line_items_batch(order_ids)

            line_items_map = {result['order_id']: result['items']
                              for result in line_items_results}

            for order in batch:
                order['detailed_line_items'] = line_items_map.get(order['id'], [])

        return all_orders


class CloverOrder:
    def __init__(self, order_data: Dict[str, Any]):
        self.order_data = order_data
        self.modification_prices = {}
        self.detailed_items = {
            item['id']: item
            for item in order_data.get('detailed_line_items', [])
            if item and 'id' in item
        }
        self.est_tz = pytz.timezone('America/New_York')

        # Store raw JSON responses
        self.order_raw_json = json.dumps(self._clean_order_data())
        self.lineitems_raw_json = json.dumps(order_data.get('detailed_line_items', []))

    def _clean_order_data(self) -> Dict:
        """Create a clean copy of order data without detailed line items"""
        clean_data = self.order_data.copy()
        clean_data.pop('detailed_line_items', None)
        return clean_data

    def _convert_to_est(self, timestamp_ms: int) -> str:
        utc_time = datetime.fromtimestamp(timestamp_ms / 1000, pytz.utc)
        est_time = utc_time.astimezone(self.est_tz)
        return est_time.strftime('%Y-%m-%d %H:%M:%S')

    def _process_discount(self, discount: Dict) -> Tuple[str, float, float]:
        name = discount.get('name', '')

        if 'percentage' in discount:
            return name, float(discount.get('percentage', 0)), 0.0
        elif 'amount' in discount:
            amount = abs(float(discount.get('amount', 0)) / 100)
            return name, 0.0, amount

        return '', 0.0, 0.0

    def get_order_level_discount(self) -> Tuple[str, float, float]:
        discounts = self.order_data.get('discounts', {}).get('elements', [])
        return self._process_discount(discounts[0]) if discounts else ('', 0.0, 0.0)

    def get_order_details(self) -> Tuple:
        delivery_note = self.order_data.get('note', '')
        platform, method, time = DeliveryInfo.parse_delivery_info(delivery_note)

        return (
            self.order_data['id'],
            self._convert_to_est(self.order_data['createdTime']),
            delivery_note,
            platform,
            method,
            time,
            self.order_data.get('currency', ''),
            self.order_data.get('total', 0) / 100,
            self.order_data.get('externalReferenceId', ''),
            self.order_data.get('employee', {}).get('id', ''),
            *self.get_order_level_discount(),
            self.order_raw_json,
            self.lineitems_raw_json
        )

    def get_items(self) -> List[Tuple]:
        items = []
        for item in self.order_data.get('lineItems', {}).get('elements', []):
            item_id = item.get('id')
            detailed_item = self.detailed_items.get(item_id, {})

            price = item.get('price', 0) / 100
            mod_total = self._calculate_modifications_total(item_id, detailed_item, item)
            price_with_mod = price + mod_total

            discount_info = self._process_item_discount(detailed_item, price_with_mod)

            items.append((
                item_id,
                self.order_data['id'],
                item.get('name'),
                price,
                price_with_mod,
                *discount_info,
                item.get('item', {}).get('id', ''),
                item.get('itemCode'),
                item.get('note')
            ))

        return items

    def _calculate_modifications_total(self, item_id: str, detailed_item: Dict, item: Dict) -> float:
        mod_total = 0
        modifications = (detailed_item.get('modifications', {}) or item.get('modifications', {}))

        if modifications:
            for mod in modifications.get('elements', []):
                mod_price = mod.get('amount', 0) / 100
                mod_total += mod_price
                self.modification_prices[(item_id, mod.get('name'))] = mod_price

        return mod_total

    def _process_item_discount(self, detailed_item: Dict, price_with_mod: float) -> Tuple:
        discount_name = ''
        discount_percentage = 0.0
        discount_amount = 0.0
        final_price = price_with_mod

        detailed_discounts = detailed_item.get('discounts', {}).get('elements', [])
        if detailed_discounts:
            name, percentage, amount = self._process_discount(detailed_discounts[0])
            discount_name = name

            if percentage:
                discount_percentage = percentage
                discount_amount = price_with_mod * (percentage / 100)
            else:
                discount_amount = amount

            final_price = price_with_mod - discount_amount

        return final_price, discount_name, discount_percentage, discount_amount

    def get_modifications(self) -> List[Tuple]:
        return [
            (item_id, mod.get('name'), self.modification_prices.get((item_id, mod.get('name')), 0))
            for item in self.order_data.get('lineItems', {}).get('elements', [])
            for item_id in [item.get('id')]
            for mod in item.get('modifications', {}).get('elements', [])
        ]

    def get_payments(self) -> List[Tuple]:
        return [
            (
                self.order_data['id'],
                payment.get('tipAmount', 0) / 100,
                payment.get('taxAmount', 0) / 100
            )
            for payment in self.order_data.get('payments', {}).get('elements', [])
        ]


class CloverSalesImporter:
    def __init__(self):
        self.db_ops = DatabaseOperations()
        self.api = CloverAPI()

    def run_update(self) -> None:
        try:
            start_date = self.db_ops.get_latest_order_date()
            st.write(f"Fetching orders since: {start_date}")

            raw_orders = self.api.fetch_all_orders(start_date)
            if raw_orders:
                processed_orders = [CloverOrder(order) for order in raw_orders]
                self.db_ops.save_orders(processed_orders)
                self._display_summary(start_date)
            else:
                st.info('No new orders to import.')
        except Exception as e:
            st.error(f"Update failed: {str(e)}")

    def _display_summary(self, start_date: datetime) -> None:
        summary = self.db_ops.get_summary(start_date)
        st.success('Data upload completed successfully.')
        for row in summary:
            st.write(f"{row['date']}: {row['orders']} orders - Total: ${row['total']:.2f} CAD")


def main():
    st.set_page_config(
        page_icon=":hot_pepper:",
        menu_items={'About': "# Ivan to the Rescue!. Find *Ivan* and ask him!"}
    )

    st.title("Import Clover Sales")
    
    # Check if configuration is available
    try:
        Config.validate_config()
        config_ok = True
    except KeyError as e:
        config_ok = False
        st.error(f"⚠️ **Configuration required**: {str(e)}")
        st.info("""
        **To use this tool, you need to configure in `.streamlit/secrets.toml`:**
        - `clover_api_key`: Your Clover API key
        - `clover_merchant_id`: Your Clover Merchant ID
        """)
        with st.expander("🔍 View available keys in secrets"):
            try:
                available = list(secrets.keys())
                if available:
                    st.write("**Keys found:**")
                    for key in available:
                        st.write(f"- `{key}`")
                else:
                    st.write("No keys found in secrets.")
            except Exception as e:
                st.write(f"Error reading secrets: {e}")

    if config_ok:
        try:
            importer = CloverSalesImporter()
            if st.button('Run Update'):
                importer.run_update()
        except KeyError as e:
            st.error(f"Configuration error: {str(e)}")
        except Exception as e:
            st.error(f"Error initializing: {str(e)}")


if __name__ == "__main__":
    main()