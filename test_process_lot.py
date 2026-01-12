"""
Script de prueba para verificar que process_single_lot.py funciona correctamente
"""
import subprocess
import sys
import os

def test_process_lot():
    """Prueba el script process_single_lot.py con un lote de ejemplo"""
    
    script_path = os.path.join(os.path.dirname(__file__), "process_single_lot.py")
    
    # Ejemplo de uso (ajusta estos valores según tus necesidades)
    lot_code = "L28868"  # Cambia por un lote real
    quantity = "10.00"
    uom = "pcs"
    
    print("=" * 60)
    print("PRUEBA DE process_single_lot.py")
    print("=" * 60)
    print(f"\nEjecutando: python {script_path} {lot_code} {quantity} {uom}")
    print()
    
    try:
        result = subprocess.run(
            [sys.executable, script_path, lot_code, quantity, uom],
            capture_output=True,
            text=True,
            timeout=120  # 2 minutos de timeout
        )
        
        print("STDOUT:")
        print(result.stdout)
        
        if result.stderr:
            print("\nSTDERR:")
            print(result.stderr)
        
        print(f"\nExit code: {result.returncode}")
        
        if result.returncode == 0:
            print("\n✅ PRUEBA EXITOSA")
        else:
            print("\n❌ PRUEBA FALLÓ")
            
    except subprocess.TimeoutExpired:
        print("\n❌ TIMEOUT: El script tardó más de 2 minutos")
    except Exception as e:
        print(f"\n❌ ERROR: {str(e)}")

if __name__ == "__main__":
    test_process_lot()

