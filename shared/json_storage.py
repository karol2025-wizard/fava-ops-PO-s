"""
JSON-based Storage Manager

This module provides file-based persistence using JSON files.
Replaces MySQL dependency with local file storage.

Storage Structure:
- data/
  - production/
    - records.json (production records: lot, mo, quantities, status)
    - logs.json (production logs)
  - clover/
    - orders.json (Clover orders for analytics)
    - orders_items.json (order items)
"""

import json
import os
from datetime import datetime
from typing import List, Dict, Any, Optional
from pathlib import Path
import logging

logger = logging.getLogger(__name__)


class JSONStorage:
    """JSON-based file storage manager"""
    
    def __init__(self, data_dir: str = "data"):
        """
        Initialize JSON storage manager.
        
        Args:
            data_dir: Base directory for storing data files
        """
        self.data_dir = Path(data_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        (self.data_dir / "production").mkdir(parents=True, exist_ok=True)
        (self.data_dir / "clover").mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, category: str, filename: str) -> Path:
        """Get full path to a data file"""
        return self.data_dir / category / filename
    
    def _read_json(self, filepath: Path, default: Any = None) -> Any:
        """Read JSON file, return default if file doesn't exist"""
        try:
            if filepath.exists():
                with open(filepath, 'r', encoding='utf-8') as f:
                    return json.load(f)
            return default if default is not None else []
        except Exception as e:
            logger.error(f"Error reading {filepath}: {e}")
            return default if default is not None else []
    
    def _write_json(self, filepath: Path, data: Any):
        """Write data to JSON file"""
        try:
            # Create directory if it doesn't exist
            filepath.parent.mkdir(parents=True, exist_ok=True)
            
            # Write with atomic operation (write to temp file first, then rename)
            temp_file = filepath.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            
            # Atomic rename
            temp_file.replace(filepath)
        except Exception as e:
            logger.error(f"Error writing {filepath}: {e}")
            raise
    
    # Production Records Methods
    
    def save_production_record(
        self,
        lot: str,
        mo: str,
        estimated_qty: float,
        actual_qty: float,
        status: str,
        timestamp: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a production record.
        
        Args:
            lot: Lot code (e.g., "L28553")
            mo: Manufacturing order code (e.g., "MO06621")
            estimated_qty: Estimated quantity
            actual_qty: Actual quantity produced
            status: Status (e.g., "Done")
            timestamp: ISO format timestamp (defaults to now)
        
        Returns:
            The saved record as a dictionary
        """
        if timestamp is None:
            timestamp = datetime.now().strftime("%Y-%m-%dT%H:%M")
        
        record = {
            "timestamp": timestamp,
            "lot": lot,
            "mo": mo,
            "estimated_qty": estimated_qty,
            "actual_qty": actual_qty,
            "status": status
        }
        
        filepath = self._get_file_path("production", "records.json")
        records = self._read_json(filepath, [])
        
        # Add record
        records.append(record)
        
        # Save
        self._write_json(filepath, records)
        
        logger.info(f"Saved production record: lot={lot}, mo={mo}, actual_qty={actual_qty}")
        return record
    
    def get_production_records(
        self,
        lot: Optional[str] = None,
        mo: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Get production records, optionally filtered by lot or mo.
        
        Args:
            lot: Filter by lot code
            mo: Filter by manufacturing order
            limit: Maximum number of records to return
        
        Returns:
            List of production records
        """
        filepath = self._get_file_path("production", "records.json")
        records = self._read_json(filepath, [])
        
        # Filter if needed
        if lot:
            records = [r for r in records if r.get("lot") == lot]
        if mo:
            records = [r for r in records if r.get("mo") == mo]
        
        # Sort by timestamp (newest first)
        records.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit if specified
        if limit:
            records = records[:limit]
        
        return records
    
    def save_production_log(
        self,
        lot_code: str,
        mo_number: str,
        mo_id: int,
        quantity: float,
        status_before: Optional[int] = None,
        status_after: Optional[int] = None,
        success: bool = True,
        error_message: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Save a production log entry.
        
        Args:
            lot_code: Lot code
            mo_number: Manufacturing order number
            mo_id: Manufacturing order ID
            quantity: Quantity produced
            status_before: Status before update
            status_after: Status after update
            success: Whether operation was successful
            error_message: Error message if failed
        
        Returns:
            The saved log entry
        """
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "lot_code": lot_code,
            "mo_number": mo_number,
            "mo_id": mo_id,
            "quantity": quantity,
            "status_before": status_before,
            "status_after": status_after,
            "success": success,
            "error_message": error_message
        }
        
        filepath = self._get_file_path("production", "logs.json")
        logs = self._read_json(filepath, [])
        
        logs.append(log_entry)
        self._write_json(filepath, logs)
        
        return log_entry
    
    def get_production_logs(
        self,
        lot_code: Optional[str] = None,
        mo_number: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get production logs, optionally filtered"""
        filepath = self._get_file_path("production", "logs.json")
        logs = self._read_json(filepath, [])
        
        # Filter if needed
        if lot_code:
            logs = [l for l in logs if l.get("lot_code") == lot_code]
        if mo_number:
            logs = [l for l in logs if l.get("mo_number") == mo_number]
        
        # Sort by timestamp (newest first)
        logs.sort(key=lambda x: x.get("timestamp", ""), reverse=True)
        
        # Limit if specified
        if limit:
            logs = logs[:limit]
        
        return logs
    
    # Generic storage methods for backward compatibility
    
    def save(self, category: str, key: str, data: Dict[str, Any]) -> Dict[str, Any]:
        """Generic save method"""
        filepath = self._get_file_path(category, f"{key}.json")
        self._write_json(filepath, data)
        return data
    
    def load(self, category: str, key: str, default: Any = None) -> Any:
        """Generic load method"""
        filepath = self._get_file_path(category, f"{key}.json")
        return self._read_json(filepath, default)


class CSVStorage:
    """CSV-based storage for large datasets (e.g., Clover orders)"""
    
    def __init__(self, data_dir: str = "data"):
        """Initialize CSV storage manager"""
        self.data_dir = Path(data_dir)
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure all required directories exist"""
        (self.data_dir / "clover").mkdir(parents=True, exist_ok=True)
    
    def _get_file_path(self, category: str, filename: str) -> Path:
        """Get full path to a CSV file"""
        if not filename.endswith('.csv'):
            filename += '.csv'
        return self.data_dir / category / filename
    
    def append_row(self, category: str, filename: str, row: Dict[str, Any], headers: Optional[List[str]] = None):
        """Append a row to a CSV file"""
        import csv
        
        filepath = self._get_file_path(category, filename)
        
        # Determine if file exists and has headers
        file_exists = filepath.exists()
        
        # If headers provided and file doesn't exist, write headers first
        if headers and not file_exists:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                writer.writeheader()
        
        # Read existing headers if file exists
        if file_exists:
            with open(filepath, 'r', encoding='utf-8') as f:
                reader = csv.DictReader(f)
                if reader.fieldnames:
                    headers = reader.fieldnames
        
        # Append row
        if headers:
            filepath.parent.mkdir(parents=True, exist_ok=True)
            with open(filepath, 'a', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=headers)
                if not file_exists:
                    writer.writeheader()
                writer.writerow(row)

