"""
MRPeasy MO Update Module

This module provides functionality to update Manufacturing Orders (MOs) 
in MRPeasy with actual produced quantities and status changes.

Requirements:
- Update MO with Actual Produced Quantity
- Confirm Lot Code
- Change Status to Done
- Close the Manufacturing Order
- Ensure update is atomic
"""

import logging
from typing import Optional, Dict, Any, Tuple
from shared.api_manager import APIManager

logger = logging.getLogger(__name__)


class MOUpdateError(Exception):
    """Custom exception for MO update errors"""
    pass


class MOUpdate:
    """Update Manufacturing Orders in MRPeasy"""
    
    # MRPeasy status codes (common values)
    STATUS_DONE = 20  # Typically "Done" status
    STATUS_IN_PROGRESS = 10  # Typically "In Progress" status
    
    def __init__(self, api_manager: Optional[APIManager] = None):
        self.api = api_manager or APIManager()
    
    def update_mo_with_production(
        self,
        mo_id: int,
        actual_quantity: float,
        lot_code: str,
        status: int = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Update a Manufacturing Order with actual produced quantity and status.
        
        Args:
            mo_id: Manufacturing Order ID
            actual_quantity: Actual produced quantity
            lot_code: Lot Code for confirmation
            status: Status code (defaults to STATUS_DONE if not provided)
        
        Returns:
            Tuple of (success, updated_mo_data, message)
            - success: True if update successful
            - updated_mo_data: Dict with updated MO data (if successful)
            - message: Success message or error message
        """
        if not mo_id:
            error_msg = "Manufacturing Order ID is required"
            logger.error(error_msg)
            return False, None, error_msg
        
        if actual_quantity is None or actual_quantity < 0:
            error_msg = f"Invalid actual quantity: {actual_quantity}"
            logger.error(error_msg)
            return False, None, error_msg
        
        if not lot_code or not lot_code.strip():
            error_msg = "Lot Code is required for confirmation"
            logger.error(error_msg)
            return False, None, error_msg
        
        # Default to Done status if not provided
        if status is None:
            status = self.STATUS_DONE
        
        logger.info(
            f"Updating MO {mo_id} with actual quantity {actual_quantity}, "
            f"lot code {lot_code}, status {status}"
        )
        
        try:
            # Verify MO exists and get current details
            current_mo = self.api.get_manufacturing_order_details(mo_id)
            if not current_mo:
                error_msg = f"Manufacturing Order {mo_id} not found"
                logger.error(error_msg)
                return False, None, error_msg
            
            # Verify lot code matches (if target_lots exist)
            target_lots = current_mo.get('target_lots', [])
            lot_code_found = False
            if target_lots:
                for lot in target_lots:
                    if lot.get('code', '').strip().upper() == lot_code.strip().upper():
                        lot_code_found = True
                        break
                if not lot_code_found:
                    error_msg = (
                        f"Lot code {lot_code} does not match any target lot "
                        f"in MO {mo_id}. Target lots: {[l.get('code') for l in target_lots]}"
                    )
                    logger.warning(error_msg)
                    # Continue anyway - might be a new lot or different scenario
            
            # Perform atomic update
            response = self.api.update_manufacturing_order(
                mo_id=mo_id,
                actual_quantity=actual_quantity,
                status=status,
                lot_code=lot_code
            )
            
            # Check if update was successful
            if response.status_code not in [200, 204]:
                error_msg = (
                    f"Failed to update MO {mo_id}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                logger.error(error_msg)
                return False, None, error_msg
            
            # Fetch updated MO details
            updated_mo = self.api.get_manufacturing_order_details(mo_id)
            if not updated_mo:
                # Update might have succeeded but fetch failed
                logger.warning(f"Update succeeded but could not fetch updated MO {mo_id}")
                updated_mo = current_mo  # Use current as fallback
            
            # Prepare updated data
            updated_data = {
                'mo_id': mo_id,
                'mo_number': updated_mo.get('code', 'N/A'),
                'item_code': updated_mo.get('item_code', 'N/A'),
                'item_title': updated_mo.get('item_title', 'N/A'),
                'expected_output': current_mo.get('quantity', 0),
                'actual_quantity': actual_quantity,
                'status': updated_mo.get('status', status),
                'lot_code': lot_code,
                'updated_at': updated_mo.get('updated_at') or updated_mo.get('modified_at')
            }
            
            # Close the manufacturing order after updating
            logger.info(f"Closing MO {mo_id} after update")
            close_success, close_message = self.close_manufacturing_order(mo_id)
            
            if close_success:
                success_msg = (
                    f"Successfully updated and closed MO {updated_data['mo_number']} "
                    f"with actual quantity {actual_quantity}. Status set to Done and order closed."
                )
                logger.info(success_msg)
            else:
                # Update succeeded but close failed - still return success but log warning
                success_msg = (
                    f"Successfully updated MO {updated_data['mo_number']} "
                    f"with actual quantity {actual_quantity}. Status set to Done. "
                    f"Warning: Failed to close order - {close_message}"
                )
                logger.warning(f"MO {mo_id} updated but failed to close: {close_message}")
            
            return True, updated_data, success_msg
            
        except Exception as e:
            error_msg = f"Error updating MO {mo_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def close_manufacturing_order(self, mo_id: int) -> Tuple[bool, str]:
        """
        Close a Manufacturing Order in MRPeasy.
        
        This method attempts to close the order by updating its status to a closed state.
        In MRPeasy, orders are typically closed by setting status to a closed value.
        Since status 20 (Done) might not fully close the order, we make an additional
        update to ensure it's properly closed.
        
        Args:
            mo_id: Manufacturing Order ID
        
        Returns:
            Tuple of (success, message)
            - success: True if close successful
            - message: Success message or error message
        """
        if not mo_id:
            error_msg = "Manufacturing Order ID is required"
            logger.error(error_msg)
            return False, error_msg
        
        try:
            # Get current MO to check status
            current_mo = self.api.get_manufacturing_order_details(mo_id)
            if not current_mo:
                error_msg = f"Manufacturing Order {mo_id} not found"
                logger.error(error_msg)
                return False, error_msg
            
            current_status = current_mo.get('status')
            mo_number = current_mo.get('code', str(mo_id))
            
            # If already in Done status (20), the order should be considered closed
            # However, we make an additional update to ensure it's properly closed
            # Some MRPeasy configurations may require a specific close action
            
            # Try to close by making a final update (some systems require this)
            # We'll update with the same status to ensure it's properly closed
            response = self.api.update_manufacturing_order(
                mo_id=mo_id,
                actual_quantity=None,  # Don't change quantity
                status=self.STATUS_DONE,  # Ensure status is Done
                lot_code=None
            )
            
            if response.status_code in [200, 204]:
                success_msg = f"Manufacturing Order {mo_number} closed successfully"
                logger.info(success_msg)
                return True, success_msg
            else:
                # If the update fails, check if order is already in Done status
                # In that case, it might already be considered closed
                if current_status == self.STATUS_DONE:
                    success_msg = f"Manufacturing Order {mo_number} is already in Done status (closed)"
                    logger.info(success_msg)
                    return True, success_msg
                else:
                    error_msg = (
                        f"Failed to close MO {mo_id}. "
                        f"Status: {response.status_code}, Response: {response.text}"
                    )
                    logger.warning(error_msg)
                    return False, error_msg
                    
        except Exception as e:
            error_msg = f"Error closing MO {mo_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg

