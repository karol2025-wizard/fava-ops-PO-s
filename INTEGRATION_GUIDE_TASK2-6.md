# Integration Guide - TASK 2-6: Barcode Scan to MRPeasy Update

## Overview
This guide documents how the external MO-lot-label-generator app should integrate with the production workflow to automatically update MRPeasy when a barcode is scanned and submitted.

## Workflow Modules Status

### ✅ TASK 3: MRPeasy MO Lookup
- **Module**: `shared/mo_lookup.py`
- **Class**: `MOLookup`
- **Method**: `find_mo_by_lot_code(lot_code: str)`
- **Features**:
  - Searches MRPeasy by Lot Code
  - Expects exactly ONE MO
  - Error handling: 0 matches → blocks and logs
  - Error handling: >1 matches → blocks and logs

### ✅ TASK 4: MRPeasy Update & Close
- **Module**: `shared/mo_update.py`
- **Class**: `MOUpdate`
- **Method**: `update_mo_with_production(mo_id, actual_quantity, lot_code, status=20)`
- **Features**:
  - Updates produced quantity
  - Confirms lot code
  - Sets status to Done (20)
  - Atomic update

### ✅ TASK 5: Labels & Summary
- **Module**: `shared/production_summary.py`
- **Class**: `ProductionSummary`
- **Methods**:
  - `generate_summary_data()` - Creates summary data
  - `create_summary_pdf()` - Generates PDF summary
- **Summary includes**:
  - MO Number
  - Item Code & Title
  - Lot Code
  - Estimated Quantity (for reference)
  - Actual Quantity (highlighted)
  - Date & Time
  - Printable format

### ✅ TASK 6: Logging & Safety
- **Module**: `shared/production_logging.py`
- **Classes**:
  - `ProductionLogger` - Logs all operations
  - `RetryHandler` - Retry logic for MRPeasy API calls
- **Features**:
  - Logs: barcode scanned, lot code, MO number, quantities, status change
  - Atomic updates
  - Retry logic (max 3 retries, exponential backoff)

### ✅ Complete Workflow
- **Module**: `shared/production_workflow.py`
- **Class**: `ProductionWorkflow`
- **Method**: `process_production_completion(lot_code, produced_quantity, uom, item_code)`
- **Orchestrates**: All steps (TASK 2-6) in sequence

## Integration Options for External App

### Option 1: Direct Function Call (Recommended)
If the external app is Python-based or can call Python:

```python
import sys
import os
sys.path.append(r'C:\Users\Operations - Fava\Desktop\code\fava ops PO\'s')

from shared.production_workflow import ProductionWorkflow

# After barcode scan + quantity entry
workflow = ProductionWorkflow()
success, result_data, message = workflow.process_production_completion(
    lot_code="L28553",  # Extracted from barcode
    produced_quantity=2.5,  # Entered by user
    uom="tray",  # Unit of measure
    item_code=None  # Will be retrieved from MO
)

if success:
    # Generate labels and summary
    summary_pdf = result_data['summary_pdf']
    # Save or print summary_pdf
    print(f"SUCCESS: {message}")
else:
    print(f"ERROR: {message}")
```

### Option 2: Command Line Script
If the external app can execute command line:

```bash
python process_single_lot.py <lot_code> <quantity> [uom]
```

Example:
```bash
python process_single_lot.py L28553 2.5 tray
```

The script returns:
- Exit code 0 = Success
- Exit code 1 = Failure
- Prints SUCCESS/ERROR message to stdout

### Option 3: Database Trigger (Auto-Process)
If the external app writes to `erp_mo_to_import` table:

1. External app inserts into database:
   ```sql
   INSERT INTO erp_mo_to_import (lot_code, quantity, uom, inserted_at)
   VALUES ('L28553', 2.5, 'tray', NOW())
   ```

2. Run auto-processor (continuous monitoring):
   ```bash
   python auto_process_production.py --mode continuous --interval 5
   ```
   (5 second interval for near-immediate processing)

3. Or process immediately after insert:
   ```python
   # After database insert
   import subprocess
   subprocess.run([
       "python",
       "auto_process_production.py",
       "--mode", "once",
       "--limit", "1"
   ])
   ```

## TASK 2 Requirements (External App)

The external app (MO-lot-label-generator) must:

1. **On barcode scan**:
   - Extract Lot Code from barcode
   - Validate lot code format

2. **On submit**:
   - Prompt user for ACTUAL produced quantity
   - Validate quantity > 0
   - Get UOM (unit of measure) if needed

3. **Immediately trigger workflow**:
   - Call `ProductionWorkflow.process_production_completion()`
   - OR call `process_single_lot.py` script
   - OR insert into database and trigger auto-processor

4. **Handle results**:
   - If success: Generate labels, show summary, allow printing
   - If error: Display error message, block process

## Error Handling

### No MO Found
- Error: "No Manufacturing Order found with lot code: {lot_code}"
- Action: Block process, show error to user
- Logged: Yes

### Multiple MOs Found
- Error: "Multiple Manufacturing Orders found with lot code {lot_code}"
- Action: Block process, log for supervisor
- Logged: Yes (requires intervention)

### MRPeasy Unavailable
- Retry: Automatic (up to 3 retries with exponential backoff)
- If all retries fail: Block process, show error
- Logged: Yes

### Invalid Quantity
- Validation: quantity > 0
- Action: Block submit, prompt user to enter valid quantity

## Summary PDF Generation

After successful update, the workflow generates a PDF summary that includes:
- MO Number
- Item Code & Title
- Lot Code
- Estimated Quantity (for reference)
- **Actual Produced Quantity** (highlighted)
- Date & Time

The PDF is available in `result_data['summary_pdf']` (BytesIO object).

## Logging

All operations are logged with:
- Timestamp
- Lot Code
- MO Number & ID
- Estimated vs Actual quantity
- Status change (before → after)
- Success/Failure status
- Error messages (if any)

Logs are written to:
- Application logs (console + file)
- Database (optional, via ProductionLogger)

## Testing

To test the integration:

```python
from shared.production_workflow import ProductionWorkflow

workflow = ProductionWorkflow()
success, result, msg = workflow.process_production_completion(
    lot_code="L28553",
    produced_quantity=2.5,
    uom="tray"
)

print(f"Success: {success}")
print(f"Message: {msg}")
if success:
    print(f"MO Number: {result['mo_update']['mo_number']}")
    print(f"Status: {result['mo_update']['status']}")
```

## Next Steps

1. **External App Developer**: Implement TASK 2 requirements
2. **Integration**: Choose integration option (1, 2, or 3)
3. **Testing**: Test with sample lot codes
4. **Validation**: Verify MRPeasy updates correctly
5. **Deployment**: Deploy to production

