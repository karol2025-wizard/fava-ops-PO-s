"""
Database Manager - JSON-based implementation

This module provides a backward-compatible interface to DatabaseManager
using JSON file storage instead of MySQL.

Since MRPeasy is the system of record, this storage is only for:
- Local analytics (Clover orders)
- Caching
- Production records (handled separately via JSONStorage)

All data is stored in JSON files in the data/ directory.
"""

import json
import re
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import logging

logger = logging.getLogger(__name__)


class DatabaseManager:
    """
    JSON-based database manager that maintains compatibility with MySQL-based code.
    Uses JSON files for persistence.
    """
    
    def __init__(self):
        """Initialize the JSON-based database manager"""
        self.data_dir = Path("data")
        self.clover_dir = self.data_dir / "clover"
        self.clover_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize data structures (in-memory for now, persisted to JSON)
        self.clover_dir = self.data_dir / "clover"
        self.production_dir = self.data_dir / "production"
        self.clover_dir.mkdir(parents=True, exist_ok=True)
        self.production_dir.mkdir(parents=True, exist_ok=True)
        
        # Clover orders files
        self._orders_file = self.clover_dir / "orders.json"
        self._items_file = self.clover_dir / "orders_items.json"
        self._modifications_file = self.clover_dir / "orders_items_modifications.json"
        self._payments_file = self.clover_dir / "orders_payments.json"
        
        # Production staging files
        self._erp_mo_to_import_file = self.production_dir / "erp_mo_to_import.json"
    
    def _read_json(self, filepath: Path, default: Any = None) -> Any:
        """Read JSON file"""
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
            filepath.parent.mkdir(parents=True, exist_ok=True)
            temp_file = filepath.with_suffix('.tmp')
            with open(temp_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, ensure_ascii=False, default=str)
            temp_file.replace(filepath)
        except Exception as e:
            logger.error(f"Error writing {filepath}: {e}")
            raise
    
    def _parse_sql_insert(self, query: str, values: Tuple = None) -> Dict[str, Any]:
        """
        Parse a simple INSERT SQL query to extract table name and columns.
        This is a simplified parser for backward compatibility.
        """
        # Extract table name (simplified)
        table_match = re.search(r'INSERT\s+INTO\s+(\w+)', query, re.IGNORECASE)
        if not table_match:
            raise ValueError(f"Cannot parse table name from query: {query}")
        
        table_name = table_match.group(1)
        
        # Extract column names (simplified)
        columns_match = re.search(r'\(([^)]+)\)', query)
        if not columns_match:
            raise ValueError(f"Cannot parse columns from query: {query}")
        
        columns = [col.strip() for col in columns_match.group(1).split(',')]
        
        return {
            'table': table_name,
            'columns': columns,
            'values': values or ()
        }
    
    def _get_table_file(self, table_name: str) -> Path:
        """Get the JSON file path for a table"""
        table_map = {
            'clover_orders': self._orders_file,
            'clover_orders_items': self._items_file,
            'clover_orders_items_modifications': self._modifications_file,
            'clover_orders_payments': self._payments_file,
            'erp_mo_to_import': self._erp_mo_to_import_file,
        }
        
        # If not in map, determine directory based on table name
        if table_name not in table_map:
            if 'clover' in table_name.lower():
                return self.clover_dir / f"{table_name}.json"
            elif 'erp' in table_name.lower() or 'mo' in table_name.lower():
                return self.production_dir / f"{table_name}.json"
            else:
                return self.data_dir / f"{table_name}.json"
        
        return table_map[table_name]
    
    def execute_query(self, query: str, values: Tuple = None):
        """
        Execute a query. For CREATE TABLE, this is a no-op.
        For INSERT/UPDATE/DELETE, it parses and executes.
        
        Returns the number of affected rows.
        """
        query_upper = query.strip().upper()
        
        # CREATE TABLE is a no-op (we don't need tables in JSON)
        if query_upper.startswith('CREATE TABLE'):
            return 0
        
        # For SELECT queries, they should use fetch_one or fetch_all
        if query_upper.startswith('SELECT'):
            logger.warning(f"SELECT queries should use fetch_one() or fetch_all(), not execute_query()")
            return 0
        
        # INSERT queries
        if query_upper.startswith('INSERT'):
            return self._execute_insert(query, values)
        
        # UPDATE queries
        if query_upper.startswith('UPDATE'):
            return self._execute_update(query, values)
        
        # DELETE queries (simplified handling)
        if query_upper.startswith('DELETE'):
            logger.warning(f"DELETE queries not yet fully supported: {query[:50]}...")
            return 0
        
        logger.warning(f"Query type not fully supported: {query[:50]}...")
        return 0
    
    def _execute_insert(self, query: str, values: Tuple = None) -> int:
        """Execute an INSERT query"""
        try:
            parsed = self._parse_sql_insert(query, values)
            table_name = parsed['table']
            columns = parsed['columns']
            values_tuple = parsed['values']
            
            # Handle auto-increment ID (for tables like erp_mo_to_import)
            # If first column is 'id' and value is None or 0, auto-generate
            filepath = self._get_table_file(table_name)
            records = self._read_json(filepath, [])
            
            # Find the next ID if needed
            if columns and columns[0].lower() == 'id':
                if not values_tuple or values_tuple[0] is None or values_tuple[0] == 0:
                    # Auto-generate ID
                    max_id = 0
                    for rec in records:
                        rec_id = rec.get('id')
                        if rec_id and isinstance(rec_id, int):
                            max_id = max(max_id, rec_id)
                    next_id = max_id + 1
                    # Replace None/0 with next_id
                    values_list = list(values_tuple)
                    values_list[0] = next_id
                    values_tuple = tuple(values_list)
            
            # Create record dictionary
            record = dict(zip(columns, values_tuple))
            
            # Add inserted_at timestamp if not present and column exists
            if 'inserted_at' not in record:
                record['inserted_at'] = datetime.now().isoformat()
            
            # Handle ON DUPLICATE KEY UPDATE (upsert)
            # Check for duplicate (assuming first column is primary key, or 'id' column)
            primary_key = 'id' if 'id' in record else (columns[0] if columns else None)
            primary_value = record.get(primary_key) if primary_key else None
            
            # Find existing record
            existing_idx = None
            if primary_key and primary_value:
                for i, rec in enumerate(records):
                    if rec.get(primary_key) == primary_value:
                        existing_idx = i
                        break
            
            if existing_idx is not None:
                # Update existing record
                if 'ON DUPLICATE KEY UPDATE' in query.upper():
                    # Merge with existing record
                    records[existing_idx].update(record)
                else:
                    # Replace existing record
                    records[existing_idx] = record
            else:
                # Add new record
                records.append(record)
            
            # Save to file
            self._write_json(filepath, records)
            
            return 1  # One row affected
        except Exception as e:
            logger.error(f"Error executing insert: {e}")
            raise

    def _execute_update(self, query: str, values: Tuple = None) -> int:
        """Execute an UPDATE query"""
        try:
            # Parse UPDATE query (simplified)
            # Format: UPDATE table SET column = %s WHERE condition
            table_match = re.search(r'UPDATE\s+(\w+)', query, re.IGNORECASE)
            if not table_match:
                raise ValueError(f"Cannot parse table name from UPDATE query: {query}")
            
            table_name = table_match.group(1)
            filepath = self._get_table_file(table_name)
            records = self._read_json(filepath, [])
            
            # Parse SET clause
            set_match = re.search(r'SET\s+(\w+)\s*=\s*%s', query, re.IGNORECASE)
            if not set_match:
                raise ValueError(f"Cannot parse SET clause from UPDATE query: {query}")
            
            column = set_match.group(1)
            new_value = values[0] if values else None
            
            # Parse WHERE clause (simplified - supports WHERE column IN (%s, %s, ...) or WHERE column = %s)
            affected_count = 0
            
            if 'WHERE' in query.upper():
                if 'IN' in query.upper():
                    # Handle WHERE id IN (%s, %s, ...) - assumes first %s is the column value
                    # values format: (new_value, id1, id2, ...)
                    in_match = re.search(r'WHERE\s+(\w+)\s+IN', query, re.IGNORECASE)
                    if in_match:
                        where_column = in_match.group(1)
                        id_values = values[1:] if len(values) > 1 else []
                        
                        for record in records:
                            if record.get(where_column) in id_values:
                                record[column] = new_value
                                affected_count += 1
                    else:
                        # Fallback: update all records
                        for record in records:
                            record[column] = new_value
                            affected_count += 1
                else:
                    # Handle WHERE column = %s or WHERE column IS NULL
                    where_match = re.search(r'WHERE\s+(\w+)\s*(=|IS\s+NULL|IS\s+NOT\s+NULL)', query, re.IGNORECASE)
                    if where_match:
                        where_column = where_match.group(1)
                        where_condition = where_match.group(2).upper().strip()
                        
                        if 'IS NULL' in where_condition:
                            where_value = None
                            check_is_null = True
                        elif 'IS NOT NULL' in where_condition:
                            where_value = None
                            check_is_null = False
                        else:
                            # WHERE column = %s
                            where_value = values[-1] if values and len(values) > 1 else values[0] if values else None
                            check_is_null = None
                        
                        for record in records:
                            record_value = record.get(where_column)
                            
                            if check_is_null is True:
                                if record_value is None or record_value == '':
                                    record[column] = new_value
                                    affected_count += 1
                            elif check_is_null is False:
                                if record_value is not None and record_value != '':
                                    record[column] = new_value
                                    affected_count += 1
                            elif record_value == where_value:
                                record[column] = new_value
                                affected_count += 1
                    else:
                        # No WHERE clause parsed - update all
                        for record in records:
                            record[column] = new_value
                            affected_count += 1
            else:
                # No WHERE clause - update all records
                for record in records:
                    record[column] = new_value
                    affected_count += 1
            
            # Save updated records
            if affected_count > 0:
                self._write_json(filepath, records)
            
            return affected_count
        except Exception as e:
            logger.error(f"Error executing update: {e}")
            raise
    
    def execute_batch_insert(self, query: str, values: List[Tuple]):
        """
        Execute batch insert. Processes multiple records at once.
        """
        try:
            affected = 0
            for value_tuple in values:
                affected += self._execute_insert(query, value_tuple)
            return affected
        except Exception as e:
            logger.error(f"Error executing batch insert: {e}")
            raise
    
    def fetch_one(self, query: str, values: Tuple = None):
        """
        Fetch one row. Returns a tuple of values (similar to MySQL cursor).
        """
        results = self._fetch_query(query, values, limit=1)
        if results:
            # Return as tuple (like MySQL cursor.fetchone())
            row = results[0]
            return tuple(row.values()) if isinstance(row, dict) else row
        return None
    
    def fetch_all(self, query: str, values: Tuple = None) -> List[Dict[str, Any]]:
        """
        Fetch all rows. Returns a list of dictionaries.
        """
        return self._fetch_query(query, values)
    
    def _fetch_query(self, query: str, values: Tuple = None, limit: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        Execute a SELECT query and return results.
        This is a simplified query parser for common SELECT patterns.
        """
        query_upper = query.strip().upper()
        
        # Parse table name from SELECT
        table_match = re.search(r'FROM\s+(\w+)', query_upper)
        if not table_match:
            logger.warning(f"Cannot parse table name from query: {query[:50]}...")
            return []
        
        table_name = table_match.group(1)
        filepath = self._get_table_file(table_name)
        records = self._read_json(filepath, [])
        
        # Simple WHERE clause parsing (very basic)
        if 'WHERE' in query_upper:
            filtered_records = []
            
            # Handle WHERE column IS NULL or IS NOT NULL
            is_null_match = re.search(r'WHERE\s+(\w+)\s+(IS\s+NULL|IS\s+NOT\s+NULL)', query_upper, re.IGNORECASE)
            if is_null_match:
                column = is_null_match.group(1)
                is_not = 'NOT' in is_null_match.group(2).upper()
                
                for record in records:
                    record_value = record.get(column)
                    is_null = record_value is None or record_value == ''
                    
                    if (is_not and not is_null) or (not is_not and is_null):
                        filtered_records.append(record)
                
                records = filtered_records
            elif values:
                # Handle WHERE column = %s or WHERE column >= %s, etc.
                where_match = re.search(r'WHERE\s+(\w+)\s*([>=<]+|=)', query_upper)
                if where_match:
                    column = where_match.group(1)
                    operator = where_match.group(2).strip()
                    value = values[0] if values else None
                    
                    for record in records:
                        record_value = record.get(column)
                        if self._evaluate_condition(record_value, operator, value):
                            filtered_records.append(record)
                    
                    records = filtered_records
                # Handle WHERE column IN (%s, %s) AND column = %s (multiple conditions)
                elif 'AND' in query_upper:
                    and_match = re.search(r'WHERE\s+(\w+)\s*(IS\s+NULL|IS\s+NOT\s+NULL|=\s*%s).*AND\s+(\w+)\s*(IS\s+NULL|IS\s+NOT\s+NULL|=\s*%s|!=\s*%s)', query_upper, re.IGNORECASE)
                    if and_match:
                        col1 = and_match.group(1)
                        cond1 = and_match.group(2)
                        col2 = and_match.group(3)
                        cond2 = and_match.group(4)
                        
                        for record in records:
                            val1 = record.get(col1)
                            val2 = record.get(col2)
                            
                            # Evaluate first condition
                            cond1_ok = False
                            if 'IS NULL' in cond1.upper():
                                cond1_ok = (val1 is None or val1 == '')
                            elif 'IS NOT NULL' in cond1.upper():
                                cond1_ok = (val1 is not None and val1 != '')
                            elif '=' in cond1 and len(values) >= 1:
                                cond1_ok = (val1 == values[0])
                            
                            # Evaluate second condition
                            cond2_ok = False
                            if 'IS NULL' in cond2.upper():
                                cond2_ok = (val2 is None or val2 == '')
                            elif 'IS NOT NULL' in cond2.upper():
                                cond2_ok = (val2 is not None and val2 != '')
                            elif '!=' in cond2 and len(values) >= 2:
                                cond2_ok = (val2 != values[1])
                            elif '=' in cond2 and len(values) >= 1:
                                cond2_ok = (val2 == values[-1])
                            
                            if cond1_ok and cond2_ok:
                                filtered_records.append(record)
                        
                        records = filtered_records
        
        # Simple ORDER BY parsing
        if 'ORDER BY' in query_upper:
            order_match = re.search(r'ORDER BY\s+(\w+)\s+(ASC|DESC)?', query_upper, re.IGNORECASE)
            if order_match:
                column = order_match.group(1)
                direction = (order_match.group(2) or 'ASC').upper()
                
                records.sort(
                    key=lambda x: x.get(column),
                    reverse=(direction == 'DESC')
                )
        
        # LIMIT
        if limit or 'LIMIT' in query_upper:
            limit_match = re.search(r'LIMIT\s+(\d+)', query_upper)
            if limit_match:
                limit_value = int(limit_match.group(1))
                records = records[:limit_value]
            elif limit:
                records = records[:limit]
        
        # GROUP BY (very basic)
        if 'GROUP BY' in query_upper:
            # For now, just return raw records
            # A more sophisticated implementation would group them
            pass
        
        return records
    
    def _evaluate_condition(self, record_value: Any, operator: str, query_value: Any) -> bool:
        """Evaluate a WHERE condition"""
        if operator == '=' or operator == '==':
            return record_value == query_value
        elif operator == '>=':
            return record_value >= query_value
        elif operator == '<=':
            return record_value <= query_value
        elif operator == '>':
            return record_value > query_value
        elif operator == '<':
            return record_value < query_value
        return False
