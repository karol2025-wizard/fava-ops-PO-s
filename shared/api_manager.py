# api_manager.py
import requests
from requests.auth import HTTPBasicAuth
from config import secrets
from typing import Optional, Dict, List, Any, Union

# Configuration
BASE_URL = 'https://api.mrpeasy.com/rest/v1'

class APIManager:
    def __init__(self):
        self.base_url = BASE_URL
        # Access secrets safely when initializing, not at module level
        try:
            mrp_secret_key = secrets.get('MRPEASY_API_KEY', '')
            mrp_secret_secret = secrets.get('MRPEASY_API_SECRET', '')
            if not mrp_secret_key or not mrp_secret_secret:
                raise ValueError("MRPEASY_API_KEY and MRPEASY_API_SECRET must be set in secrets")
            self.auth = HTTPBasicAuth(mrp_secret_key, mrp_secret_secret)
        except (KeyError, TypeError, ValueError) as e:
            raise ValueError(f"Failed to initialize APIManager: {str(e)}. Please check your secrets configuration.")

    def fetch_routings(self):
        """Fetch all routings from MRPeasy"""
        routings = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/routings",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                current_routings = response.json()
                if not current_routings:
                    break
                routings.extend(current_routings)
                start += 100
            else:
                return None
        return routings

    def fetch_routing_by_code(self, routing_code: str) -> Optional[Dict]:
        """Fetch a specific routing by code from MRPeasy
        
        Args:
            routing_code (str): The routing code to fetch
            
        Returns:
            Optional[Dict]: The routing data if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/routings",
                auth=self.auth,
                params={'code': routing_code},
                headers={'content-type': 'application/json'}
            )
            
            if response.status_code == 200:
                routings = response.json()
                return routings[0] if routings else None
            return None
        except Exception as e:
            print(f"Error fetching routing: {e}")
            return None

    def fetch_boms(self):
        """Fetch all bills of materials from MRPeasy"""
        boms = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/boms",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                current_boms = response.json()
                if not current_boms:
                    break
                boms.extend(current_boms)
                start += 100
            else:
                return None
        return boms

    def fetch_bom_by_product_id(self, product_id: int) -> Optional[List[Dict]]:
        """Fetch bills of materials for a specific product ID"""
        try:
            response = requests.get(
                f"{self.base_url}/boms",
                auth=self.auth,
                params={'product_id': product_id},
                headers={'content-type': 'application/json'}
            )
            if response.status_code == 200:
                return response.json()
            else:
                print(f"Error fetching BOM for product ID {product_id}: {response.status_code}")
                return None
        except Exception as e:
            print(f"Exception fetching BOM: {e}")
            return None

    def fetch_units(self) -> Optional[List[Dict]]:
        """Fetch all units of measurement from MRPeasy"""
        try:
            units = []
            start = 0
            while True:
                response = requests.get(
                    f"{self.base_url}/units",
                    auth=self.auth,
                    headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
                )
                if response.status_code in [200, 206]:
                    current_units = response.json()
                    if not current_units:
                        break
                    units.extend(current_units)
                    if len(current_units) < 100:
                        break
                    start += 100
                else:
                    print(f"Error fetching units: {response.status_code}")
                    return None
            return units
        except Exception as e:
            print(f"Exception fetching units: {e}")
            return None

    def fetch_vendors(self):
        vendors = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/vendors",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                current_vendors = response.json()
                if not current_vendors:
                    break
                vendors.extend(current_vendors)
                start += 100
            else:
                return None
        return vendors

    def fetch_all_products(self):
        all_products = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/items",  # Adjust endpoint as necessary,
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start+99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                products = response.json()
                if not products:
                    break
                all_products.extend(products)
                start += 100
            else:
                return None
        return all_products

    def get_manufacturing_order_by_code(self, mo_code: str) -> Optional[Dict]:
        try:
            print(f"Attempting to fetch MO with code: {mo_code}")
            response = requests.get(
                f"{self.base_url}/manufacturing-orders",
                auth=self.auth,
                params={'code': mo_code},
                headers={'content-type': 'application/json'}
            )
            print(f"API Response status: {response.status_code}")
            print(f"API Response content: {response.text}")

            if response.status_code == 200:
                orders = response.json()
                print(f"Parsed orders: {orders}")
                return orders[0] if orders else None
            return None
        except Exception as e:
            print(f"Error fetching manufacturing order: {e}")
            return None

    def get_manufacturing_order_details(self, mo_id: int):
        """Fetch complete details for a specific manufacturing order - by MO_ID"""
        response = requests.get(
            f"{self.base_url}/manufacturing-orders/{mo_id}",
            auth=self.auth,
            headers={'content-type': 'application/json'}
        )

        if response.status_code == 200:
            return response.json()
        else:
            return None

    def fetch_manufacturing_orders(self, **filters):
        """Fetch manufacturing orders with optional filtering

        Args:
            **filters: Optional filter parameters such as:
                - status: Status code to filter by
                - created_min: Minimum creation date (YYYY-MM-DD or timestamp)
                - created_max: Maximum creation date (YYYY-MM-DD or timestamp)
                - due_date_min: Minimum due date (YYYY-MM-DD or timestamp)
                - due_date_max: Maximum due date (YYYY-MM-DD or timestamp)
                - start_date_min: Minimum start date (YYYY-MM-DD or timestamp)
                - start_date_max: Maximum start date (YYYY-MM-DD or timestamp)
                - finish_date_min: Minimum finish date (YYYY-MM-DD or timestamp)
                - finish_date_max: Maximum finish date (YYYY-MM-DD or timestamp)
                - item_code: Filter by item code
                - article_id: Filter by article ID
                - product_id: Filter by product ID
                - group_id: Filter by group ID
                - quantity_min: Minimum quantity
                - quantity_max: Maximum quantity
                - bom_id: Filter by BOM ID
                - routing_id: Filter by routing ID
                - assigned_id: Filter by assigned user ID

        Returns:
            List[Dict]: List of manufacturing orders matching the specified filters
        """
        manufacturing_orders = []
        start = 0

        try:
            import time
            while True:
                response = requests.get(
                    f"{self.base_url}/manufacturing-orders",
                    auth=self.auth,
                    params=filters,
                    headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'},
                    timeout=30  # Add timeout
                )
                
                # Handle rate limiting with retry
                if response.status_code == 429:
                    retry_after = int(response.headers.get('Retry-After', 60))
                    print(f"Rate limit hit. Waiting {retry_after} seconds before retry...")
                    time.sleep(retry_after)
                    continue  # Retry the same request

                if response.status_code in [200, 206]:
                    try:
                        orders = response.json()
                    except ValueError as e:
                        error_msg = f"Failed to parse JSON response. Status: {response.status_code}, Response text: {response.text[:200]}"
                        print(f"Error: {error_msg}")
                        raise ValueError(error_msg)
                    
                    if not orders:
                        break
                    manufacturing_orders.extend(orders)

                    # If we received fewer than 100 records, we've reached the end
                    if len(orders) < 100:
                        break

                    start += 100
                    
                    # Add a small delay between requests to avoid hitting rate limits
                    # Only delay if we're fetching multiple pages
                    if start > 0:
                        time.sleep(0.5)  # 500ms delay between pages
                elif response.status_code == 401:
                    # Unauthorized - credentials issue
                    error_msg = f"Authentication failed (401 Unauthorized). Please check your MRPEASY_API_KEY and MRPEASY_API_SECRET. Response: {response.text[:200]}"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
                elif response.status_code == 403:
                    # Forbidden - permission issue
                    error_msg = f"Access forbidden (403). Your API credentials may not have permission to access manufacturing orders. Response: {response.text[:200]}"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
                elif response.status_code == 404:
                    # Not found - endpoint issue
                    error_msg = f"Endpoint not found (404). The manufacturing-orders endpoint may not be available. Response: {response.text[:200]}"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
                elif response.status_code == 429:
                    # Rate limit exceeded
                    retry_after = response.headers.get('Retry-After', '60')
                    error_msg = (
                        f"Rate limit exceeded (429 Too Many Requests). "
                        f"MRPeasy está limitando las solicitudes. "
                        f"Espera {retry_after} segundos antes de intentar nuevamente. "
                        f"Si estás obteniendo todos los MOs, esto puede tardar varios minutos."
                    )
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
                elif response.status_code >= 500:
                    # Server error
                    error_msg = f"MRPeasy server error ({response.status_code}). The service may be temporarily unavailable. Response: {response.text[:200]}"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)
                else:
                    # Other error
                    error_msg = f"Unexpected response from MRPeasy API. Status: {response.status_code}, Response: {response.text[:200]}"
                    print(f"Error: {error_msg}")
                    raise ValueError(error_msg)

            return manufacturing_orders
        except requests.exceptions.Timeout:
            error_msg = "Request to MRPeasy API timed out. Check your network connection."
            print(f"Error: {error_msg}")
            raise ValueError(error_msg)
        except requests.exceptions.ConnectionError as e:
            error_msg = f"Connection error to MRPeasy API: {str(e)}. Check your internet connection and that MRPeasy service is available."
            print(f"Error: {error_msg}")
            raise ValueError(error_msg)
        except ValueError:
            # Re-raise ValueError (our custom errors)
            raise
        except Exception as e:
            error_msg = f"Unexpected error fetching manufacturing orders: {str(e)}"
            print(f"Error: {error_msg}")
            raise ValueError(error_msg)

    def fetch_customer_orders(self):
        customer_orders = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/customer-orders",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                orders = response.json()
                if not orders:
                    break
                customer_orders.extend(orders)
                start += 100
            else:
                return None
        return customer_orders

    def fetch_purchase_orders(self):
        purchase_orders = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/purchase-orders",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                orders = response.json()
                if not orders:
                    break
                # Filter out orders with specified statuses
                orders = [order for order in orders if order['status'] not in [30, 40, 110, 120]]
                purchase_orders.extend(orders)
                start += 100
            else:
                return None
        return purchase_orders

    def fetch_stock_lots(self):
        stock_lots = []
        start = 0
        while True:
            response = requests.get(
                f"{self.base_url}/lots",
                auth=self.auth,
                headers={'content-type': 'application/json', 'range': f'items={start}-{start + 99}'}
            )
            if response.status_code in [200, 206]:  # OK or Partial Content
                lots = response.json()
                if not lots:
                    break
                stock_lots.extend(lots)
                start += 100
            else:
                return None
        return stock_lots

    def get_item_details(self, item_code: str):
        """Fetch details for a specific item including purchase terms"""
        if not item_code or not item_code.strip():
            return None
            
        item_code = item_code.strip()
        
        response = requests.get(
            f"{self.base_url}/items",
            auth=self.auth,
            params={'code': item_code},
            headers={'content-type': 'application/json'}
        )

        if response.status_code == 200:
            items = response.json()
            # Return the first (and should be only) item matching the code
            if items:
                return items[0]
            else:
                # Try case-insensitive search as fallback
                # Fetch all items and search locally
                all_items = self.fetch_all_products()
                if all_items:
                    # Try exact match first (case-sensitive)
                    for item in all_items:
                        if item.get('code') == item_code:
                            return item
                    # Try case-insensitive match
                    for item in all_items:
                        if item.get('code', '').upper() == item_code.upper():
                            return item
                return None
        else:
            # Log the error for debugging
            print(f"Error fetching item {item_code}: Status {response.status_code}, Response: {response.text}")
            return None

    def create_manufacturing_order(self, item_code=None, article_id=None, quantity=None, assigned_id=1, start_date=None,
                                   custom_40604=None):
        """
        Create a manufacturing order using either item_code or article_id.
        If item_code is provided, it will be used to look up the corresponding article_id.

        Args:
            item_code (str, optional): The item code to use (will be converted to article_id)
            article_id (int, optional): The article ID to use directly
            quantity (float): The quantity to manufacture
            assigned_id (int, optional): The assigned user ID. Defaults to 1.
            start_date (int, optional): The start date as a Unix timestamp
            custom_40604 (str, optional): Daily Group Summary

        Returns:
            Response object from the API call
        """
        # If item_code is provided, look up the corresponding article_id
        if item_code and not article_id:
            # Get item details using the item code
            item = self.get_item_details(item_code)
            if not item:
                # Provide more helpful error message
                error_msg = f"Item with code '{item_code}' not found in MRPEasy system."
                error_msg += " Please verify:"
                error_msg += "\n1. The item code is correct (case-sensitive: e.g., 'A1567' not 'a1567')"
                error_msg += "\n2. The item exists in your MRPEasy account"
                error_msg += "\n3. Your API credentials have access to this item"
                raise ValueError(error_msg)
            article_id = item.get('article_id')
            if not article_id:
                raise ValueError(f"No article_id found for item with code {item_code}. The item may not be properly configured in MRPEasy.")

        # Ensure we have an article_id and quantity
        if not article_id:
            raise ValueError("Either item_code or article_id must be provided")
        if quantity is None:
            raise ValueError("Quantity must be provided")

        order_details = {
            "article_id": article_id,
            "quantity": quantity,
            "assigned_id": assigned_id,
            "no_bookings": 1,
            "no_scheduling": 1
        }

        # Add start_date if provided
        if start_date:
            order_details["start_date"] = start_date

        # Add custom_40604 - Daily Group Summary if provided
        if custom_40604:
            order_details["custom_40604"] = custom_40604

        response = requests.post(
            f"{self.base_url}/manufacturing-orders",
            auth=self.auth,
            headers={'content-type': 'application/json'},
            json=order_details
        )

        if response.status_code == 201:
            print("Manufacturing order created successfully.")
        else:
            print("Failed to create manufacturing order.")

        return response
    
    def update_manufacturing_order(self, mo_id: int, actual_quantity: float = None, 
                                   status: int = None, lot_code: str = None) -> requests.Response:
        """
        Update a manufacturing order with actual produced quantity and status.
        
        Args:
            mo_id: Manufacturing Order ID
            actual_quantity: Actual produced quantity (optional)
            status: Status code (optional). Common statuses: 20=Done, 10=In Progress, etc.
            lot_code: Lot code for confirmation (optional)
        
        Returns:
            Response object from the API call
        """
        # First, get the current MO details
        current_mo = self.get_manufacturing_order_details(mo_id)
        if not current_mo:
            raise ValueError(f"Manufacturing Order {mo_id} not found")
        
        # Prepare update payload
        update_payload = {}
        
        # Update actual quantity if provided
        if actual_quantity is not None:
            update_payload['actual_quantity'] = actual_quantity
        
        # Update status if provided
        if status is not None:
            update_payload['status'] = status
        
        # Note: Lot code confirmation might need to be handled differently
        # depending on MRPeasy API structure. This is a placeholder.
        if lot_code:
            # If MRPeasy supports lot code in update, add it here
            # Otherwise, this might need to be handled via a different endpoint
            pass
        
        # Use PUT method to update (standard REST pattern)
        response = requests.put(
            f"{self.base_url}/manufacturing-orders/{mo_id}",
            auth=self.auth,
            headers={'content-type': 'application/json'},
            json=update_payload
        )
        
        if response.status_code in [200, 204]:
            print(f"Manufacturing order {mo_id} updated successfully.")
        else:
            print(f"Failed to update manufacturing order {mo_id}. Status: {response.status_code}, Response: {response.text}")
        
        return response
    
    def get_lot_details(self, lot_code: str) -> Optional[Dict]:
        """Get details for a specific lot"""
        lots = self.fetch_stock_lots()
        if lots:
            return next((lot for lot in lots if lot['code'] == lot_code), None)
        return None


    def get_containers(self) -> List[Dict]:
        """Get list of containers (group_id 71) with improved error handling"""
        try:
            all_products = self.fetch_all_products()
            if not all_products:
                return []

            containers = [item for item in all_products if item.get('group_id') == 71]
            processed_containers = []
            for container in containers:
                try:
                    # Parse custom_14740 field (weight:uom format)
                    weight_info = container.get('custom_14740', '0:kg').split(':')
                    if len(weight_info) < 2:
                        continue

                    weight = float(weight_info[0]) if weight_info[0] else 0
                    weight_uom = weight_info[1] if weight_info[1] else 'kg'

                    processed_container = {
                        'container_id': container.get('article_id'),
                        'container_code': container.get('code', ''),
                        'container_name': container.get('title', ''),
                        'weight': weight,
                        'weight_uom': weight_uom,
                        'image': container.get('icon')
                    }

                    # Only validate critical fields
                    required_fields = ['container_id', 'container_code', 'container_name', 'weight', 'weight_uom']
                    if all(processed_container[field] not in [None, ''] for field in required_fields):
                        processed_containers.append(processed_container)

                except Exception:
                    continue

            return processed_containers

        except Exception:
            return []

    def get_single_lot(self, lot_code: str) -> Optional[Dict]:
        """Get details for a specific lot by directly querying the API with the lot code.

        Args:
            lot_code (str): The code of the lot to retrieve

        Returns:
            Optional[Dict]: The lot details if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/lots",
                auth=self.auth,
                params={'code': lot_code},
                headers={'content-type': 'application/json'}
            )

            if response.status_code == 200:
                lots = response.json()
                # Return the first (and should be only) lot matching the code
                return lots[0] if lots else None
            return None
        except Exception:
            return None

    def get_single_purchase_order(self, pur_ord_id: int) -> Optional[Dict]:
        """Get details for a specific purchase order by ID.

        Args:
            pur_ord_id (int): The ID of the purchase order to retrieve

        Returns:
            Optional[Dict]: The purchase order details if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/purchase-orders/{pur_ord_id}",
                auth=self.auth,
                headers={'content-type': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def fetch_single_purchase_order(self, po_code: str) -> Optional[Dict]:
        """Get details for a specific purchase order by code.

        Args:
            po_code (str): The code of the purchase order to retrieve

        Returns:
            Optional[Dict]: The purchase order details if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/purchase-orders",
                auth=self.auth,
                params={'code': po_code},
                headers={'content-type': 'application/json'}
            )

            if response.status_code == 200:
                orders = response.json()
                # Return the first (and should be only) order matching the code
                return orders[0] if orders else None
            return None
        except Exception:
            return None

    def get_single_purchase_order_code(self, pur_ord_id: int) -> Optional[Dict]:
        """Get details for a specific purchase order by ID.

        Args:
            pur_ord_id (int): The ID of the purchase order to retrieve

        Returns:
            Optional[Dict]: The purchase order details if found, None otherwise
        """
        try:
            response = requests.get(
                f"{self.base_url}/purchase-orders/{pur_ord_id}",
                auth=self.auth,
                headers={'content-type': 'application/json'}
            )

            if response.status_code == 200:
                return response.json()
            return None
        except Exception:
            return None

    def create_customer_order(self, order_data: Dict) -> requests.Response:
        """Create a customer order in MRPeasy

        Args:
            order_data (Dict): Customer order data including:
                - customer_id (int): Customer ID
                - status (str): Order status
                - products (List[Dict]): List of products to order
                - created (int): Unix timestamp
                - reference (str): Order reference
                - notes (str): Order notes

        Returns:
            requests.Response: API response
        """
        response = requests.post(
            f"{self.base_url}/customer-orders",
            auth=self.auth,
            headers={'content-type': 'application/json'},
            json=order_data
        )

        if response.status_code == 201:
            print("Customer order created successfully.")
        else:
            print(f"Failed to create customer order. Status code: {response.status_code}")
            print(f"Error message: {response.text}")

        return response


    def get_complete_lot_details(self, lot_code: str) -> Optional[Dict]:
        """Get complete details for a lot including related item and PO information.
        Uses optimized single queries for lot, item, and purchase order."""
        # Get lot details using the optimized query
        lot_data = self.get_single_lot(lot_code)
        if not lot_data:
            return None

        # Get item details
        item_data = self.get_item_details(lot_data.get('item_code', ''))
        if not item_data:
            return None

        # Initialize units list with the lot's unit
        available_units = [{'unit': lot_data.get('unit', ''), 'source': 'Stock Lot'}]
        vendor_unit = None

        # If purchase order exists, get vendor unit directly from the PO
        pur_ord_id = lot_data.get('pur_ord_id')
        if pur_ord_id:
            po_data = self.get_single_purchase_order(pur_ord_id)
            if po_data:
                for product in po_data.get('products', []):
                    if product.get('article_id') == lot_data.get('article_id'):
                        vendor_unit = product.get('vendor_unit')
                        if vendor_unit:
                            available_units.append({
                                'unit': vendor_unit,
                                'source': 'Vendor'
                            })
                        break

        return {
            'item_name': item_data.get('title', ''),
            'icon': item_data.get('icon'),
            'default_container_id': None,
            'available_units': available_units,
            'default_unit': vendor_unit or lot_data.get('unit', ''),
            'item_code': item_data.get('code', ''),
            'mrpeasy_expiry_timestamp': lot_data.get('expiry')
        }


if __name__ == "__main__":
    test = APIManager()
    bloom = test.fetch_customer_orders()
    print(bloom)