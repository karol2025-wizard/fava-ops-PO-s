"""
Auto-Process Production Entries

This script automatically processes production entries from WeightLabelPrinter.exe
and updates MRPeasy with actual quantities and status.

It monitors the erp_mo_to_import table for new entries and processes them automatically.
Can be run as:
1. A standalone script (one-time processing)
2. A continuous monitoring service
3. Called from WeightLabelPrinter.exe as an external process
"""

import sys
import os
import time
import logging
from datetime import datetime
from typing import List, Dict, Any, Tuple

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.database_manager import DatabaseManager
from shared.production_workflow import ProductionWorkflow

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('production_auto_process.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class AutoProductionProcessor:
    """Automatically process production entries from database"""
    
    def __init__(self):
        self.db = DatabaseManager()
        self.workflow = ProductionWorkflow()
        self.processed_count = 0
        self.failed_count = 0
    
    def fetch_pending_entries(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Fetch pending production entries from database"""
        try:
            query = """
            SELECT id, lot_code, quantity, uom, user_operations, inserted_at, failed_code
            FROM erp_mo_to_import 
            WHERE processed_at IS NULL AND (failed_code IS NULL OR failed_code = '')
            ORDER BY inserted_at ASC
            LIMIT %s
            """
            results = self.db.fetch_all(query, (limit,))
            return results if results else []
        except Exception as e:
            logger.error(f"Error fetching pending entries: {str(e)}")
            return []
    
    def mark_as_processed(self, entry_id: int) -> bool:
        """Mark an entry as processed"""
        try:
            current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
            query = """
            UPDATE erp_mo_to_import 
            SET processed_at = %s 
            WHERE id = %s AND processed_at IS NULL
            """
            rows_updated = self.db.execute_query(query, (current_time, entry_id))
            return rows_updated > 0
        except Exception as e:
            logger.error(f"Error marking entry {entry_id} as processed: {str(e)}")
            return False
    
    def mark_as_failed(self, lot_code: str, error_message: str) -> bool:
        """Mark an entry as failed"""
        try:
            query = """
            UPDATE erp_mo_to_import 
            SET failed_code = %s 
            WHERE lot_code = %s AND processed_at IS NULL
            """
            rows_updated = self.db.execute_query(query, (error_message[:255], lot_code))
            return rows_updated > 0
        except Exception as e:
            logger.error(f"Error marking entry {lot_code} as failed: {str(e)}")
            return False
    
    def process_entry(self, entry: Dict[str, Any]) -> Tuple[bool, str]:
        """
        Process a single production entry
        
        Returns:
            (success, message)
        """
        entry_id = entry['id']
        lot_code = entry['lot_code']
        quantity = float(entry['quantity'])
        uom = entry.get('uom')
        
        logger.info(f"Processing entry {entry_id}: Lot={lot_code}, Qty={quantity}, UOM={uom}")
        
        try:
            # Process using ProductionWorkflow
            success, result_data, message = self.workflow.process_production_completion(
                lot_code=lot_code,
                produced_quantity=quantity,
                uom=uom,
                item_code=None  # Will be retrieved from MO lookup
            )
            
            if success:
                # Mark as processed
                if self.mark_as_processed(entry_id):
                    logger.info(f"✅ Successfully processed {lot_code}: {message}")
                    self.processed_count += 1
                    return True, message
                else:
                    logger.warning(f"Processing succeeded but failed to mark {entry_id} as processed")
                    return True, message
            else:
                # Mark as failed
                self.mark_as_failed(lot_code, message)
                logger.error(f"❌ Failed to process {lot_code}: {message}")
                self.failed_count += 1
                return False, message
                
        except Exception as e:
            error_msg = f"Error processing entry {entry_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            self.mark_as_failed(lot_code, error_msg)
            self.failed_count += 1
            return False, error_msg
    
    def process_pending_entries(self, limit: int = 10) -> Dict[str, Any]:
        """
        Process all pending entries
        
        Returns:
            Dict with processing statistics
        """
        logger.info("=" * 60)
        logger.info("Starting automatic production processing...")
        logger.info("=" * 60)
        
        pending_entries = self.fetch_pending_entries(limit)
        
        if not pending_entries:
            logger.info("No pending entries to process")
            return {
                'total': 0,
                'processed': 0,
                'failed': 0
            }
        
        logger.info(f"Found {len(pending_entries)} pending entries")
        
        # Reset counters
        self.processed_count = 0
        self.failed_count = 0
        
        # Process each entry
        for entry in pending_entries:
            self.process_entry(entry)
            # Small delay to avoid overwhelming the API
            time.sleep(0.5)
        
        # Summary
        total = len(pending_entries)
        logger.info("=" * 60)
        logger.info(f"Processing complete: {self.processed_count} succeeded, {self.failed_count} failed out of {total} total")
        logger.info("=" * 60)
        
        return {
            'total': total,
            'processed': self.processed_count,
            'failed': self.failed_count
        }
    
    def run_continuous(self, check_interval: int = 30):
        """
        Run continuous monitoring mode
        
        Args:
            check_interval: Seconds between checks for new entries
        """
        logger.info("Starting continuous monitoring mode...")
        logger.info(f"Checking for new entries every {check_interval} seconds")
        logger.info("Press Ctrl+C to stop")
        
        try:
            while True:
                self.process_pending_entries(limit=50)  # Process up to 50 at a time
                time.sleep(check_interval)
        except KeyboardInterrupt:
            logger.info("Stopping continuous monitoring...")
        except Exception as e:
            logger.error(f"Error in continuous mode: {str(e)}", exc_info=True)


def main():
    """Main entry point"""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Auto-process production entries from WeightLabelPrinter.exe'
    )
    parser.add_argument(
        '--mode',
        choices=['once', 'continuous'],
        default='once',
        help='Processing mode: once (process and exit) or continuous (monitor and process)'
    )
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Maximum number of entries to process per run (default: 10)'
    )
    parser.add_argument(
        '--interval',
        type=int,
        default=30,
        help='Seconds between checks in continuous mode (default: 30)'
    )
    
    args = parser.parse_args()
    
    processor = AutoProductionProcessor()
    
    if args.mode == 'continuous':
        processor.run_continuous(check_interval=args.interval)
    else:
        result = processor.process_pending_entries(limit=args.limit)
        print(f"\nResults: {result['processed']} processed, {result['failed']} failed out of {result['total']} total")


if __name__ == "__main__":
    main()

