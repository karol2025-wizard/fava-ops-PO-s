from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

@dataclass
class OrderItem:
    item_sku: str
    item_name: str
    quantity: int
    total_price: Decimal

@dataclass
class Order:
    check_number: str
    start_date: datetime
    total: Decimal
    tip_amount: Decimal
    items: Optional[List[OrderItem]] = None

@dataclass
class DailySummary:
    date: datetime
    weekday: int
    total_sales: Decimal
    total_tips: Decimal
    total_discounts: Decimal
