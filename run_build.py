"""
Script Python para ejecutar el build del .exe
Este script puede ejecutarse directamente sin problemas de shell
"""
import subprocess
import sys
import os
from pathlib import Path

def check_pyinstaller():
    """Verifica si PyInstaller está instalado"""
    try:
        import PyInstaller
        print("[OK] PyInstaller está instalado")
        return True
    except ImportError:
        print("[INFO] PyInstaller no está instalado. Instalando...")
        try:
            subprocess.check_call([sys.executable, "-m", "pip", "install", "pyinstaller"])
            print("[OK] PyInstaller instalado correctamente")
            return True
        except subprocess.CalledProcessError:
            print("[ERROR] No se pudo instalar PyInstaller")
            return False

def clean_build_dirs():
    """Limpia directorios de build anteriores"""
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for dir_name in dirs_to_clean:
        if os.path.exists(dir_name):
            try:
                import shutil
                shutil.rmtree(dir_name)
                print(f"[OK] Limpiado: {dir_name}")
            except Exception as e:
                print(f"[WARN] No se pudo limpiar {dir_name}: {e}")

def run_build():
    """Ejecuta PyInstaller para generar el .exe"""
    spec_file = "mo_and_recipes.spec"
    
    if not os.path.exists(spec_file):
        print(f"[ERROR] No se encontró el archivo {spec_file}")
        return False
    
    print(f"[INFO] Construyendo ejecutable usando {spec_file}...")
    print("=" * 60)
    
    try:
        # Ejecutar PyInstaller
        result = subprocess.run(
            [sys.executable, "-m", "PyInstaller", spec_file, "--clean"],
            check=True,
            capture_output=False
        )
        
        print("=" * 60)
        print("[OK] Build completado exitosamente!")
        print()
        print("El ejecutable se encuentra en: dist\\mo_and_recipes.exe")
        print()
        print("IMPORTANTE: Para usar el .exe en otra PC, necesitas:")
        print("1. Copiar el archivo dist\\mo_and_recipes.exe")
        print("2. Copiar la carpeta dist\\mo_and_recipes (si existe) con todos sus archivos")
        print("3. Asegurarte de que la PC destino tenga las credenciales necesarias")
        print("   (archivo .streamlit/secrets.toml)")
        return True
        
    except subprocess.CalledProcessError as e:
        print("=" * 60)
        print(f"[ERROR] Error al construir el ejecutable")
        print(f"Código de error: {e.returncode}")
        return False
    except Exception as e:
        print("=" * 60)
        print(f"[ERROR] Error inesperado: {e}")
        return False

def main():
    """Función principal"""
    print("=" * 60)
    print("Build de mo_and_recipes.exe")
    print("=" * 60)
    print()
    
    # Verificar PyInstaller
    if not check_pyinstaller():
        input("Presiona Enter para salir...")
        sys.exit(1)
    
    print()
    
    # Limpiar builds anteriores
    print("Limpiando builds anteriores...")
    clean_build_dirs()
    print()
    
    # Ejecutar build
    success = run_build()
    
    print()
    if not success:
        input("Presiona Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()
