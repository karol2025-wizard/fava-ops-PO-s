from dataclasses import dataclass
from datetime import datetime
from decimal import Decimal
from typing import Optional, List

@dataclass
class OrderItem:
    clover_name: str
    quantity: int
    total_price: Decimal

@dataclass
class Order:
    order_id: str
    created_time: datetime
    total: Decimal
    delivery_method: str
    delivery_platform: str
    tip_amount: Decimal
    items: Optional[List[OrderItem]] = None