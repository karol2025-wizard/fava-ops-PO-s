"""
Auto MO Processor Module

This module automatically processes Manufacturing Orders when production quantities
are entered in WeightLabelPrinter.spec. It monitors the erp_mo_to_import table
and automatically updates MOs from "not booked" (status 0) to "Done" (status 20).

When a quantity is entered for a LOT in WeightLabelPrinter.spec:
1. The system finds the associated MO using the LOT code
2. Updates the MO with the actual produced quantity
3. Changes status from "not booked" (0) to "Done" (20)
4. Closes the Manufacturing Order

Usage from WeightLabelPrinter.spec:
    from shared.auto_mo_processor import process_production_by_lot
    
    # When quantity is entered:
    success, message = process_production_by_lot(
        lot_code="L28553",
        quantity=100.5,
        uom="kg"
    )
"""

import logging
import time
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from shared.database_manager import DatabaseManager
from shared.production_workflow import ProductionWorkflow

logger = logging.getLogger(__name__)


class AutoMOProcessor:
    """Automatically process Manufacturing Orders when production quantities are entered"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.workflow = ProductionWorkflow()
        self.processed_ids = set()  # Track processed IDs to avoid duplicates
    
    def fetch_new_production_entries(self) -> List[Dict[str, Any]]:
        """
        Fetch new production entries from erp_mo_to_import that haven't been processed.
        
        Returns:
            List of dictionaries with production entry data
        """
        try:
            query = """
            SELECT id, lot_code, quantity, uom, user_operations, inserted_at, failed_code
            FROM erp_mo_to_import 
            WHERE processed_at IS NULL 
            AND (failed_code IS NULL OR failed_code = '')
            AND lot_code IS NOT NULL
            AND lot_code != ''
            AND quantity IS NOT NULL
            AND quantity > 0
            ORDER BY inserted_at ASC
            """
            results = self.db.fetch_all(query)
            return results if results else []
        except Exception as e:
            logger.error(f"Error fetching new production entries: {str(e)}")
            return []
    
    def process_production_entry(
        self, 
        entry: Dict[str, Any]
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a single production entry by updating the associated MO.
        
        Args:
            entry: Dictionary with production entry data (lot_code, quantity, uom, etc.)
        
        Returns:
            Tuple of (success, message)
        """
        entry_id = entry.get('id')
        lot_code = entry.get('lot_code', '').strip()
        quantity = entry.get('quantity', 0)
        uom = entry.get('uom')
        
        if not lot_code:
            error_msg = f"Entry {entry_id} has no lot_code"
            logger.error(error_msg)
            self._mark_as_failed(entry_id, error_msg)
            return False, error_msg
        
        if not quantity or quantity <= 0:
            error_msg = f"Entry {entry_id} has invalid quantity: {quantity}"
            logger.error(error_msg)
            self._mark_as_failed(entry_id, error_msg)
            return False, error_msg
        
        try:
            logger.info(
                f"Processing production entry {entry_id}: "
                f"LOT={lot_code}, Qty={quantity}, UOM={uom}"
            )
            
            # Use ProductionWorkflow to process the completion
            success, result_data, message = self.workflow.process_production_completion(
                lot_code=lot_code,
                produced_quantity=float(quantity),
                uom=uom,
                item_code=None
            )
            
            if success:
                # Mark entry as processed
                self._mark_as_processed(entry_id)
                success_msg = (
                    f"Successfully processed entry {entry_id} for LOT {lot_code}. "
                    f"Lot updated with quantity {quantity}. "
                    f"(Si el MO sigue «Not booked», marca como Done/Received manualmente en MRPeasy.)"
                )
                logger.info(success_msg)
                return True, success_msg
            else:
                # Mark as failed with error message
                self._mark_as_failed(entry_id, message)
                error_msg = f"Failed to process entry {entry_id}: {message}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error processing entry {entry_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self._mark_as_failed(entry_id, error_msg)
            return False, error_msg
    
    def _mark_as_processed(self, entry_id: int):
        """Mark an entry as processed by setting processed_at timestamp"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = """
            UPDATE erp_mo_to_import 
            SET processed_at = %s 
            WHERE id = %s
            """
            self.db.execute_query(query, (current_time, entry_id))
            logger.debug(f"Marked entry {entry_id} as processed")
        except Exception as e:
            logger.error(f"Error marking entry {entry_id} as processed: {str(e)}")
    
    def _mark_as_failed(self, entry_id: int, error_message: str):
        """Mark an entry as failed by setting failed_code"""
        try:
            # Truncate error message if too long (database constraint)
            max_length = 500
            if len(error_message) > max_length:
                error_message = error_message[:max_length-3] + "..."
            
            query = """
            UPDATE erp_mo_to_import 
            SET failed_code = %s 
            WHERE id = %s
            """
            self.db.execute_query(query, (error_message, entry_id))
            logger.debug(f"Marked entry {entry_id} as failed: {error_message}")
        except Exception as e:
            logger.error(f"Error marking entry {entry_id} as failed: {str(e)}")
    
    def process_all_pending(self) -> Dict[str, Any]:
        """
        Process all pending production entries.
        
        Returns:
            Dictionary with processing results
        """
        entries = self.fetch_new_production_entries()
        
        if not entries:
            return {
                'total': 0,
                'processed': 0,
                'failed': 0,
                'results': []
            }
        
        results = {
            'total': len(entries),
            'processed': 0,
            'failed': 0,
            'results': []
        }
        
        logger.info(f"Processing {len(entries)} pending production entries")
        
        for entry in entries:
            entry_id = entry.get('id')
            lot_code = entry.get('lot_code', 'N/A')
            
            # Skip if already processed in this session
            if entry_id in self.processed_ids:
                logger.debug(f"Skipping entry {entry_id} (already processed)")
                continue
            
            success, message = self.process_production_entry(entry)
            
            if success:
                results['processed'] += 1
            else:
                results['failed'] += 1
            
            results['results'].append({
                'id': entry_id,
                'lot_code': lot_code,
                'success': success,
                'message': message
            })
            
            self.processed_ids.add(entry_id)
        
        logger.info(
            f"Processing complete: {results['processed']} processed, "
            f"{results['failed']} failed out of {results['total']} total"
        )
        
        return results
    
    def process_single_entry_by_lot(
        self,
        lot_code: str,
        quantity: float,
        uom: Optional[str] = None
    ) -> Tuple[bool, Optional[str]]:
        """
        Process a single production entry by LOT code and quantity.
        This can be called directly when WeightLabelPrinter.spec enters a quantity.
        
        Args:
            lot_code: Lot code (e.g., L28553)
            quantity: Produced quantity
            uom: Unit of measure (optional)
        
        Returns:
            Tuple of (success, message)
        """
        if not lot_code or not lot_code.strip():
            error_msg = "Lot code is required"
            logger.error(error_msg)
            return False, error_msg
        
        if not quantity or quantity <= 0:
            error_msg = f"Invalid quantity: {quantity}"
            logger.error(error_msg)
            return False, error_msg
        
        try:
            logger.info(
                f"Processing production completion for LOT {lot_code} "
                f"with quantity {quantity} {uom or ''}"
            )
            
            # Use ProductionWorkflow to process the completion
            success, result_data, message = self.workflow.process_production_completion(
                lot_code=lot_code.strip(),
                produced_quantity=float(quantity),
                uom=uom,
                item_code=None
            )
            
            if success:
                success_msg = (
                    f"Successfully processed LOT {lot_code}. "
                    f"Lot updated with quantity {quantity}. "
                    f"(Si el MO sigue «Not booked», marca como Done/Received manualmente en MRPeasy.)"
                )
                logger.info(success_msg)
                return True, success_msg
            else:
                error_msg = f"Failed to process LOT {lot_code}: {message}"
                logger.error(error_msg)
                return False, error_msg
                
        except Exception as e:
            error_msg = f"Error processing LOT {lot_code}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return False, error_msg


# Convenience function for direct calls from WeightLabelPrinter.spec
def process_production_by_lot(
    lot_code: str,
    quantity: float,
    uom: Optional[str] = None
) -> Tuple[bool, str]:
    """
    Convenience function to process production completion by LOT code.
    This can be called directly from WeightLabelPrinter.spec when a quantity is entered.
    
    Args:
        lot_code: Lot code (e.g., L28553)
        quantity: Produced quantity
        uom: Unit of measure (optional)
    
    Returns:
        Tuple of (success, message)
    
    Example:
        >>> success, message = process_production_by_lot("L28553", 100.5, "kg")
        >>> if success:
        ...     print(f"MO updated: {message}")
        ... else:
        ...     print(f"Error: {message}")
    """
    processor = AutoMOProcessor()
    return processor.process_single_entry_by_lot(
        lot_code=lot_code,
        quantity=quantity,
        uom=uom
    )
