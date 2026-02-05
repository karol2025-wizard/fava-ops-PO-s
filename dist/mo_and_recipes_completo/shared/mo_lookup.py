"""
MRPeasy MO Lookup Module

This module provides functionality to search for Manufacturing Orders (MOs) 
in MRPeasy using Lot Code.

Requirements:
- Expect exactly ONE matching MO
- Retrieve: MO Number, Item Code, Status, Expected Output
- Error handling: 0 matches → block and log error
- Error handling: >1 matches → block and alert supervisor
"""

import logging
from typing import Optional, Dict, Any, Tuple
from shared.api_manager import APIManager

logger = logging.getLogger(__name__)


class MOLookupError(Exception):
    """Custom exception for MO lookup errors"""
    pass


class MOLookup:
    """Lookup Manufacturing Orders by Lot Code"""
    
    def __init__(self, api_manager: Optional[APIManager] = None):
        self.api = api_manager or APIManager()
    
    def find_mo_by_lot_code(self, lot_code: str) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Search MRPeasy for a Manufacturing Order using Lot Code.
        
        Args:
            lot_code: Lot Code (e.g., L28553)
        
        Returns:
            Tuple of (success, mo_data, message)
            - success: True if exactly one MO found
            - mo_data: Dict with MO Number, Item Code, Status, Expected Output (if found)
            - message: Success message or error message
        
        Raises:
            MOLookupError: If 0 matches or >1 matches found
        """
        if not lot_code or not lot_code.strip():
            error_msg = "Lot Code is required"
            logger.error(error_msg)
            return False, None, error_msg
        
        lot_code = lot_code.strip()
        logger.info(f"Searching for MO with lot code: {lot_code}")
        
        try:
            # Fetch all manufacturing orders
            # Note: This could be optimized with a filter if MRPeasy API supports it
            # IMPORTANT: This fetches ALL manufacturing orders, which can be slow and hit rate limits
            try:
                all_mos = self.api.fetch_manufacturing_orders()
            except ValueError as ve:
                # Check if it's a rate limit error
                if "429" in str(ve) or "Rate limit" in str(ve) or "Too Many Requests" in str(ve):
                    error_msg = (
                        f"Rate limit exceeded. MRPeasy está limitando las solicitudes. "
                        f"Intenta nuevamente en unos minutos, o usa la búsqueda directa por código MO."
                    )
                else:
                    error_msg = f"Error connecting to MRPeasy API: {str(ve)}"
                logger.error(error_msg, exc_info=True)
                return False, None, error_msg
            except Exception as api_error:
                error_msg = f"Error connecting to MRPeasy API: {str(api_error)}"
                logger.error(error_msg, exc_info=True)
                return False, None, error_msg
            
            if all_mos is None:
                error_msg = "Failed to fetch manufacturing orders from MRPeasy. The API returned None. Check your API credentials and network connection."
                logger.error(error_msg)
                return False, None, error_msg
            
            if not isinstance(all_mos, list):
                error_msg = f"Unexpected response type from MRPeasy API. Expected list, got {type(all_mos)}"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Filter MOs that have the lot code in their target_lots
            matching_mos = []
            for mo in all_mos:
                target_lots = mo.get('target_lots', [])
                for lot in target_lots:
                    lot_code_in_mo = lot.get('code', '').strip()
                    if lot_code_in_mo.upper() == lot_code.upper():
                        matching_mos.append(mo)
                        break  # Found match, no need to check other lots in this MO
            
            # Error handling: 0 matches
            if len(matching_mos) == 0:
                error_msg = f"No Manufacturing Order found with lot code: {lot_code}"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Error handling: >1 matches
            if len(matching_mos) > 1:
                mo_numbers = [mo.get('code', 'N/A') for mo in matching_mos]
                error_msg = (
                    f"Multiple Manufacturing Orders found with lot code {lot_code}. "
                    f"Found {len(matching_mos)} MOs: {', '.join(mo_numbers)}. "
                    f"Supervisor intervention required."
                )
                logger.error(error_msg)
                return False, None, error_msg
            
            # Success: Exactly one match
            mo = matching_mos[0]
            
            # Extract required information
            mo_data = {
                'mo_number': mo.get('code', 'N/A'),
                'mo_id': mo.get('man_ord_id'),
                'item_code': mo.get('item_code', 'N/A'),
                'item_title': mo.get('item_title', 'N/A'),
                'status': mo.get('status', 'N/A'),
                'expected_output': mo.get('quantity', 0),
                'expected_output_unit': mo.get('unit', ''),
                'lot_code': lot_code
            }
            
            success_msg = (
                f"Found Manufacturing Order: {mo_data['mo_number']} "
                f"for Item: {mo_data['item_code']} "
                f"with Expected Output: {mo_data['expected_output']} {mo_data['expected_output_unit']}"
            )
            logger.info(success_msg)
            
            return True, mo_data, success_msg
            
        except Exception as e:
            error_msg = f"Error searching for MO with lot code {lot_code}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def get_mo_details(self, mo_id: int) -> Optional[Dict[str, Any]]:
        """
        Get full details for a Manufacturing Order by ID.
        
        Args:
            mo_id: Manufacturing Order ID
        
        Returns:
            Dict with full MO details, or None if not found
        """
        try:
            return self.api.get_manufacturing_order_details(mo_id)
        except Exception as e:
            logger.error(f"Error fetching MO details for ID {mo_id}: {str(e)}")
            return None

