# Integración de MORecordInsert.exe con MRPeasy

Esta guía explica cómo integrar `MORecordInsert.exe` con el sistema de actualización automática de MRPeasy.

## 📋 Resumen

Cuando el usuario hace clic en el botón **"Submit"** en MORecordInsert.exe, el sistema debe:

1. ✅ Buscar la Orden de Manufactura (MO) en MRPeasy usando el código de lote
2. ✅ Actualizar la cantidad real producida en MRPeasy
3. ✅ Cambiar el estado a "Done" (20)
4. ✅ Cerrar automáticamente la orden de manufactura

## 🔧 Implementación

### Opción 1: Llamar al script Python desde MORecordInsert.exe (Recomendado)

Si MORecordInsert.exe puede ejecutar scripts externos, llama al script `process_single_lot.py` después de hacer clic en Submit.

#### Ejemplo de código (si MORecordInsert.exe es Python):

```python
import subprocess
import sys
import os

def on_submit_button_click(lot_code, quantity, uom=None):
    """
    Esta función se llama cuando el usuario hace clic en Submit
    """
    # Ruta al script
    script_path = r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\process_single_lot.py"
    
    # Construir comando
    cmd = [sys.executable, script_path, lot_code, str(quantity)]
    if uom:
        cmd.append(uom)
    
    try:
        # Ejecutar el script
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=60  # Timeout de 60 segundos
        )
        
        # Verificar resultado
        if result.returncode == 0:
            print("✅ SUCCESS:", result.stdout)
            # Mostrar mensaje de éxito al usuario
            show_success_message("Orden actualizada y cerrada en MRPeasy")
        else:
            print("❌ ERROR:", result.stderr)
            # Mostrar mensaje de error al usuario
            show_error_message(f"Error: {result.stderr}")
            
    except subprocess.TimeoutExpired:
        show_error_message("Timeout: La operación tardó demasiado")
    except Exception as e:
        show_error_message(f"Error al ejecutar script: {str(e)}")
```

#### Ejemplo de código (si MORecordInsert.exe es C# o .NET):

```csharp
using System;
using System.Diagnostics;

public void OnSubmitButtonClick(string lotCode, double quantity, string uom = null)
{
    // Ruta al script Python
    string scriptPath = @"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\process_single_lot.py";
    string pythonExe = @"C:\Python\python.exe"; // Ajustar según tu instalación
    
    // Construir comando
    string arguments = $"\"{scriptPath}\" \"{lotCode}\" \"{quantity}\"";
    if (!string.IsNullOrEmpty(uom))
    {
        arguments += $" \"{uom}\"";
    }
    
    try
    {
        ProcessStartInfo startInfo = new ProcessStartInfo
        {
            FileName = pythonExe,
            Arguments = arguments,
            UseShellExecute = false,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
            CreateNoWindow = true
        };
        
        using (Process process = Process.Start(startInfo))
        {
            string output = process.StandardOutput.ReadToEnd();
            string error = process.StandardError.ReadToEnd();
            process.WaitForExit(60000); // Timeout de 60 segundos
            
            if (process.ExitCode == 0)
            {
                MessageBox.Show($"✅ SUCCESS: {output}", "Éxito");
            }
            else
            {
                MessageBox.Show($"❌ ERROR: {error}", "Error");
            }
        }
    }
    catch (Exception ex)
    {
        MessageBox.Show($"Error al ejecutar script: {ex.Message}", "Error");
    }
}
```

### Opción 2: Integración directa con ProductionWorkflow

Si tienes acceso al código fuente de MORecordInsert.exe y puede importar módulos Python, puedes usar directamente `ProductionWorkflow`:

```python
import sys
import os

# Agregar ruta del proyecto
sys.path.append(r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's")

from shared.production_workflow import ProductionWorkflow

def on_submit_button_click(lot_code, quantity, uom=None):
    """
    Esta función se llama cuando el usuario hace clic en Submit
    """
    try:
        workflow = ProductionWorkflow()
        
        success, result_data, message = workflow.process_production_completion(
            lot_code=lot_code,
            produced_quantity=float(quantity),
            uom=uom,
            item_code=None
        )
        
        if success:
            print(f"✅ SUCCESS: {message}")
            show_success_message("Orden actualizada y cerrada en MRPeasy")
        else:
            print(f"❌ ERROR: {message}")
            show_error_message(f"Error: {message}")
            
    except Exception as e:
        error_msg = f"Error procesando lote: {str(e)}"
        print(f"❌ ERROR: {error_msg}")
        show_error_message(error_msg)
```

## 📝 Uso del Script desde Línea de Comandos

También puedes probar el script manualmente desde la línea de comandos:

```bash
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
python process_single_lot.py L28868 10.00 pcs
```

### Parámetros:

- `<lot_code>`: Código del lote (ej: L28868)
- `<quantity>`: Cantidad producida (ej: 10.00)
- `[uom]`: Unidad de medida (opcional, ej: pcs, tray, kg)

### Ejemplos:

```bash
# Con unidad de medida
python process_single_lot.py L28868 10.00 pcs

# Sin unidad de medida (se usará la del MO)
python process_single_lot.py L28868 10.00
```

## ✅ Qué hace el script automáticamente:

1. **Busca el MO**: Encuentra la Orden de Manufactura asociada al código de lote
2. **Actualiza cantidad**: Actualiza la cantidad real producida en MRPeasy
3. **Cambia estado**: Cambia el estado a "Done" (20)
4. **Cierra la orden**: Cierra automáticamente la orden de manufactura
5. **Genera resumen**: Crea un registro de producción con todos los detalles

## 🔍 Verificación

Para verificar que la integración funciona:

1. Abre MORecordInsert.exe
2. Ingresa un código de lote (ej: L28868)
3. Ingresa una cantidad (ej: 10.00)
4. Haz clic en "Submit"
5. Verifica que aparezca un mensaje de éxito
6. Verifica en MRPeasy que:
   - La cantidad real se actualizó
   - El estado cambió a "Done"
   - La orden está cerrada

## 🐛 Solución de Problemas

### Error: "No Manufacturing Order found with lot code"
- Verifica que el código de lote existe en MRPeasy
- Verifica que hay un MO asociado a ese lote

### Error: "Authentication failed (401)"
- Verifica que `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` estén configurados en `.streamlit/secrets.toml`

### Error: "Rate limit exceeded (429)"
- Espera 1-2 minutos y vuelve a intentar
- MRPeasy está limitando las solicitudes

### Error: "Connection error"
- Verifica tu conexión a internet
- Verifica que el servicio de MRPeasy esté disponible

## 📞 Soporte

Si tienes problemas con la integración, verifica:

1. Que Python esté instalado y en el PATH
2. Que todas las dependencias estén instaladas (`pip install -r requirements.txt`)
3. Que las credenciales de MRPeasy estén configuradas correctamente
4. Que el script `process_single_lot.py` funcione correctamente desde la línea de comandos

## 📚 Archivos Relacionados

- `process_single_lot.py` - Script principal para procesar un lote
- `shared/production_workflow.py` - Flujo completo de procesamiento
- `shared/mo_update.py` - Actualización y cierre de órdenes en MRPeasy
- `shared/mo_lookup.py` - Búsqueda de órdenes por código de lote

