"""
WeightLabelPrinter Helper Module

Este módulo proporciona una función simple para que WeightLabelPrinter.spec
pueda insertar fácilmente las cantidades producidas en el sistema.

OPCIÓN MÁS FÁCIL Y EFECTIVA:
Solo necesitas llamar a insert_production_quantity() cuando el usuario ingresa la cantidad.
"""

import logging
from datetime import datetime
from typing import Optional
from shared.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


def insert_production_quantity(
    lot_code: str,
    quantity: float,
    uom: Optional[str] = None,
    user_operations: Optional[str] = None
) -> bool:
    """
    Inserta una cantidad producida en el sistema para procesamiento automático.
    
    Esta es la función MÁS FÁCIL de usar. Solo necesitas llamarla cuando
    WeightLabelPrinter.spec captura la cantidad real producida.
    
    Args:
        lot_code: Código del LOT (ej: "L28553")
        quantity: Cantidad real producida (debe ser > 0)
        uom: Unidad de medida (opcional, ej: "kg", "lb", "gr")
        user_operations: Información adicional del usuario (opcional)
    
    Returns:
        True si se insertó correctamente, False si hubo error
    
    Example:
        # En WeightLabelPrinter.spec, cuando el usuario ingresa la cantidad:
        from shared.weightlabelprinter_helper import insert_production_quantity
        
        lot_code = "L28553"  # Del sistema
        cantidad_real = 100.5  # Ingresada por el usuario
        unidad = "kg"  # Del sistema
        
        if insert_production_quantity(lot_code, cantidad_real, unidad):
            print("✅ Cantidad registrada. El MO se actualizará automáticamente.")
        else:
            print("❌ Error al registrar la cantidad.")
    """
    if not lot_code or not lot_code.strip():
        logger.error("Lot code is required")
        return False
    
    if not quantity or quantity <= 0:
        logger.error(f"Invalid quantity: {quantity}. Must be > 0")
        return False
    
    try:
        db = DatabaseManager()
        
        # Insertar en erp_mo_to_import
        query = """
        INSERT INTO erp_mo_to_import (lot_code, quantity, uom, user_operations, inserted_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute_query(
            query,
            (
                lot_code.strip(),
                float(quantity),
                uom.strip() if uom else None,
                user_operations if user_operations else None,
                current_time
            )
        )
        
        logger.info(
            f"Production quantity inserted: LOT={lot_code}, Qty={quantity}, UOM={uom}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting production quantity: {str(e)}", exc_info=True)
        return False


# Función alternativa: procesamiento inmediato (si prefieres no usar la base de datos)
def process_production_immediately(
    lot_code: str,
    quantity: float,
    uom: Optional[str] = None
) -> tuple[bool, str]:
    """
    Procesa inmediatamente la producción sin usar la base de datos.
    
    Esta función actualiza el MO directamente sin pasar por la tabla.
    Úsala si prefieres procesamiento inmediato en lugar de procesamiento automático.
    
    Args:
        lot_code: Código del LOT
        quantity: Cantidad producida
        uom: Unidad de medida (opcional)
    
    Returns:
        Tuple de (success, message)
    
    Example:
        from shared.weightlabelprinter_helper import process_production_immediately
        
        success, message = process_production_immediately("L28553", 100.5, "kg")
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    """
    try:
        from shared.auto_mo_processor import process_production_by_lot
        return process_production_by_lot(lot_code, quantity, uom)
    except Exception as e:
        logger.error(f"Error processing production immediately: {str(e)}", exc_info=True)
        return False, f"Error: {str(e)}"
