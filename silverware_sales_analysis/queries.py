class SalesQueries:
    GET_HISTORICAL_ORDERS = """
    SELECT 
        o.check_number, 
        o.start_date, 
        o.total,
        COALESCE(p.tip_amount, 0) as tip_amount
    FROM silverware_orders o
    LEFT JOIN silverware_orders_payments p ON o.check_number = p.check_number
    WHERE o.start_date BETWEEN %s AND %s
    """

    GET_ITEM_SALES = """
    SELECT 
        si.item_sku,
        si.name as item_name,
        sc.category_name,
        soi.price as price,
        so.start_date,
        so.check_number
    FROM silverware_orders_items soi
    JOIN silverware_orders so ON so.check_number = soi.check_number
    LEFT JOIN silverware_items si ON si.item_sku = soi.item_sku
    LEFT JOIN silverware_category sc ON sc.category_id = si.category_id
    WHERE so.start_date BETWEEN %s AND %s
    """

    GET_ORDER_ITEMS = """
    SELECT 
        si.name as item_name,
        si.item_sku,
        COUNT(*) as quantity,
        SUM(soi.price) as total_price
    FROM silverware_orders_items soi
    JOIN silverware_items si ON si.item_sku = soi.item_sku
    WHERE soi.check_number = %s
    GROUP BY si.name, si.item_sku
    """

    GET_DAILY_SALES = """
    SELECT 
        DATE(start_date) as date,
        WEEKDAY(start_date) as weekday,
        SUM(total) as total_sales
    FROM silverware_orders
    WHERE start_date BETWEEN %s AND %s
    GROUP BY DATE(start_date), WEEKDAY(start_date)
    """

    GET_DAILY_TIPS = """
    SELECT 
        DATE(so.start_date) as date,
        WEEKDAY(so.start_date) as weekday,
        SUM(sop.tip_amount) as total_tips
    FROM 
        silverware_orders so
        JOIN silverware_orders_payments sop ON so.check_number = sop.check_number
    WHERE 
        so.start_date BETWEEN %s AND %s
    GROUP BY 
        DATE(so.start_date), 
        WEEKDAY(so.start_date)
    """

    GET_DAILY_DISCOUNTS = """
    SELECT 
        DATE(so.start_date) as date,
        WEEKDAY(so.start_date) as weekday,
        SUM(soi.discount_value) as total_discounts
    FROM silverware_orders so
    JOIN silverware_orders_items soi ON so.check_number = soi.check_number
    WHERE so.start_date BETWEEN %s AND %s
    GROUP BY DATE(so.start_date), WEEKDAY(so.start_date)
    """
