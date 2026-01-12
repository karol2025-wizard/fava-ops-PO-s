"""
Production Workflow Integration Module

This module integrates all production workflow components:
1. Production Capture (Task 2)
2. MO Lookup (Task 3)
3. MO Update (Task 4)
4. Summary & Print (Task 5)
5. Logging & Safety (Task 6)

This provides a complete workflow for processing production completions.
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, Tuple
from shared.production_capture import ProductionCapture
from shared.mo_lookup import MOLookup
from shared.mo_update import MOUpdate
from shared.production_summary import ProductionSummary
from shared.production_logging import ProductionLogger, RetryHandler
from shared.json_storage import JSONStorage

logger = logging.getLogger(__name__)


class ProductionWorkflow:
    """Complete production workflow integration"""
    
    def __init__(self):
        self.capture = ProductionCapture()
        self.lookup = MOLookup()
        self.update = MOUpdate()
        self.summary = ProductionSummary()
        self.logger = ProductionLogger()
        self.storage = JSONStorage()
        self.retry_handler = RetryHandler(max_retries=3, initial_delay=1.0)
    
    def process_production_completion(
        self,
        lot_code: str,
        produced_quantity: float,
        uom: Optional[str] = None,
        item_code: Optional[str] = None
    ) -> Tuple[bool, Optional[Dict[str, Any]], str]:
        """
        Complete workflow for processing production completion.
        
        This method:
        1. Captures production data
        2. Looks up MO by lot code
        3. Updates MO with actual quantity and status
        4. Generates summary
        5. Logs the operation
        
        Args:
            lot_code: Lot Code (e.g., L28553)
            produced_quantity: Actual produced quantity
            uom: Unit of measure (optional)
            item_code: Item code if available (optional)
        
        Returns:
            Tuple of (success, result_data, message)
            - success: True if entire workflow succeeded
            - result_data: Dict with complete workflow results including summary PDF
            - message: Success or error message
        """
        workflow_start = datetime.now()
        
        try:
            # Step 1: Capture production data
            logger.info(f"Step 1: Capturing production data for lot {lot_code}")
            captured_data = self.capture.capture_production_entry(
                lot_code=lot_code,
                produced_quantity=produced_quantity,
                uom=uom,
                item_code=item_code,
                timestamp=workflow_start
            )
            
            # Step 2: Lookup MO by lot code (with retry)
            logger.info(f"Step 2: Looking up MO for lot {lot_code}")
            lookup_success, mo_data, lookup_message = self.retry_handler.execute_with_retry(
                self.lookup.find_mo_by_lot_code,
                lot_code
            )
            
            if not lookup_success:
                error_msg = f"MO lookup failed: {lookup_message}"
                self.logger.log_production_update(
                    lot_code=lot_code,
                    mo_number="N/A",
                    mo_id=0,
                    quantity=produced_quantity,
                    success=False,
                    error_message=error_msg
                )
                return False, None, error_msg
            
            mo_id = mo_data['mo_id']
            mo_number = mo_data['mo_number']
            status_before = mo_data.get('status')
            
            # Step 3: Update MO with actual quantity and status (with retry)
            logger.info(f"Step 3: Updating MO {mo_number} with production data")
            update_success, updated_mo_data, update_message = self.retry_handler.execute_with_retry(
                self.update.update_mo_with_production,
                mo_id=mo_id,
                actual_quantity=produced_quantity,
                lot_code=lot_code
            )
            
            if not update_success:
                error_msg = f"MO update failed: {update_message}"
                self.logger.log_production_update(
                    lot_code=lot_code,
                    mo_number=mo_number,
                    mo_id=mo_id,
                    quantity=produced_quantity,
                    status_before=status_before,
                    success=False,
                    error_message=error_msg
                )
                return False, None, error_msg
            
            status_after = updated_mo_data.get('status')
            
            # Step 4: Save production record
            logger.info(f"Step 4: Saving production record for MO {mo_number}")
            estimated_qty = updated_mo_data.get('expected_output', 0)
            self.storage.save_production_record(
                lot=lot_code,
                mo=mo_number,
                estimated_qty=estimated_qty,
                actual_qty=produced_quantity,
                status=updated_mo_data.get('status_name', 'Done')
            )
            
            # Step 4b: Log successful update
            logger.info(f"Step 4b: Logging production update for MO {mo_number}")
            self.logger.log_production_update(
                lot_code=lot_code,
                mo_number=mo_number,
                mo_id=mo_id,
                quantity=produced_quantity,
                status_before=status_before,
                status_after=status_after,
                success=True
            )
            
            # Step 5: Generate summary
            logger.info(f"Step 5: Generating production summary for MO {mo_number}")
            summary_data = self.summary.generate_summary_data(
                mo_number=mo_number,
                item_code=updated_mo_data.get('item_code', 'N/A'),
                item_title=updated_mo_data.get('item_title', 'N/A'),
                lot_code=lot_code,
                produced_quantity=produced_quantity,
                produced_unit=uom or updated_mo_data.get('expected_output_unit', ''),
                expected_output=updated_mo_data.get('expected_output'),
                expected_unit=updated_mo_data.get('expected_output_unit'),
                timestamp=workflow_start
            )
            
            # Generate PDF summary
            summary_pdf = self.summary.create_summary_pdf(summary_data)
            
            # Prepare result data
            result_data = {
                'captured_data': captured_data,
                'mo_lookup': mo_data,
                'mo_update': updated_mo_data,
                'summary_data': summary_data,
                'summary_pdf': summary_pdf,
                'workflow_timestamp': workflow_start.isoformat()
            }
            
            success_msg = (
                f"Production completion processed successfully. "
                f"MO {mo_number} updated with {produced_quantity} {uom or ''}. "
                f"Status changed to Done and order closed."
            )
            
            logger.info(f"Workflow completed successfully: {success_msg}")
            return True, result_data, success_msg
            
        except Exception as e:
            error_msg = f"Workflow error: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.logger.log_production_update(
                lot_code=lot_code,
                mo_number="N/A",
                mo_id=0,
                quantity=produced_quantity,
                success=False,
                error_message=error_msg
            )
            return False, None, error_msg

