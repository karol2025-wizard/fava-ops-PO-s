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
    
    # MRPeasy manufacturing order status codes (from MRPEasy API docs)
    STATUS_DONE = 40       # Done
    STATUS_SHIPPED = 50    # Shipped
    STATUS_CLOSED = 60     # Closed
    STATUS_IN_PROGRESS = 30  # In progress
    STATUS_SCHEDULED = 20    # Scheduled
    STATUS_NOT_SCHEDULED = 15  # Not Scheduled
    STATUS_NEW = 10         # New
    
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
            target_lots = current_mo.get('target_lots', []) or []
            lot_code_found = False
            if target_lots:
                for lot in target_lots:
                    if (lot.get('code') or '').strip().upper() == lot_code.strip().upper():
                        lot_code_found = True
                        break
                if not lot_code_found:
                    logger.warning(
                        f"Lot code {lot_code} does not match any target lot in MO {mo_id}. "
                        f"Target lots: {[l.get('code') for l in target_lots]}"
                    )
            
            # PRIMARY: Update the stock lot quantity (this is what MRPEasy shows on the MO row)
            lot_id = None
            for lot in target_lots:
                if (lot.get('code') or '').strip().upper() == lot_code.strip().upper():
                    lot_id = (
                        lot.get('lot_id') or lot.get('id')
                        or lot.get('lotId')  # camelCase
                        or lot.get('stock_lot_id')
                    )
                    break
            if not lot_id:
                # Fallback: get lot by code from API (MO target_lots may use different key names)
                lot_by_code = self.api.get_single_lot(lot_code.strip())
                if not lot_by_code and lot_code.strip().upper().startswith("L"):
                    lot_by_code = self.api.get_single_lot(lot_code.strip()[1:])  # try without L
                if lot_by_code:
                    lot_id = (
                        lot_by_code.get('lot_id') or lot_by_code.get('id')
                        or lot_by_code.get('lotId') or lot_by_code.get('stock_lot_id')
                    )
                if not lot_id:
                    logger.warning(
                        f"Could not resolve lot_id for lot {lot_code}. "
                        f"target_lots keys sample: {list(target_lots[0].keys()) if target_lots else 'no target_lots'}."
                    )
            
            lot_update_success = False
            if lot_id:
                try:
                    lot_id_int = int(lot_id)
                    logger.info(f"Updating lot {lot_id_int} ({lot_code}) with quantity {actual_quantity}")
                    lot_response = self.api.update_stock_lot_quantity(lot_id_int, actual_quantity)
                    if lot_response and lot_response.status_code in [200, 202, 204]:
                        lot_update_success = True
                        logger.info(f"Lot {lot_code} updated with quantity {actual_quantity}")
                    else:
                        logger.warning(
                            f"Lot update returned {getattr(lot_response, 'status_code', None)}: {getattr(lot_response, 'text', '')}"
                        )
                except (ValueError, RuntimeError) as e:
                    logger.warning(f"Lot update failed: {e}", exc_info=True)
                except Exception as e:
                    logger.warning(f"Lot update failed: {e}", exc_info=True)
            
            if not lot_update_success and not lot_id:
                logger.warning("No lot_id available; only MO update will be attempted (may not change quantity in UI).")
            
            # SECONDARY: Update MO with quantity only (API rejects if we send status in same request)
            response = self.api.update_manufacturing_order(
                mo_id=mo_id,
                actual_quantity=actual_quantity,
                status=None,  # do not send; we try status in a separate request below
                lot_code=lot_code
            )
            
            # TERTIARY: Try to set status to Done (40). If MO is in 15 (Not Scheduled), try transition 15→20→30→40 first.
            status_set_done = False
            try:
                current_status = current_mo.get('status')
                current_status_int = int(current_status) if current_status is not None else None
                if current_status_int == self.STATUS_NOT_SCHEDULED:  # 15
                    status_set_done, _ = self.api.try_set_mo_status_transition_15_to_40(mo_id)
                else:
                    status_set_done, _ = self.api.try_set_mo_status_done(mo_id, self.STATUS_DONE)
            except Exception:
                pass
            
            # Check if update was successful (200 OK, 202 Accepted, 204 No Content)
            status_rejected_by_api = (
                response.status_code == 400
                and "Status cannot be changed" in (response.text or "")
            )
            if response.status_code not in [200, 202, 204] and not status_rejected_by_api:
                error_msg = (
                    f"Failed to update MO {mo_id}. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                logger.error(error_msg)
                return False, None, error_msg
            if status_rejected_by_api:
                logger.warning(
                    f"MO {mo_id}: status 40 (Done) cannot be changed via API. "
                    f"Lot {lot_code} update attempted; change status to Done manually in MRPeasy."
                )
            
            # Fetch updated MO details (after optional status=Done PUT)
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
                'status': updated_mo.get('status', self.STATUS_DONE),
                'lot_code': lot_code,
                'updated_at': updated_mo.get('updated_at') or updated_mo.get('modified_at'),
                'status_set_done': status_set_done,
            }
            
            # Consider closed when we set status to Done via API, or when quantity was updated (legacy message)
            if not status_set_done:
                logger.info(f"MO {mo_id} quantity updated; status could not be set to Done via API.")
            close_success, close_message, playwright_error, playwright_closed = self.close_manufacturing_order(
                mo_id,
                lot_code=lot_code,
                actual_quantity=actual_quantity,
                mo_number=updated_data.get('mo_number'),
            )
            if playwright_error:
                updated_data['playwright_error'] = playwright_error
            updated_data['playwright_closed'] = playwright_closed
            
            # Consider success if HTTP 2xx, or if 400 was only due to "Status cannot be changed" (quantity may still be updated)
            status_ok = response.status_code in [200, 202, 204] or status_rejected_by_api
            if not status_ok:
                error_msg = (
                    f"Failed to update MO {mo_id} with actual quantity. "
                    f"Status: {response.status_code}, Response: {response.text}"
                )
                logger.error(error_msg)
                return False, None, error_msg
            
            status_note = (
                " Estado actualizado a Done." if status_set_done else
                " Marca el MO como Done manualmente en MRPEasy (la API no permite cambiar el estado)."
            )
            
            # Build success message (lot update is what makes quantity appear in MRPEasy)
            if lot_update_success:
                success_msg = (
                    f"Lot {lot_code} y MO {updated_data['mo_number']} actualizados con cantidad {actual_quantity}. "
                    f"Revisa en MRPEasy que la cantidad se vea correcta."
                    f"{status_note}"
                )
            else:
                success_msg = (
                    f"MO {updated_data['mo_number']} registrado con cantidad {actual_quantity} para LOT {lot_code}. "
                    f"Si la cantidad no se actualizó en MRPEasy, la API puede no permitir actualizar el lote: "
                    f"introduce la cantidad manualmente en el MO o en el lote {lot_code} en MRPEasy."
                    f"{status_note}"
                )
            logger.info(success_msg)
            return True, updated_data, success_msg
            
        except Exception as e:
            error_msg = f"Error updating MO {mo_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, None, error_msg
    
    def close_manufacturing_order(
        self,
        mo_id: int,
        lot_code: Optional[str] = None,
        actual_quantity: Optional[float] = None,
        mo_number: Optional[str] = None,
    ) -> Tuple[bool, str, Optional[str], bool]:
        """
        Consider a Manufacturing Order "closed" after actual_quantity was set.
        If Playwright is enabled in secrets and API did not set Done, tries to close via browser.

        Returns:
            Tuple of (success, message, playwright_error or None, playwright_closed: bool)
        """
        if not mo_id:
            logger.error("Manufacturing Order ID is required")
            return False, "Manufacturing Order ID is required", None, False

        playwright_error: Optional[str] = None
        playwright_closed = False
        try:
            current_mo = self.api.get_manufacturing_order_details(mo_id)
            if not current_mo:
                return False, f"Manufacturing Order {mo_id} not found", None, False

            mo_code = mo_number or current_mo.get('code', str(mo_id))

            # Intentar cierre por Playwright si está habilitado y tenemos lot y cantidad
            enabled = False
            try:
                import streamlit as st
                if hasattr(st, "secrets") and st.secrets:
                    enabled = bool(st.secrets.get("mrpeasy_playwright_enabled", False))
            except Exception:
                pass

            if enabled and lot_code and actual_quantity is not None:
                try:
                    from shared.mrpeasy_playwright_close import close_mo_via_playwright
                    success, msg = close_mo_via_playwright(
                        mo_id=mo_id,
                        lot_code=lot_code,
                        quantity=actual_quantity,
                        mo_number=mo_code,
                    )
                    if success:
                        logger.info("Playwright cerró el MO: %s", msg)
                        return True, msg, None, True
                    playwright_error = msg
                    logger.warning("Playwright no cerró el MO: %s", msg)
                except Exception as e:
                    playwright_error = str(e)
                    logger.warning("Playwright no cerró el MO: %s", e)

            success_msg = (
                f"Manufacturing Order {mo_code} updated with actual quantity. "
                "(Status cannot be changed via API; update in MRPeasy UI if needed.)"
            )
            logger.info(success_msg)
            return True, success_msg, playwright_error, playwright_closed
        except Exception as e:
            error_msg = f"Error closing MO {mo_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg, None, False
