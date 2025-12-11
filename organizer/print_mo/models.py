from dataclasses import dataclass
from typing import List, Optional, Dict, Any
from datetime import datetime
import logging
from shared.api_manager import APIManager
from organizer.print_mo.cache_manager import CacheManager

# Exception class for data validation
class DataValidationError(Exception):
    """Raised when data validation fails"""
    pass

# Base data model
@dataclass
class BaseModel:
    """Base class for data models with common functionality"""

    @classmethod
    def validate_required_fields(cls, data: Dict[str, Any], required_fields: List[str]) -> None:
        """Validate that all required fields are present in the data"""
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            raise DataValidationError(f"Missing required fields: {', '.join(missing_fields)}")

@dataclass
class TargetLot(BaseModel):
    """Model for target lot data"""
    lot_id: int
    code: str
    location: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], api_manager: Optional['APIManager'] = None) -> 'TargetLot':
        """Create TargetLot instance from dictionary data"""
        cls.validate_required_fields(data, ['lot_id', 'code'])

        instance = cls(
            lot_id=data['lot_id'],
            code=data['code']
        )

        # Fetch additional lot details if API manager is provided
        if api_manager:
            try:
                cache_manager = CacheManager()
                lot_details = cache_manager.get_lot(data['code'])
                if lot_details:
                    locations = lot_details.get('locations', [])
                    instance.location = locations[0].get('location') if locations else None
            except Exception as e:
                logging.error(f"Error fetching lot details for {data['code']}: {str(e)}")

        return instance


@dataclass
class PartLot(BaseModel):
    """Model for part lot data"""
    lot_id: int
    code: str
    booked: float
    item_code: Optional[str] = None
    item_title: Optional[str] = None
    unit: Optional[str] = None
    location: Optional[str] = None
    vendor_uom: Optional[str] = None
    vendor_id: Optional[int] = None
    unit_conversion_rate: Optional[float] = None
    vendor_uom_percentage: Optional[float] = None
    group_title: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], product_details: Optional[Dict[str, Any]] = None,
                 api_manager: Optional['APIManager'] = None) -> 'PartLot':
        """Create PartLot instance from dictionary data"""
        cls.validate_required_fields(data, ['lot_id', 'code'])

        instance = cls(
            lot_id=data['lot_id'],
            code=data['code'],
            booked=data.get('booked', 0.0)
        )

        # Use product details for item information
        if product_details:
            instance.item_code = product_details.get('code')
            instance.item_title = product_details.get('title')
            instance.unit = product_details.get('unit')
            instance.group_title = product_details.get('group_title')

        # Still fetch location from lot cache
        if api_manager:
            try:
                cache_manager = CacheManager()
                lot_details = cache_manager.get_lot(data['code'])
                if lot_details:
                    locations = lot_details.get('locations', [])
                    instance.location = locations[0].get('location') if locations else None

                    # Get purchase order details if pur_ord_id exists
                    pur_ord_id = lot_details.get('pur_ord_id')
                    if pur_ord_id:
                        po_details = api_manager.get_single_purchase_order(pur_ord_id)
                        if po_details:
                            # Find matching product in PO
                            for product in po_details.get('products', []):
                                if product.get('item_code') == instance.item_code:
                                    instance.vendor_uom = product.get('vendor_unit')
                                    instance.vendor_id = po_details.get('vendor_id')
                                    break

                            # Get item details for purchase terms
                            if instance.vendor_id and instance.vendor_uom and product_details:
                                # Find matching purchase term
                                for term in product_details.get('purchase_terms', []):
                                    if (term.get('vendor_id') == instance.vendor_id and
                                        term.get('unit') == instance.vendor_uom):
                                        instance.unit_conversion_rate = term.get('unit_rate')
                                        break

                    # Calculate vendor UOM percentage if we have both booked quantity and conversion rate
                    if instance.unit_conversion_rate and instance.unit_conversion_rate != 0:
                        instance.vendor_uom_percentage = instance.booked / instance.unit_conversion_rate

            except Exception as e:
                logging.error(f"Error fetching lot details for {data['code']}: {str(e)}")

        return instance


@dataclass
class Part(BaseModel):
    """Model for part data"""
    lots: List[PartLot]
    product_id: Optional[int] = None
    item_code: Optional[str] = None
    item_title: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Dict[str, Any], api_manager: Optional['APIManager'] = None) -> 'Part':
        """Create Part instance from dictionary data"""
        product_id = data.get('product_id')
        product_details = None

        # Fetch product details from cache if product_id is available
        if product_id and api_manager:
            try:
                cache_manager = CacheManager()
                # Find product in cache where product_id matches
                product_details = next(
                    (prod for prod in cache_manager.cache.products.values()
                     if prod.get('product_id') == product_id),
                    None
                )
                if not product_details:
                    logging.warning(f"Could not find product details for product_id {product_id}")
            except Exception as e:
                logging.error(f"Error fetching product details for ID {product_id}: {str(e)}")

        lots = [PartLot.from_dict(lot, product_details, api_manager)
               for lot in data.get('lots', [])]

        return cls(
            lots=lots,
            product_id=product_id,
            item_code=product_details.get('code') if product_details else None,
            item_title=product_details.get('title') if product_details else None
        )

@dataclass
class Note(BaseModel):
    """Model for note data"""
    note_id: int
    author: str
    text: str

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Note':
        """Create Note instance from dictionary data"""
        cls.validate_required_fields(data, ['note_id', 'author', 'text'])
        return cls(
            note_id=data['note_id'],
            author=data['author'],
            text=data['text']
        )


@dataclass
class ManufacturingOrder(BaseModel):
    """Model for manufacturing order data"""
    code: str
    start_date: Optional[str]
    item_code: str
    item_title: str
    quantity: float
    unit: str
    man_ord_id: int
    target_lots: List[TargetLot]
    parts: List[Part]
    notes: List[Note]

    @classmethod
    def from_dict(cls, basic_data: Dict[str, Any],
                 detailed_data: Optional[Dict[str, Any]] = None,
                 api_manager: Optional['APIManager'] = None) -> 'ManufacturingOrder':
        """Create ManufacturingOrder instance from basic and detailed data"""
        try:
            data = detailed_data if detailed_data else basic_data
            cls.validate_required_fields(data, ['code', 'item_code', 'item_title', 'quantity', 'unit', 'man_ord_id'])

            # Initialize cache if needed
            if api_manager:
                cache_manager = CacheManager()
                if not cache_manager.is_initialized():
                    cache_manager.initialize_cache(api_manager)

            # Convert Unix timestamp to human readable date if present
            start_date = None
            if data.get('start_date'):
                try:
                    timestamp = float(data['start_date'])
                    start_date = datetime.fromtimestamp(timestamp).strftime('%Y-%m-%d %H:%M:%S')
                except (ValueError, TypeError) as e:
                    logging.warning(f"Error converting start_date: {str(e)}")
                    start_date = str(data['start_date'])

            return cls(
                man_ord_id=data['man_ord_id'],
                code=data['code'],
                start_date=start_date,
                item_code=data['item_code'],
                item_title=data['item_title'],
                quantity=float(data['quantity']),
                unit=data['unit'],
                target_lots=[TargetLot.from_dict(lot, api_manager) for lot in data.get('target_lots', [])],
                parts=[Part.from_dict(part, api_manager) for part in data.get('parts', [])],
                notes=[Note.from_dict(note) for note in data.get('notes', [])]
            )
        except (KeyError, ValueError, DataValidationError) as e:
            logging.error(f"Error creating ManufacturingOrder: {str(e)}")
            raise DataValidationError(f"Invalid manufacturing order data: {str(e)}")

