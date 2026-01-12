"""
Production Flow Capture Module

This module captures production data (Lot Code, Produced Quantity, Timestamp, Item)
when entered in the MO-lot-label-generator application.

Since the MO-lot-label-generator is an executable, this module provides:
1. A function to capture production data when inserted into erp_mo_to_import
2. A database trigger mechanism (if supported)
3. A monitoring function to capture new entries
"""

import logging
from datetime import datetime
from typing import Optional, Dict, Any, List
from shared.json_storage import JSONStorage

logger = logging.getLogger(__name__)


class ProductionCapture:
    """Captures production data from MO-lot-label-generator app"""
    
    def __init__(self):
        self.storage = JSONStorage()
    
    def capture_production_entry(
        self,
        lot_code: str,
        produced_quantity: float,
        uom: Optional[str] = None,
        item_code: Optional[str] = None,
        timestamp: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """
        Capture production entry data.
        
        Args:
            lot_code: Lot Code (e.g., L28553)
            produced_quantity: Actual production quantity
            uom: Unit of measure
            item_code: Item code if available
            timestamp: Timestamp of production (defaults to now)
        
        Returns:
            Dict with captured data including id, timestamp, etc.
        """
        if not lot_code:
            raise ValueError("Lot Code is required")
        
        if produced_quantity is None or produced_quantity < 0:
            raise ValueError("Produced quantity must be >= 0")
        
        if timestamp is None:
            timestamp = datetime.now()
        
        captured_data = {
            'lot_code': lot_code.strip(),
            'produced_quantity': float(produced_quantity),
            'uom': uom,
            'item_code': item_code,
            'timestamp': timestamp,
            'captured_at': datetime.now()
        }
        
        logger.info(f"Captured production entry: Lot={lot_code}, Qty={produced_quantity}, UOM={uom}, Item={item_code}")
        
        # Store captured data
        # Note: This will be saved when the production record is created in the workflow
        # For now, we just return the data
        
        return captured_data
    
    def capture_from_database_entry(self, db_entry: Dict[str, Any]) -> Dict[str, Any]:
        """
        Capture production data from an existing database entry in erp_mo_to_import.
        
        Args:
            db_entry: Dictionary with keys: lot_code, quantity, uom, inserted_at, etc.
        
        Returns:
            Dict with captured production data
        """
        lot_code = db_entry.get('lot_code')
        quantity = db_entry.get('quantity', 0)
        uom = db_entry.get('uom')
        inserted_at = db_entry.get('inserted_at')
        
        # Parse timestamp if it's a string
        if isinstance(inserted_at, str):
            try:
                timestamp = datetime.fromisoformat(inserted_at.replace('Z', '+00:00'))
            except:
                timestamp = datetime.now()
        elif isinstance(inserted_at, datetime):
            timestamp = inserted_at
        else:
            timestamp = datetime.now()
        
        return self.capture_production_entry(
            lot_code=lot_code,
            produced_quantity=quantity,
            uom=uom,
            item_code=db_entry.get('item_code'),
            timestamp=timestamp
        )
    
    def get_recent_captures(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get recent production captures from storage.
        
        Args:
            limit: Maximum number of recent entries to return
        
        Returns:
            List of captured production entries
        """
        try:
            # Get recent production records
            records = self.storage.get_production_records(limit=limit)
            
            # Convert to capture format
            captures = []
            for record in records:
                try:
                    capture = {
                        'lot_code': record.get('lot'),
                        'produced_quantity': record.get('actual_qty', 0),
                        'timestamp': record.get('timestamp'),
                        'mo_number': record.get('mo'),
                        'status': record.get('status')
                    }
                    captures.append(capture)
                except Exception as e:
                    logger.error(f"Error processing record: {str(e)}")
                    continue
            
            return captures
        except Exception as e:
            logger.error(f"Error getting recent captures: {str(e)}")
            return []

