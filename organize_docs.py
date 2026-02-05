import os
import shutil

# Crear carpeta docs si no existe
os.makedirs('docs', exist_ok=True)

# Mover todos los archivos .md excepto README.md
md_files = [f for f in os.listdir('.') if f.endswith('.md') and f != 'README.md' and os.path.isfile(f)]
for file in md_files:
    try:
        shutil.move(file, 'docs/')
        print(f"Movido: {file}")
    except Exception as e:
        print(f"Error moviendo {file}: {e}")

# Mover archivos .txt de documentación
txt_files = ['COMANDOS_RAPIDOS.txt', 'INSTRUCCIONES_GIT.txt']
for file in txt_files:
    if os.path.exists(file):
        try:
            shutil.move(file, 'docs/')
            print(f"Movido: {file}")
        except Exception as e:
            print(f"Error moviendo {file}: {e}")

print("\n¡Organización completada!")
