# MO and Recipes Optimization Analysis

## 1. API Calls Per Product Analysis

### Current API Call Flow for a Single Product:

#### Initial Load (Once per session):
- `fetch_all_products()` - Fetches ALL products (paginated, ~100 per page)
- `fetch_units()` - Fetches ALL units (paginated, ~100 per page)
- **Total: 2 API calls** (cached for 6 hours)

#### Recipe View Flow (per product):
- `find_recipe_pdf_from_zip()` - No API call (local file system)
- `find_recipe_by_item_code()` - 1 Google Docs API call (if ZIP fails)
- **Total: 0-1 API calls per product**

#### MO Creation Flow (per product):
- `create_manufacturing_order()` - 1 API call (POST)
  - Internally calls `get_item_details()` - 1 API call (GET) if item_code provided
- `get_manufacturing_order_details()` - 1 API call (GET) after MO creation
- **Total: 2-3 API calls per MO creation**

### Performance Issues:
1. **Redundant item lookup**: `create_manufacturing_order()` calls `get_item_details()` even though we already have the item from cache
2. **No batching**: Each MO creation is a separate API call
3. **Cache not fully utilized**: Items are cached but we still make API calls for item details

### Optimization Opportunities:
- Pass `article_id` directly to `create_manufacturing_order()` instead of `item_code` to avoid extra API call
- Batch MO creation requests (if creating multiple MOs)
- Use cached item data instead of fetching item details again

---

## 2. Unused Code Identification

### Unused Functions/Variables:
1. **`selected_team`** - Initialized but never set/used in main flow (only in validation sidebar)
2. **`validate_items_for_team()`** - Only used if `selected_team` is set, which never happens
3. **`EXPECTED_ITEMS_BY_TEAM`** - Only used by validation function above
4. **`TEAM_NAME_MAPPING`** and **`TEAM_NAME_REVERSE_MAPPING`** - Only used by validation
5. **`get_display_team_name()`** and **`get_original_team_name()`** - Only used by validation
6. **`download_image()`** - Defined but never called
7. **Legacy state variables** - Many are maintained for "compatibility" but may not be needed:
   - `selected_team`
   - `step` (partially used)
   - `show_recipe` (not used)
   - `gdocs_manager` (not used)

### Unused Imports:
- Check if all imports are actually used

### Dead Code Paths:
- Team selection/validation logic (lines 1731-1751) - never executed because `selected_team` is never set

---

## 3. Complexity Analysis

### State Management Complexity:
- **Dual state system**: New state machine + legacy states maintained in parallel
- **Sync function**: `sync_legacy_states()` adds complexity
- **Multiple aliases**: `category_selected`/`selected_category`, `item_selected`/`selected_item`, etc.

### Recipe Finding Complexity:
- `find_recipe_pdf_from_zip()` - Complex PDF parsing with multiple search variations
- `find_recipe_by_item_code()` - 3-pass search algorithm with extensive title variations
- Both functions have overlapping logic that could be consolidated

### Category Assignment Complexity:
- `get_professional_category()` - Very long function with many nested conditions
- Could be simplified with better data structure

### Redundant Logic:
- Item filtering happens multiple times with same logic
- Category assignment happens in loop (could be done once)
- Multiple places where `item.get('code')` is checked

---

## 4. Recommended Optimizations

### High Priority:
1. **Remove unused team validation code** (lines 1731-1751, related functions)
2. **Optimize MO creation** - Pass `article_id` directly instead of `item_code`
3. **Remove `download_image()` function** if not used
4. **Simplify state management** - Remove legacy state aliases if not needed

### Medium Priority:
5. **Consolidate recipe finding logic** - Extract common search patterns
6. **Simplify category assignment** - Use lookup table instead of complex conditionals
7. **Remove unused imports**

### Low Priority:
8. **Optimize PDF parsing** - Cache parsed PDFs if same file accessed multiple times
9. **Batch API calls** if creating multiple MOs

---

## 5. API Call Summary

### Per Product (Recipe View):
- **Current**: 0-1 API calls (0 if ZIP found, 1 if Google Docs needed)
- **Optimized**: Same (already optimal)

### Per Product (MO Creation):
- **Current**: 2-3 API calls
  - 1x `get_item_details()` (if using item_code)
  - 1x `create_manufacturing_order()` (POST)
  - 1x `get_manufacturing_order_details()` (GET)
- **Optimized**: 2 API calls
  - 1x `create_manufacturing_order()` with `article_id` (POST)
  - 1x `get_manufacturing_order_details()` (GET)
- **Savings**: 1 API call per MO creation (33% reduction)

### Initial Load:
- **Current**: 2 API calls (cached for 6 hours)
- **Optimized**: Same (already optimal with caching)
