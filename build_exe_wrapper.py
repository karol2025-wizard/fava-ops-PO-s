"""
Wrapper script para ejecutar mo_and_recipes.py como aplicación Streamlit
Este script será convertido a .exe usando PyInstaller
"""
import sys
import os
import subprocess
import webbrowser
import time
from pathlib import Path

def get_base_path():
    """Obtiene la ruta base del ejecutable o del script"""
    if getattr(sys, 'frozen', False):
        # Si está ejecutándose como .exe
        # PyInstaller crea un directorio temporal en sys._MEIPASS
        # Los archivos de datos están ahí durante la ejecución
        if hasattr(sys, '_MEIPASS'):
            # Primero intentar en el directorio temporal de PyInstaller
            temp_path = Path(sys._MEIPASS)
            if (temp_path / "pages" / "mo_and_recipes.py").exists():
                return temp_path
        
        # Si no está en _MEIPASS, usar el directorio del .exe
        base_path = Path(sys.executable).parent
    else:
        # Si está ejecutándose como script
        base_path = Path(__file__).parent
    
    return base_path

def main():
    """Función principal que ejecuta Streamlit"""
    base_path = get_base_path()
    
    # Ruta al archivo mo_and_recipes.py
    script_path = base_path / "pages" / "mo_and_recipes.py"
    
    # Verificar que el archivo existe
    if not script_path.exists():
        print("=" * 60)
        print("ERROR: No se encontró el archivo necesario")
        print("=" * 60)
        print(f"Buscando: {script_path}")
        print(f"Directorio actual: {os.getcwd()}")
        print(f"Directorio base: {base_path}")
        print()
        
        # Intentar buscar en ubicaciones alternativas
        alternative_paths = [
            Path(sys.executable).parent / "pages" / "mo_and_recipes.py",
            Path.cwd() / "pages" / "mo_and_recipes.py",
        ]
        
        if getattr(sys, 'frozen', False) and hasattr(sys, '_MEIPASS'):
            alternative_paths.insert(0, Path(sys._MEIPASS) / "pages" / "mo_and_recipes.py")
        
        print("Buscando en ubicaciones alternativas:")
        for alt_path in alternative_paths:
            print(f"  - {alt_path} {'[ENCONTRADO]' if alt_path.exists() else '[NO ENCONTRADO]'}")
            if alt_path.exists():
                script_path = alt_path
                base_path = script_path.parent.parent
                print(f"\n✓ Archivo encontrado en: {script_path}")
                break
        
        if not script_path.exists():
            print()
            print("SOLUCION:")
            print("Asegúrate de que los siguientes archivos estén en la misma carpeta que el .exe:")
            print("  - pages/mo_and_recipes.py")
            print("  - shared/ (carpeta completa)")
            print("  - config.py")
            print("  - .streamlit/secrets.toml")
            print("  - credentials/ (carpeta completa)")
            print()
            input("Presiona Enter para salir...")
            sys.exit(1)
    
    # Cambiar al directorio base para que Streamlit encuentre los módulos
    os.chdir(base_path)
    
    # Agregar el directorio base al PYTHONPATH
    if str(base_path) not in sys.path:
        sys.path.insert(0, str(base_path))
    
    # Configurar Streamlit
    os.environ['STREAMLIT_BROWSER_GATHER_USAGE_STATS'] = 'false'
    
    # Construir el comando de Streamlit
    # Usar streamlit directamente si está disponible, sino usar python -m streamlit
    streamlit_cmd = [
        sys.executable,
        "-m", "streamlit", "run",
        str(script_path),
        "--server.headless", "true",
        "--server.port", "8501",
        "--browser.gatherUsageStats", "false",
        "--server.address", "localhost"
    ]
    
    try:
        # Abrir el navegador después de un breve delay
        def open_browser():
            time.sleep(3)
            try:
                webbrowser.open("http://localhost:8501")
            except Exception as e:
                print(f"No se pudo abrir el navegador automáticamente: {e}")
                print("Por favor, abre manualmente: http://localhost:8501")
        
        import threading
        browser_thread = threading.Thread(target=open_browser, daemon=True)
        browser_thread.start()
        
        # Ejecutar Streamlit
        print("=" * 50)
        print("Iniciando aplicación Streamlit...")
        print(f"Directorio de trabajo: {base_path}")
        print(f"Archivo: {script_path}")
        print(f"La aplicación se abrirá en: http://localhost:8501")
        print("Presiona Ctrl+C para cerrar la aplicación")
        print("=" * 50)
        print()
        
        subprocess.run(streamlit_cmd)
        
    except KeyboardInterrupt:
        print("\n\nCerrando aplicación...")
    except FileNotFoundError:
        print("Error: No se encontró Streamlit. Asegúrate de que esté instalado.")
        input("Presiona Enter para salir...")
        sys.exit(1)
    except Exception as e:
        print(f"Error al ejecutar la aplicación: {e}")
        import traceback
        traceback.print_exc()
        input("Presiona Enter para salir...")
        sys.exit(1)

if __name__ == "__main__":
    main()
