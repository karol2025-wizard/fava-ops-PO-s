class SalesQueries:
    GET_HISTORICAL_ORDERS = """
    SELECT 
        o.order_id, 
        o.created_time, 
        o.total,
        o.delivery_method,
        o.delivery_platform,
        COALESCE(p.tip_amount, 0) as tip_amount
    FROM clover_orders o
    LEFT JOIN clover_orders_payments p ON o.order_id = p.order_id
    WHERE o.created_time BETWEEN %s AND %s
    """

    GET_ITEM_SALES = """
    SELECT 
        ci.item_sku,
        ci.name as item_name,
        cc.category_name,
        coi.final_price,
        co.created_time,
        co.order_id
    FROM clover_orders_items coi
    JOIN clover_orders co ON co.order_id = coi.order_id
    LEFT JOIN clover_items ci ON ci.item_sku = coi.item_sku
    LEFT JOIN clover_category cc ON cc.category_id = ci.category_id
    WHERE co.created_time BETWEEN %s AND %s
    """

    GET_ORDER_ITEMS = """
    SELECT 
        coi.clover_name,
        COUNT(*) as quantity,
        SUM(coi.final_price) as total_price
    FROM clover_orders_items coi
    WHERE coi.order_id = %s
    GROUP BY coi.clover_name
    """

    GET_DAILY_SALES = """
    SELECT 
        DATE(created_time) as date,
        WEEKDAY(created_time) as weekday,
        SUM(total) as total_sales
    FROM clover_orders
    WHERE created_time BETWEEN %s AND %s
    GROUP BY DATE(created_time), WEEKDAY(created_time)
    """

    GET_DAILY_TIPS = """
    SELECT 
        DATE(co.created_time) as date,
        WEEKDAY(co.created_time) as weekday,
        SUM(cop.tip_amount) as total_tips
    FROM 
        clover_orders co
        JOIN clover_orders_payments cop ON co.order_id = cop.order_id
    WHERE 
        co.created_time BETWEEN %s AND %s
    GROUP BY 
        DATE(co.created_time), 
        WEEKDAY(co.created_time)
    """

    GET_DAILY_MODIFICATIONS = """
    SELECT 
        DATE(co.created_time) as date,
        WEEKDAY(co.created_time) as weekday,
        SUM(coim.price) as total_mods
    FROM 
        clover_orders co
        JOIN clover_orders_items coi ON co.order_id = coi.order_id
        JOIN clover_orders_items_modifications coim ON coi.item_id = coim.item_id
    WHERE 
        co.created_time BETWEEN %s AND %s
    GROUP BY 
        DATE(co.created_time), 
        WEEKDAY(co.created_time)
    """

    GET_ORDER_DISCOUNTS = """
    SELECT 
        DATE(created_time) as date,
        WEEKDAY(created_time) as weekday,
        SUM(order_level_discount_amount) as total_order_discounts
    FROM clover_orders
    WHERE created_time BETWEEN %s AND %s
    GROUP BY DATE(created_time), WEEKDAY(created_time)
    """

    GET_ITEM_DISCOUNTS = """
    SELECT 
        DATE(co.created_time) as date,
        WEEKDAY(co.created_time) as weekday,
        SUM(coi.item_level_discount_amount) as total_item_discounts
    FROM 
        clover_orders co
        JOIN clover_orders_items coi ON co.order_id = coi.order_id
    WHERE 
        co.created_time BETWEEN %s AND %s
    GROUP BY 
        DATE(co.created_time), 
        WEEKDAY(co.created_time)
    """