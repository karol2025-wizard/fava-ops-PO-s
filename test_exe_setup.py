"""
Script de prueba para verificar que todos los archivos necesarios están presentes
antes de generar el .exe
"""
import os
from pathlib import Path

def check_files():
    """Verifica que todos los archivos necesarios existan"""
    project_root = Path(__file__).parent
    errors = []
    warnings = []
    
    # Archivos requeridos
    required_files = [
        'pages/mo_and_recipes.py',
        'config.py',
        'build_exe_wrapper.py',
        'mo_and_recipes.spec',
    ]
    
    # Directorios requeridos
    required_dirs = [
        'shared',
    ]
    
    # Archivos opcionales (solo advertencia)
    optional_files = [
        '.streamlit/secrets.toml',
        'credentials',
        'media',
    ]
    
    print("=" * 60)
    print("Verificación de archivos para build del .exe")
    print("=" * 60)
    print()
    
    # Verificar archivos requeridos
    print("Archivos requeridos:")
    for file_path in required_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [ERROR] {file_path} - FALTANTE")
            errors.append(file_path)
    
    print()
    
    # Verificar directorios requeridos
    print("Directorios requeridos:")
    for dir_path in required_dirs:
        full_path = project_root / dir_path
        if full_path.exists() and full_path.is_dir():
            print(f"  [OK] {dir_path}/")
        else:
            print(f"  [ERROR] {dir_path}/ - FALTANTE")
            errors.append(dir_path)
    
    print()
    
    # Verificar archivos opcionales
    print("Archivos opcionales (recomendados):")
    for file_path in optional_files:
        full_path = project_root / file_path
        if full_path.exists():
            print(f"  [OK] {file_path}")
        else:
            print(f"  [WARN] {file_path} - No encontrado (puede causar problemas en runtime)")
            warnings.append(file_path)
    
    print()
    print("=" * 60)
    
    if errors:
        print("ERRORES ENCONTRADOS:")
        for error in errors:
            print(f"  - {error}")
        print()
        print("Por favor, asegúrate de que todos los archivos requeridos existan")
        print("antes de generar el .exe")
        return False
    else:
        print("[OK] Todos los archivos requeridos estan presentes")
        if warnings:
            print()
            print("ADVERTENCIAS:")
            for warning in warnings:
                print(f"  - {warning}")
            print()
            print("Estos archivos son opcionales pero recomendados.")
            print("El .exe puede no funcionar correctamente sin ellos.")
        return True

if __name__ == "__main__":
    success = check_files()
    if not success:
        exit(1)
