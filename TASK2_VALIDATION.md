# TASK 2 Validation - Barcode Scan Trigger (Lot App)

## Status: ⚠️ REQUIRES EXTERNAL APP IMPLEMENTATION

## Requirements

The external app (`G:\Shared drives\Fava\Applications\MO-lot-label-generator`) must implement:

### On Barcode Scan + Submit:
1. ✅ Extract Lot Code from barcode
2. ✅ Prompt user for ACTUAL produced quantity
3. ✅ Validate quantity > 0
4. ✅ Immediately trigger workflow

## Implementation Options

### Option 1: Direct Function Call (If Python-based)
```python
import sys
import os
sys.path.append(r'C:\Users\Operations - Fava\Desktop\code\fava ops PO\'s')

from shared.production_workflow import ProductionWorkflow

# After barcode scan
lot_code = extract_lot_from_barcode(barcode_data)  # Extract from barcode

# Prompt user for actual quantity
actual_quantity = prompt_user_for_quantity()  # User input
if actual_quantity <= 0:
    show_error("Quantity must be greater than 0")
    return

# Get UOM if needed
uom = get_uom_from_user()  # Optional

# Immediately trigger workflow
workflow = ProductionWorkflow()
success, result_data, message = workflow.process_production_completion(
    lot_code=lot_code,
    produced_quantity=actual_quantity,
    uom=uom,
    item_code=None
)

if success:
    # Generate labels
    generate_labels(result_data)
    # Show summary
    show_summary(result_data['summary_pdf'])
    # Allow printing
    enable_print_button()
else:
    # Block process, show error
    show_error(message)
    block_submit()
```

### Option 2: Command Line Script
```python
# After barcode scan + quantity entry
import subprocess

lot_code = extract_lot_from_barcode(barcode_data)
actual_quantity = prompt_user_for_quantity()

if actual_quantity <= 0:
    show_error("Quantity must be greater than 0")
    return

# Call script
result = subprocess.run([
    "python",
    r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\process_single_lot.py",
    lot_code,
    str(actual_quantity),
    uom  # Optional
], capture_output=True, text=True)

if result.returncode == 0:
    # Success
    show_success(result.stdout)
    generate_labels()
else:
    # Error
    show_error(result.stdout)
    block_submit()
```

### Option 3: Database Insert + Auto-Process
```python
# After barcode scan + quantity entry
import mysql.connector

lot_code = extract_lot_from_barcode(barcode_data)
actual_quantity = prompt_user_for_quantity()

if actual_quantity <= 0:
    show_error("Quantity must be greater than 0")
    return

# Insert into database
db = mysql.connector.connect(...)
cursor = db.cursor()
cursor.execute("""
    INSERT INTO erp_mo_to_import (lot_code, quantity, uom, inserted_at)
    VALUES (%s, %s, %s, NOW())
""", (lot_code, actual_quantity, uom))
db.commit()

# Trigger immediate processing
subprocess.run([
    "python",
    r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\auto_process_production.py",
    "--mode", "once",
    "--limit", "1"
])
```

## Validation Checklist

### External App Must:
- [ ] Extract Lot Code from barcode scan
- [ ] Prompt user for ACTUAL produced quantity
- [ ] Validate quantity > 0 (block if invalid)
- [ ] Immediately call workflow after submit
- [ ] Handle success: Generate labels, show summary, allow printing
- [ ] Handle errors: Block process, show error message

### Workflow Integration Ready:
- [x] `ProductionWorkflow.process_production_completion()` exists
- [x] `process_single_lot.py` script exists
- [x] `auto_process_production.py` exists
- [x] All workflow modules (TASK 3-6) are complete

## Error Handling in External App

### No MO Found
- **Error**: "No Manufacturing Order found with lot code: {lot_code}"
- **Action**: Block submit, show error, allow user to retry

### Multiple MOs Found
- **Error**: "Multiple Manufacturing Orders found with lot code {lot_code}. Supervisor intervention required."
- **Action**: Block submit, show error, require supervisor

### MRPeasy Unavailable
- **Error**: Retry logic handles this automatically (up to 3 retries)
- **If all retries fail**: Block submit, show error

### Invalid Quantity
- **Validation**: quantity > 0
- **Action**: Block submit, show error "Quantity must be greater than 0"

## Testing

To test the integration from external app:

1. **Test with valid lot code**:
   ```python
   workflow = ProductionWorkflow()
   success, result, msg = workflow.process_production_completion(
       lot_code="L28553",
       produced_quantity=2.5,
       uom="tray"
   )
   assert success == True
   ```

2. **Test with invalid lot code**:
   ```python
   success, result, msg = workflow.process_production_completion(
       lot_code="INVALID",
       produced_quantity=2.5,
       uom="tray"
   )
   assert success == False
   assert "No Manufacturing Order found" in msg
   ```

3. **Test with invalid quantity**:
   ```python
   # Should be blocked by external app before calling workflow
   # Workflow also validates: actual_quantity >= 0
   ```

## Next Steps

1. **External App Developer**: Implement TASK 2 requirements
2. **Integration**: Choose integration option (1, 2, or 3)
3. **Testing**: Test with sample lot codes
4. **Validation**: Verify complete flow works end-to-end

## Notes

- The workflow modules (TASK 3-6) are **already complete** and ready to use
- The external app only needs to call the workflow after barcode scan + quantity entry
- All error handling, logging, and MRPeasy updates are handled by the workflow
- The workflow automatically generates summary PDF and handles all operations

