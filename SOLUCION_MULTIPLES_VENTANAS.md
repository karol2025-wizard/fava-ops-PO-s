# Solución: Múltiples Ventanas y Command Prompt que se Cierra

## Problema
Cuando ejecutas `mo_and_recipes.exe`, se abren múltiples ventanas del navegador y el Command Prompt se cierra antes de poder ver los errores.

## Soluciones

### Solución 1: Usar el Script de Debug (RECOMENDADO)

En la carpeta `mo_and_recipes_completo`, ejecuta:

```
EJECUTAR_CON_DEBUG.bat
```

Este script:
- ✅ Verifica que todos los archivos estén presentes
- ✅ Mantiene la ventana de comandos abierta para ver errores
- ✅ Muestra mensajes claros sobre qué está pasando

### Solución 2: Verificar Archivos Primero

Antes de ejecutar, verifica que todo esté bien:

```
VERIFICAR_ARCHIVOS.bat
```

Este script te dirá exactamente qué archivos faltan.

### Solución 3: Ejecutar Manualmente con Python (Alternativa)

Si el .exe sigue dando problemas, puedes ejecutar directamente con Python:

1. **Instala Python 3.8+** si no lo tienes

2. **Instala las dependencias**:
   ```bash
   pip install streamlit pandas numpy pillow reportlab google-api-python-client gspread toml
   ```
   
   O si tienes `requirements.txt`:
   ```bash
   pip install -r requirements.txt
   ```

3. **Ejecuta directamente**:
   ```bash
   streamlit run pages\mo_and_recipes.py
   ```

### Solución 4: Prevenir Múltiples Ventanas

Si se abren múltiples ventanas del navegador:

1. **Cierra todas las ventanas del navegador** que se abrieron
2. **Cierra el Command Prompt** si está abierto
3. **Abre manualmente** una sola ventana en: `http://localhost:8501`
4. **Ejecuta de nuevo** `EJECUTAR_CON_DEBUG.bat`

## Errores Comunes

### Error: "No module named X"
**Causa**: Faltan dependencias de Python  
**Solución**: Usa la Solución 3 (ejecutar con Python) e instala las dependencias

### Error: "FileNotFoundError: secrets.toml"
**Causa**: Falta el archivo de configuración  
**Solución**: Asegúrate de copiar `.streamlit\secrets.toml`

### Error: "No se encuentra pages/mo_and_recipes.py"
**Causa**: La estructura de carpetas está mal  
**Solución**: Ejecuta `VERIFICAR_ARCHIVOS.bat` para ver qué falta

### Múltiples ventanas se abren
**Causa**: El script intenta abrir el navegador automáticamente varias veces  
**Solución**: 
- Cierra las ventanas extras
- Abre manualmente solo una: `http://localhost:8501`
- O usa la Solución 3 (Python directo) que no abre el navegador automáticamente

## Pasos Recomendados

1. **Primero**: Ejecuta `VERIFICAR_ARCHIVOS.bat` para asegurarte de que todo esté presente

2. **Segundo**: Ejecuta `EJECUTAR_CON_DEBUG.bat` para ver los errores

3. **Si hay errores**: 
   - Lee el mensaje de error en la ventana de comandos
   - Busca la solución en esta guía
   - O usa la Solución 3 (Python directo) como alternativa

4. **Si funciona pero se abren múltiples ventanas**:
   - Cierra las extras
   - Abre manualmente solo una: `http://localhost:8501`

## Notas Importantes

- **NO cierres la ventana de comandos** mientras la aplicación esté corriendo
- Si cierras la ventana de comandos, la aplicación se detendrá
- Para detener la aplicación, presiona `Ctrl+C` en la ventana de comandos
- El puerto 8501 puede cambiar si está ocupado (8502, 8503, etc.)
