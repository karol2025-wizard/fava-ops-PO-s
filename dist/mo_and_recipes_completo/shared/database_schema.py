# database_schema.py

ORDERS_TABLE = """
CREATE TABLE IF NOT EXISTS clover_orders (
    order_id VARCHAR(255) PRIMARY KEY,
    created_time DATETIME,
    delivery_note TEXT,
    delivery_platform VARCHAR(255),
    delivery_method VARCHAR(255),
    delivery_time VARCHAR(255),
    currency VARCHAR(10),
    total DECIMAL(10, 2),
    external_reference_id VARCHAR(255),
    employee_id VARCHAR(255),
    order_level_discount_name VARCHAR(255),
    order_level_discount_percentage DECIMAL(10, 2),
    order_level_discount_amount DECIMAL(10, 2),
    order_raw_json JSON,
    lineitems_raw_json JSON,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

ITEMS_TABLE = """
CREATE TABLE IF NOT EXISTS clover_orders_items (
    item_id VARCHAR(255) PRIMARY KEY,
    order_id VARCHAR(255),
    clover_name VARCHAR(255),
    price DECIMAL(10, 2),
    price_with_mod DECIMAL(10, 2),
    final_price DECIMAL(10, 2),
    item_level_discount_name VARCHAR(255),
    item_level_discount_percentage DECIMAL(10, 2),
    item_level_discount_amount DECIMAL(10, 2),
    item_sku VARCHAR(255),
    item_code VARCHAR(255),
    item_note TEXT,
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
"""

MODIFICATIONS_TABLE = """
CREATE TABLE IF NOT EXISTS clover_orders_items_modifications (
    id INT AUTO_INCREMENT PRIMARY KEY,
    item_id VARCHAR(255),
    modifier_name VARCHAR(255),
    price DECIMAL(10, 2),
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (item_id) REFERENCES clover_orders_items(item_id)
);
"""

PAYMENTS_TABLE = """
CREATE TABLE IF NOT EXISTS clover_orders_payments (
    id INT AUTO_INCREMENT PRIMARY KEY,
    order_id VARCHAR(255),
    tip_amount DECIMAL(10, 2),
    tax_amount DECIMAL(10, 2),
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (order_id) REFERENCES clover_orders(order_id)
);
"""

# Dictionary to easily access all table schemas
SCHEMAS = {
    'orders': ORDERS_TABLE,
    'items': ITEMS_TABLE,
    'modifications': MODIFICATIONS_TABLE,
    'payments': PAYMENTS_TABLE
}