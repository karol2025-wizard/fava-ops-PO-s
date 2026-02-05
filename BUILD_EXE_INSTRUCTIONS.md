# Instrucciones para Generar el Ejecutable .exe

Este documento explica cómo generar un archivo `.exe` del módulo `mo_and_recipes.py` para ejecutarlo en otra PC.

## Requisitos Previos

1. **Python instalado** (versión 3.8 o superior)
2. **Todas las dependencias instaladas** (ejecutar `pip install -r requirements.txt`)
3. **PyInstaller** (se instalará automáticamente si no está presente)

## Pasos para Generar el .exe

### Opción 1: Usar el Script Automático (Recomendado)

1. Abre una terminal/PowerShell en el directorio del proyecto
2. Ejecuta:
   ```bash
   build_exe.bat
   ```

El script automáticamente:
- Instalará PyInstaller si no está presente
- Limpiará builds anteriores
- Generará el ejecutable
- Te mostrará dónde encontrar el resultado

### Opción 2: Manual

1. Instala PyInstaller:
   ```bash
   pip install pyinstaller
   ```

2. Genera el ejecutable:
   ```bash
   pyinstaller mo_and_recipes.spec --clean
   ```

3. El ejecutable estará en la carpeta `dist/mo_and_recipes.exe`

## Uso del Ejecutable en Otra PC

### Archivos Necesarios

Para que el `.exe` funcione en otra PC, necesitas copiar:

1. **El ejecutable**: `dist/mo_and_recipes.exe`
2. **La carpeta completa** `dist/mo_and_recipes/` (si PyInstaller la crea)
3. **Archivos de configuración**:
   - `.streamlit/secrets.toml` (con las credenciales necesarias)
   - `credentials/` (carpeta con archivos JSON de credenciales de Google)
   - `config.py` (si es necesario)

### Estructura Recomendada en la PC Destino

```
C:\ruta\a\aplicacion\
├── mo_and_recipes.exe
├── .streamlit\
│   └── secrets.toml
├── credentials\
│   └── [archivos JSON de credenciales]
└── config.py (si es necesario)
```

### Configuración en la PC Destino

1. **Credenciales de Google**: 
   - Copia la carpeta `credentials/` con los archivos JSON necesarios
   - Asegúrate de que la ruta en `secrets.toml` apunte correctamente

2. **Archivo secrets.toml**:
   - Copia el archivo `.streamlit/secrets.toml`
   - Ajusta las rutas si es necesario (especialmente las rutas a archivos de credenciales)

3. **Primera Ejecución**:
   - Ejecuta `mo_and_recipes.exe`
   - La aplicación se abrirá automáticamente en tu navegador en `http://localhost:8501`
   - Si no se abre automáticamente, abre manualmente el navegador y ve a esa URL

## Solución de Problemas

### Error: "No module named 'X'"

Si aparece un error de módulo faltante:
1. Edita `mo_and_recipes.spec`
2. Agrega el módulo faltante en la lista `hiddenimports`
3. Vuelve a ejecutar `build_exe.bat`

### Error: "File not found" o problemas con rutas

- Asegúrate de que todos los archivos necesarios estén en la misma carpeta que el `.exe`
- Verifica que las rutas en `secrets.toml` sean relativas o absolutas correctas

### La aplicación no se abre en el navegador

- Abre manualmente tu navegador
- Ve a `http://localhost:8501`
- Si el puerto está ocupado, el ejecutable intentará usar otro puerto (8502, 8503, etc.)

### Error de credenciales

- Verifica que el archivo `secrets.toml` esté presente
- Verifica que las rutas a los archivos de credenciales sean correctas
- Asegúrate de que los archivos JSON de credenciales estén presentes

## Notas Importantes

1. **Tamaño del ejecutable**: El `.exe` puede ser grande (100-200 MB) porque incluye Python y todas las dependencias

2. **Antivirus**: Algunos antivirus pueden marcar el `.exe` como sospechoso. Esto es normal con PyInstaller. Puedes agregar una excepción si es necesario.

3. **Primera ejecución**: La primera vez que ejecutes el `.exe` puede tardar unos segundos en iniciar

4. **Puerto**: La aplicación usa el puerto 8501 por defecto. Si está ocupado, Streamlit intentará usar otro puerto

5. **Cerrar la aplicación**: Para cerrar, presiona `Ctrl+C` en la ventana de consola o cierra la ventana

## Alternativa: Ejecutable con Todos los Archivos Incluidos

Si prefieres un único archivo `.exe` (más grande pero más fácil de distribuir), puedes modificar `mo_and_recipes.spec` y cambiar:

```python
exe = EXE(
    ...
    console=True,
    onefile=True,  # Agregar esta línea
    ...
)
```

Luego ejecuta `build_exe.bat` nuevamente.
