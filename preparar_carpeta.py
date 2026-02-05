"""
Script Python para preparar carpeta completa para otra PC
Evita problemas con el shell de PowerShell
"""
import os
import shutil
from pathlib import Path

def main():
    print("=" * 60)
    print("Preparando carpeta completa para otra PC")
    print("=" * 60)
    print()
    
    # Directorio base del proyecto
    base_dir = Path(__file__).parent
    destino = base_dir / "dist" / "mo_and_recipes_completo"
    
    # Limpiar carpeta anterior si existe
    if destino.exists():
        print("Limpiando carpeta anterior...")
        shutil.rmtree(destino)
    
    # Crear estructura de carpetas
    print("Creando estructura de carpetas...")
    destino.mkdir(parents=True, exist_ok=True)
    (destino / ".streamlit").mkdir(exist_ok=True)
    (destino / "credentials").mkdir(exist_ok=True)
    (destino / "pages").mkdir(exist_ok=True)
    (destino / "shared").mkdir(exist_ok=True)
    
    print()
    print("Copiando archivos...")
    print()
    
    errores = []
    
    # 1. Copiar ejecutable
    exe_origen = base_dir / "dist" / "mo_and_recipes.exe"
    if exe_origen.exists():
        shutil.copy2(exe_origen, destino / "mo_and_recipes.exe")
        print("[OK] mo_and_recipes.exe")
    else:
        print("[ERROR] No se encontró dist/mo_and_recipes.exe")
        print("        Asegúrate de haber ejecutado el build primero!")
        errores.append("Ejecutable no encontrado")
    
    # 2. Copiar secrets.toml
    secrets_origen = base_dir / ".streamlit" / "secrets.toml"
    if secrets_origen.exists():
        shutil.copy2(secrets_origen, destino / ".streamlit" / "secrets.toml")
        print("[OK] .streamlit/secrets.toml")
    else:
        print("[ERROR] .streamlit/secrets.toml no encontrado - CRITICO")
        errores.append("secrets.toml faltante")
    
    # 3. Copiar credentials
    creds_origen = base_dir / "credentials"
    if creds_origen.exists() and creds_origen.is_dir():
        for archivo in creds_origen.iterdir():
            if archivo.is_file():
                shutil.copy2(archivo, destino / "credentials" / archivo.name)
        print(f"[OK] credentials/ ({len(list(creds_origen.glob('*.*')))} archivos)")
    else:
        print("[WARN] Carpeta credentials no encontrada")
    
    # 4. Copiar pages/mo_and_recipes.py
    pages_origen = base_dir / "pages" / "mo_and_recipes.py"
    if pages_origen.exists():
        shutil.copy2(pages_origen, destino / "pages" / "mo_and_recipes.py")
        print("[OK] pages/mo_and_recipes.py")
    else:
        print("[ERROR] pages/mo_and_recipes.py no encontrado - CRITICO")
        errores.append("mo_and_recipes.py faltante")
    
    # 5. Copiar shared (solo archivos .py, excluyendo __pycache__)
    shared_origen = base_dir / "shared"
    if shared_origen.exists() and shared_origen.is_dir():
        archivos_copiados = 0
        for archivo in shared_origen.glob("*.py"):
            shutil.copy2(archivo, destino / "shared" / archivo.name)
            archivos_copiados += 1
        print(f"[OK] shared/ ({archivos_copiados} archivos .py)")
    else:
        print("[ERROR] Carpeta shared no encontrada - CRITICO")
        errores.append("shared/ faltante")
    
    # 6. Copiar config.py
    config_origen = base_dir / "config.py"
    if config_origen.exists():
        shutil.copy2(config_origen, destino / "config.py")
        print("[OK] config.py")
    else:
        print("[WARN] config.py no encontrado")
    
    # 7. Crear README
    readme_content = """========================================
MO AND RECIPES - Aplicación Completa
========================================

INSTRUCCIONES DE USO:

1. Copia TODA esta carpeta a la PC destino

2. Asegúrate de que la estructura sea:
   mo_and_recipes_completo\\
   ├── mo_and_recipes.exe
   ├── pages\\
   │   └── mo_and_recipes.py
   ├── shared\\
   │   └── [archivos .py]
   ├── .streamlit\\
   │   └── secrets.toml
   ├── credentials\\
   │   └── [archivos JSON]
   └── config.py

3. Ejecuta mo_and_recipes.exe haciendo doble clic

4. La aplicación se abrirá en: http://localhost:8501

5. Si no se abre automáticamente, abre tu navegador
   y ve a esa dirección.

NOTAS:
- No muevas ni elimines ningún archivo de esta carpeta
- Todos los archivos deben estar en la misma carpeta
- La primera ejecución puede tardar unos segundos

========================================
"""
    with open(destino / "LEEME_PRIMERO.txt", "w", encoding="utf-8") as f:
        f.write(readme_content)
    print("[OK] LEEME_PRIMERO.txt (instrucciones)")
    
    # 8. Copiar script de verificación si existe
    verificar_script = base_dir / "verificar_archivos_necesarios.bat"
    if verificar_script.exists():
        shutil.copy2(verificar_script, destino / "verificar_archivos_necesarios.bat")
        print("[OK] verificar_archivos_necesarios.bat")
    
    print()
    print("=" * 60)
    if errores:
        print("ADVERTENCIA: Algunos archivos críticos faltan!")
        print("Errores encontrados:")
        for error in errores:
            print(f"  - {error}")
        print()
    else:
        print("Copia completada exitosamente!")
        print()
    print("=" * 60)
    print()
    print(f"Carpeta lista en: {destino}")
    print()
    print("ESTRUCTURA CREADA:")
    print()
    for item in sorted(destino.iterdir()):
        if item.is_dir():
            print(f"  📁 {item.name}/")
            # Mostrar algunos archivos dentro
            archivos = list(item.iterdir())
            if archivos:
                for arch in archivos[:3]:  # Mostrar primeros 3
                    print(f"      - {arch.name}")
                if len(archivos) > 3:
                    print(f"      ... y {len(archivos) - 3} más")
        else:
            print(f"  📄 {item.name}")
    print()
    print("Puedes:")
    print("1. Comprimir esta carpeta (ZIP/RAR)")
    print("2. Copiarla a otra PC")
    print("3. Descomprimirla")
    print("4. Ejecutar mo_and_recipes.exe")
    print()
    print("IMPORTANTE: Copia TODA la carpeta, no solo el .exe")
    print()
    
    input("Presiona Enter para salir...")

if __name__ == "__main__":
    main()
