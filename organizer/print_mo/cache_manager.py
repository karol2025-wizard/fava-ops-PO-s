# cache_manager.py
from typing import Dict, Optional, Any
from dataclasses import dataclass
import logging
from shared.api_manager import APIManager
from datetime import datetime, timedelta

@dataclass
class CacheData:
    """Data structure to hold cached data"""
    products: Dict[str, Any]  # Keyed by item_code
    lots: Dict[str, Any]      # Keyed by lot_code
    initialized: bool = False
    last_updated: Optional[datetime] = None

class CacheManager:
    """Manages caching of product and lot data"""
    _instance = None
    CACHE_EXPIRY_MINUTES = 15

    def __new__(cls):
        """Implement singleton pattern"""
        if cls._instance is None:
            cls._instance = super(CacheManager, cls).__new__(cls)
            cls._instance.cache = CacheData({}, {}, False, None)
        return cls._instance

    def initialize_cache(self, api_manager: APIManager) -> None:
        """Initialize cache with all products and lots"""
        current_time = datetime.now()

        # Check if cache needs refreshing
        if (self.cache.initialized and self.cache.last_updated and
            current_time - self.cache.last_updated < timedelta(minutes=self.CACHE_EXPIRY_MINUTES)):
            return

        try:
            # Fetch all products
            products = api_manager.fetch_all_products()
            if products:
                self.cache.products = {
                    product['code']: product
                    for product in products
                    if 'code' in product
                }

            # Fetch all lots
            lots = api_manager.fetch_stock_lots()
            if lots:
                self.cache.lots = {
                    lot['code']: lot
                    for lot in lots
                    if 'code' in lot
                }

            self.cache.initialized = True
            self.cache.last_updated = current_time
            logging.info(f"Cache initialized with {len(self.cache.products)} products and {len(self.cache.lots)} lots")

        except Exception as e:
            logging.error(f"Error initializing cache: {str(e)}")
            raise

    def get_product(self, item_code: str) -> Optional[Dict]:
        """Get product details from cache"""
        return self.cache.products.get(item_code)

    def get_lot(self, lot_code: str) -> Optional[Dict]:
        """Get lot details from cache"""
        return self.cache.lots.get(lot_code)

    def is_initialized(self) -> bool:
        """Check if cache is initialized"""
        return self.cache.initialized

    def needs_refresh(self) -> bool:
        """Check if cache needs to be refreshed"""
        if not self.cache.initialized or not self.cache.last_updated:
            return True

        current_time = datetime.now()
        return (current_time - self.cache.last_updated) >= timedelta(minutes=self.CACHE_EXPIRY_MINUTES)

    def clear_cache(self) -> None:
        """Clear the cache"""
        self.cache.products.clear()
        self.cache.lots.clear()
        self.cache.initialized = False
        self.cache.last_updated = None