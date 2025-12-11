import requests
import pandas as pd
import json
import logging
from typing import List, Dict, Optional, Any
from config import secrets

BOXHERO_BEARER = secrets['BOXHERO_API_TOKEN']

class BoxHeroAPIManager:
    """A class to manage interactions with the BoxHero API"""

    def __init__(self, debug=False):
        """
        Initialize with the BoxHero API token

        Args:
            debug (bool): Enable debug logging
        """
        self.api_token = BOXHERO_BEARER
        self.base_url = 'https://rest.boxhero-app.com/v1'
        self.headers = {
            'Authorization': f'Bearer {self.api_token}',
            'Content-Type': 'application/json'
        }
        self.debug = debug

        # Set up logging
        logging.basicConfig(level=logging.DEBUG if debug else logging.INFO)
        self.logger = logging.getLogger('BoxHeroAPI')

    def fetch_all_items(self) -> List[Dict[str, Any]]:
        """
        Fetch all items from BoxHero API with pagination support

        Returns:
            List[Dict[str, Any]]: List of item dictionaries
        """
        all_items = []
        cursor = None
        has_more = True

        while has_more:
            try:
                # Prepare request parameters
                params = {}
                if cursor:
                    params['cursor'] = cursor

                # Make API request
                response = requests.get(
                    f'{self.base_url}/items',
                    headers=self.headers,
                    params=params
                )

                # Validate response
                response.raise_for_status()
                data = response.json()

                # Add items to our collection
                if 'items' in data:
                    all_items.extend(data['items'])

                # Update pagination parameters
                has_more = data.get('has_more', False)
                cursor = data.get('cursor')

                # Safety check
                if not cursor and has_more:
                    break

            except requests.exceptions.RequestException as e:
                raise Exception(f"Error fetching items from BoxHero API: {e}")

        return all_items

    def get_inventory_data(self, update_date=None) -> pd.DataFrame:
        """
        Get inventory data formatted as a DataFrame with SKU, quantity, and update date

        Args:
            update_date (str, optional): Date string to use as update date.
                                         If None, current date/time will not be added.

        Returns:
            pd.DataFrame: DataFrame with columns 'sku', 'quantity', and 'update_date'
        """
        try:
            items = self.fetch_all_items()

            # Extract relevant data
            inventory_data = []
            for item in items:
                data = {
                    'sku': item.get('sku', ''),
                    'quantity': item.get('quantity', 0)
                }

                # Add update date if provided
                if update_date:
                    data['update_date'] = update_date

                inventory_data.append(data)

            return pd.DataFrame(inventory_data)

        except Exception as e:
            raise Exception(f"Error processing inventory data: {e}")

    def validate_update_payload(self, payload: Dict[str, Any]) -> bool:
        """
        Validate the update payload for a BoxHero item

        Args:
            payload (Dict[str, Any]): The payload to validate

        Returns:
            bool: Whether the payload is valid
        """
        # Basic validation
        if not isinstance(payload, dict):
            self.logger.error(f"Payload is not a dictionary: {payload}")
            return False

        # Check required fields
        if "name" not in payload:
            self.logger.warning("Missing required field 'name' in payload")

        # Validate attrs structure
        if "attrs" in payload and not isinstance(payload["attrs"], dict):
            self.logger.error(f"'attrs' is not a dictionary: {payload['attrs']}")
            return False

        # All checks passed
        return True

    def update_item(self, item_id: int, update_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Update a single BoxHero item using the PUT /items/{item_id} endpoint

        Args:
            item_id (int): The ID of the item to update
            update_data (Dict[str, Any]): The data to update the item with

        Returns:
            Dict[str, Any]: The response from the API
        """
        try:
            # Validate the payload
            if not self.validate_update_payload(update_data):
                raise ValueError(f"Invalid update payload for item {item_id}")

            # Log the payload if debug mode is enabled
            if self.debug:
                self.logger.debug(f"Updating item {item_id} with payload: {json.dumps(update_data)}")

            # Make the request
            response = requests.put(
                f'{self.base_url}/items/{item_id}',
                headers=self.headers,
                json=update_data
            )

            # Check for error responses
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = f". Response: {response.json()}"
                except:
                    error_detail = f". Response text: {response.text}"

                raise requests.exceptions.HTTPError(
                    f"API error {response.status_code}{error_detail}"
                )

            # Return the successful response
            return response.json()

        except requests.exceptions.RequestException as e:
            # Get the full error details
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
                raise Exception(f"Error updating item {item_id} in BoxHero API: {e}. Details: {error_detail}")
            else:
                raise Exception(f"Error updating item {item_id} in BoxHero API: {e}")

    def delete_item(self, item_id: int) -> bool:
        """
        Delete a single BoxHero item using the DELETE /items/{item_id} endpoint

        Args:
            item_id (int): The ID of the item to delete

        Returns:
            bool: Whether the deletion was successful
        """
        try:
            # Log the operation if debug mode is enabled
            if self.debug:
                self.logger.debug(f"Deleting item with ID: {item_id}")

            # Make the request
            response = requests.delete(
                f'{self.base_url}/items/{item_id}',
                headers=self.headers
            )

            # Check for error responses
            if response.status_code != 200:
                error_detail = ""
                try:
                    error_detail = f". Response: {response.json()}"
                except:
                    error_detail = f". Response text: {response.text}"

                raise requests.exceptions.HTTPError(
                    f"API error {response.status_code}{error_detail}"
                )

            # Return success
            return True

        except requests.exceptions.RequestException as e:
            # Get the full error details
            if hasattr(e, 'response') and e.response is not None:
                try:
                    error_detail = e.response.json()
                except:
                    error_detail = e.response.text
                self.logger.error(f"Error deleting item {item_id} in BoxHero API: {e}. Details: {error_detail}")
            else:
                self.logger.error(f"Error deleting item {item_id} in BoxHero API: {e}")

            return False

    def update_items_from_df(self, products_df: pd.DataFrame,
                             progress_callback=None) -> Dict[str, Any]:
        """
        Update multiple BoxHero items based on data from a DataFrame

        Args:
            products_df (pd.DataFrame): DataFrame containing product data
            progress_callback (callable, optional): Callback function to update progress

        Returns:
            Dict[str, Any]: Statistics about the update operation
        """
        # Get current inventory from BoxHero to compare/update
        current_items = self.fetch_all_items()

        if self.debug:
            # Print the first item structure to understand the data format
            if current_items:
                self.logger.debug(f"Sample BoxHero item structure: {json.dumps(current_items[0])}")

        # Create a dictionary of items by SKU for faster lookup
        item_dict = {item.get('sku', ''): item for item in current_items}

        # Track statistics
        items_updated = 0
        items_skipped = 0
        errors = []

        # Process each product in the dataframe
        total_items = len(products_df)

        # Get a sample row for debugging
        if not products_df.empty and self.debug:
            sample_row = products_df.iloc[0].to_dict()
            self.logger.debug(f"Sample Google Sheet row: {json.dumps(sample_row)}")

        for index, row in products_df.iterrows():
            try:
                # Update progress if callback provided
                if progress_callback:
                    progress = (index + 1) / total_items
                    progress_callback(progress)

                # Get the item_id from "Part No." column
                part_no = str(row.get('SKU', ''))

                if not part_no:
                    items_skipped += 1
                    continue

                # Find the item in BoxHero items
                if part_no not in item_dict:
                    errors.append(f"Item with Part No. {part_no} not found in BoxHero")
                    items_skipped += 1
                    continue

                # Get the BoxHero item_id
                item_id = item_dict[part_no].get('id')

                if not item_id:
                    errors.append(f"No valid item ID found for Part No. {part_no}")
                    items_skipped += 1
                    continue

                # Convert types appropriately - ensure numbers are sent as numbers, not strings
                # For ROP (764397) and MAX (764396), set to 0 if empty or None
                rop = row.get('ROP')
                max_val = row.get('MAX')
                conversion_rate = row.get('Conversion Rate')

                # Convert numeric values properly - defaulting to 0 for empty/null ROP and MAX
                try:
                    if rop not in (None, ''):
                        rop = float(rop) if '.' in str(rop) else int(rop)
                    else:
                        rop = 0  # Default to 0 for empty ROP values
                except (ValueError, TypeError):
                    rop = 0  # Default to 0 if conversion fails

                try:
                    if max_val not in (None, ''):
                        max_val = float(max_val) if '.' in str(max_val) else int(max_val)
                    else:
                        max_val = 0  # Default to 0 for empty MAX values
                except (ValueError, TypeError):
                    max_val = 0  # Default to 0 if conversion fails

                try:
                    if conversion_rate not in (None, ''):
                        conversion_rate = float(conversion_rate) if '.' in str(conversion_rate) else int(conversion_rate)
                    else:
                        conversion_rate = 0  # Default to 0 for empty Conversion Rate values
                except (ValueError, TypeError):
                    conversion_rate = 0  # Default to 0 if conversion fails

                # Prepare the update payload
                update_payload = {
                    "name": row.get('Name', ''),
                    "barcode": row.get('Barcode', ''),
                    "attrs": {
                        "764400": row.get('Supplier'),
                        "764394": row.get('UOM'),
                        "764397": rop,  # ROP (never null, defaults to 0)
                        "764396": max_val,  # MAX (never null, defaults to 0)
                        "768129": row.get('List'),
                        "769262": conversion_rate  # Conversion Rate (never null, defaults to 0)
                    }
                }

                # Clean the payload - remove None values and empty strings for non-numeric fields only
                attrs = update_payload["attrs"]
                for key in list(attrs.keys()):
                    # Only clean non-numeric fields (those other than 764397, 764396, 769262)
                    if key not in ["764397", "764396", "769262"] and attrs[key] in (None, ''):
                        attrs[key] = None

                # Update the item
                self.update_item(item_id, update_payload)
                items_updated += 1

            except Exception as e:
                error_msg = f"Error processing item {part_no if 'part_no' in locals() else 'unknown'}: {str(e)}"
                errors.append(error_msg)
                self.logger.error(error_msg)

        # Return statistics
        return {
            "items_updated": items_updated,
            "items_skipped": items_skipped,
            "errors": errors
        }

    def clean_up_items(self, reference_skus: List[str],
                       progress_callback=None,
                       dry_run=False) -> Dict[str, Any]:
        """
        Delete items in BoxHero that are not in the reference SKU list

        Args:
            reference_skus (List[str]): List of SKUs that should be kept
            progress_callback (callable, optional): Callback function to update progress
            dry_run (bool): If True, only simulate deletions without actually deleting

        Returns:
            Dict[str, Any]: Statistics about the cleanup operation
        """
        try:
            # Get all items from BoxHero
            current_items = self.fetch_all_items()

            if not current_items:
                return {
                    "items_to_delete": 0,
                    "items_deleted": 0,
                    "skipped": 0,
                    "errors": ["No items found in BoxHero"]
                }

            # Convert reference SKUs to a set for faster lookups
            reference_sku_set = set(reference_skus)

            # Find items to delete
            items_to_delete = []
            for item in current_items:
                item_sku = item.get('sku', '')
                if item_sku and item_sku not in reference_sku_set:
                    items_to_delete.append(item)

            # Track statistics
            total_to_delete = len(items_to_delete)
            items_deleted = 0
            skipped = 0
            errors = []

            # Process deletions
            for index, item in enumerate(items_to_delete):
                try:
                    # Update progress if callback provided
                    if progress_callback:
                        progress = (index + 1) / total_to_delete if total_to_delete > 0 else 1.0
                        progress_callback(progress)

                    item_id = item.get('id')
                    item_sku = item.get('sku', '')
                    item_name = item.get('name', 'Unknown')

                    if not item_id:
                        errors.append(f"Missing item ID for SKU: {item_sku}")
                        skipped += 1
                        continue

                    # Log the deletion attempt
                    self.logger.info(f"{'Would delete' if dry_run else 'Deleting'} item: {item_name} (SKU: {item_sku}, ID: {item_id})")

                    # Perform the deletion unless this is a dry run
                    if not dry_run:
                        success = self.delete_item(item_id)
                        if success:
                            items_deleted += 1
                        else:
                            errors.append(f"Failed to delete item: {item_name} (SKU: {item_sku}, ID: {item_id})")
                            skipped += 1
                    else:
                        # In dry run mode, count as deleted for statistics
                        items_deleted += 1

                except Exception as e:
                    error_msg = f"Error processing deletion for item {item.get('sku', '')}: {str(e)}"
                    errors.append(error_msg)
                    self.logger.error(error_msg)
                    skipped += 1

            # Return statistics
            return {
                "items_to_delete": total_to_delete,
                "items_deleted": items_deleted,
                "skipped": skipped,
                "errors": errors,
                "dry_run": dry_run
            }

        except Exception as e:
            return {
                "items_to_delete": 0,
                "items_deleted": 0,
                "skipped": 0,
                "errors": [f"Error during cleanup: {str(e)}"],
                "dry_run": dry_run
            }