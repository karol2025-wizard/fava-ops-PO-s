"""
Process Single Lot Entry

This script can be called directly from MORecordInsert.exe or WeightLabelPrinter.exe
to process a single lot entry immediately after it's created.

What this script does:
1. Looks up the Manufacturing Order (MO) by lot code in MRPeasy
2. Updates the actual produced quantity in MRPeasy
3. Changes the status to "Done" (20)
4. Closes the manufacturing order automatically

Usage from command line:
    python process_single_lot.py <lot_code> <quantity> [uom]

Example:
    python process_single_lot.py L28868 10.00 pcs

Or can be integrated into MORecordInsert.exe to call after clicking Submit button.
"""

import sys
import os
import logging
import traceback

# Add project root to path
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)

# Configure logging to both file and console
log_file = os.path.join(project_root, 'process_single_lot.log')
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)
logger = logging.getLogger(__name__)

try:
    from shared.production_workflow import ProductionWorkflow
except ImportError as e:
    logger.error(f"❌ Error importing ProductionWorkflow: {str(e)}")
    logger.error(f"Project root: {project_root}")
    logger.error(f"Python path: {sys.path}")
    raise


def process_lot(lot_code: str, quantity: float, uom: str = None):
    """
    Process a single lot entry immediately.
    
    This function:
    1. Looks up the MO by lot code
    2. Updates actual quantity in MRPeasy
    3. Changes status to "Done"
    4. Closes the manufacturing order automatically
    
    Args:
        lot_code: Lot code (e.g., L28868)
        quantity: Produced quantity (e.g., 10.00)
        uom: Unit of measure (optional, e.g., "pcs", "tray", "kg")
    
    Returns:
        Tuple of (success: bool, message: str)
        - success: True if the order was updated and closed successfully
        - message: Success or error message
    """
    logger.info(f"Processing lot: {lot_code}, quantity: {quantity}, uom: {uom}")
    
    try:
        logger.info("=" * 60)
        logger.info(f"Iniciando procesamiento de lote: {lot_code}")
        logger.info(f"Cantidad: {quantity}, UOM: {uom or 'N/A'}")
        logger.info("=" * 60)
        
        workflow = ProductionWorkflow()
        logger.info("✅ ProductionWorkflow inicializado correctamente")
        
        logger.info("Buscando MO en MRPeasy...")
        success, result_data, message = workflow.process_production_completion(
            lot_code=lot_code,
            produced_quantity=float(quantity),
            uom=uom,
            item_code=None
        )
        
        if success:
            logger.info("=" * 60)
            logger.info(f"✅ ÉXITO: {message}")
            logger.info("=" * 60)
            print(f"\n✅ SUCCESS: {message}")
            print(f"✅ La orden fue actualizada y cerrada en MRPeasy")
            
            # Mostrar detalles adicionales si están disponibles
            if result_data:
                mo_update = result_data.get('mo_update', {})
                mo_number = mo_update.get('mo_number', 'N/A')
                actual_qty = mo_update.get('actual_quantity', 'N/A')
                status = mo_update.get('status', 'N/A')
                logger.info(f"MO Number: {mo_number}")
                logger.info(f"Actual Quantity: {actual_qty}")
                logger.info(f"Status: {status}")
                print(f"   MO Number: {mo_number}")
                print(f"   Actual Quantity: {actual_qty}")
                print(f"   Status: {status}")
            
            return True, message
        else:
            logger.error("=" * 60)
            logger.error(f"❌ FALLÓ: {message}")
            logger.error("=" * 60)
            print(f"\n❌ ERROR: {message}")
            print(f"\nPor favor verifica:")
            print(f"  1. Que el código de lote '{lot_code}' existe en MRPeasy")
            print(f"  2. Que hay un MO asociado a este lote")
            print(f"  3. Que las credenciales de MRPeasy están configuradas correctamente")
            print(f"  4. Revisa el archivo de log: {log_file}")
            return False, message
            
    except ValueError as ve:
        error_msg = f"Error de validación o API: {str(ve)}"
        logger.error("=" * 60)
        logger.error(f"❌ ERROR: {error_msg}")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        print(f"\n❌ ERROR: {error_msg}")
        print(f"\nDetalles del error:")
        print(f"  {str(ve)}")
        print(f"\nRevisa el archivo de log para más detalles: {log_file}")
        return False, error_msg
    except Exception as e:
        error_msg = f"Error inesperado procesando lote {lot_code}: {str(e)}"
        logger.error("=" * 60)
        logger.error(f"❌ ERROR INESPERADO: {error_msg}")
        logger.error(traceback.format_exc())
        logger.error("=" * 60)
        print(f"\n❌ ERROR INESPERADO: {error_msg}")
        print(f"\nTraceback completo guardado en: {log_file}")
        return False, error_msg


def main():
    """Main entry point for command line usage"""
    if len(sys.argv) < 3:
        print("=" * 60)
        print("Process Single Lot - Actualizar MRPeasy")
        print("=" * 60)
        print("\nUsage: python process_single_lot.py <lot_code> <quantity> [uom]")
        print("\nExample:")
        print("  python process_single_lot.py L28868 10.00 pcs")
        print("\nThis script will:")
        print("  1. Look up the MO by lot code in MRPeasy")
        print("  2. Update the actual produced quantity")
        print("  3. Change status to 'Done'")
        print("  4. Close the manufacturing order automatically")
        print(f"\nLog file: {log_file}")
        sys.exit(1)
    
    lot_code = sys.argv[1].strip()
    try:
        quantity = float(sys.argv[2])
    except ValueError:
        print(f"❌ ERROR: La cantidad '{sys.argv[2]}' no es un número válido")
        sys.exit(1)
    
    uom = sys.argv[3].strip() if len(sys.argv) > 3 and sys.argv[3].strip() else None
    
    print("=" * 60)
    print(f"Procesando lote: {lot_code}")
    print(f"Cantidad: {quantity} {uom or ''}")
    print("=" * 60)
    print()
    
    success, message = process_lot(lot_code, quantity, uom)
    
    print()
    print("=" * 60)
    if success:
        print("✅ PROCESAMIENTO COMPLETADO EXITOSAMENTE")
        print(f"   {message}")
    else:
        print("❌ PROCESAMIENTO FALLÓ")
        print(f"   {message}")
        print(f"\n   Revisa el archivo de log para más detalles:")
        print(f"   {log_file}")
    print("=" * 60)
    
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()

