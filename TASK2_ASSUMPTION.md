# TASK 2 - Production Flow Hook - Assumption Documentation

## Issue
The MO-lot-label-generator application is located at:
`G:\Shared drives\Fava\Applications\MO-lot-label-generator`

It is an **executable (.exe) file**, not a Python script, so it cannot be directly modified.

## Assumption
Based on the existing codebase:
1. The `erp_mo_to_import` database table already exists and is used by `pages/erp_close_mo.py`
2. The table structure includes: `id`, `lot_code`, `quantity`, `uom`, `user_operations`, `inserted_at`, `failed_code`, `processed_at`
3. **ASSUMPTION**: The MO-lot-label-generator executable already writes to the `erp_mo_to_import` table when:
   - Lot Code is entered (e.g., L28553)
   - Actual production quantity is entered

## Implementation
I have created `shared/production_capture.py` which provides:
- `ProductionCapture` class to capture production data
- `capture_production_entry()` - Direct capture function
- `capture_from_database_entry()` - Capture from existing database entries
- `get_recent_captures()` - Retrieve recent captures

## Required Data Captured
- ✅ Lot Code
- ✅ Produced quantity
- ✅ Timestamp (from `inserted_at`)
- ⚠️ Item (if available - may need to be added to table or retrieved via API)

## Next Steps
1. Verify that MO-lot-label-generator writes to `erp_mo_to_import` table
2. If not, the executable source code needs to be modified to write to this table
3. If item_code is not in the table, it may need to be retrieved via MRPeasy API using the lot code

## Validation Needed
- Confirm MO-lot-label-generator writes to `erp_mo_to_import` table
- Confirm the table structure matches expectations
- Test that capture mechanism works with actual data

