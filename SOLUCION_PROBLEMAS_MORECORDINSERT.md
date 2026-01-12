# Solución de Problemas - MORecordInsert.exe

## 🔍 Problema: No aparece nada después de hacer clic en Submit

Si después de hacer clic en "Submit" en MORecordInsert.exe:
- ❌ No aparece nada en la interfaz de "MRP Easy - Manufacturing Order Processor"
- ❌ No se ven cambios en MRPeasy

Sigue estos pasos para diagnosticar y solucionar el problema:

## 📋 Pasos de Diagnóstico

### Paso 1: Verificar que MORecordInsert.exe está escribiendo a la base de datos

1. Abre la página "MRP Easy - Manufacturing Order Processor" en Streamlit
2. Haz clic en **"🔄 Fetch Orders from Database"**
3. Si aparecen órdenes pendientes, significa que MORecordInsert.exe SÍ está escribiendo a la base de datos
4. Si NO aparecen órdenes, el problema está en MORecordInsert.exe (no está escribiendo a la BD)

### Paso 2: Verificar que el script se puede ejecutar manualmente

Abre una terminal (PowerShell o CMD) y ejecuta:

```bash
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
python process_single_lot.py L28868 10.00 pcs
```

**Reemplaza `L28868` y `10.00 pcs` con valores reales de tu lote.**

#### Si el script funciona:
- Verás mensajes de éxito ✅
- La orden se actualizará en MRPeasy
- El problema es que MORecordInsert.exe no está llamando al script

#### Si el script NO funciona:
- Verás mensajes de error ❌
- Revisa el archivo `process_single_lot.log` para ver el error detallado
- Sigue con los pasos de solución de problemas abajo

### Paso 3: Verificar que MORecordInsert.exe está llamando al script

**Opción A: Si MORecordInsert.exe es Python:**

Verifica que el código tenga algo como esto cuando se hace clic en Submit:

```python
import subprocess
import sys

def on_submit_click(lot_code, quantity, uom):
    script_path = r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\process_single_lot.py"
    
    result = subprocess.run(
        [sys.executable, script_path, lot_code, str(quantity), uom],
        capture_output=True,
        text=True
    )
    
    if result.returncode == 0:
        print("✅ Éxito:", result.stdout)
    else:
        print("❌ Error:", result.stderr)
```

**Opción B: Si MORecordInsert.exe es C# o .NET:**

Verifica que tenga código similar para ejecutar el script Python.

### Paso 4: Verificar credenciales de MRPeasy

1. Abre el archivo `.streamlit/secrets.toml`
2. Verifica que existan estas líneas:

```toml
MRPEASY_API_KEY = "tu_api_key_aqui"
MRPEASY_API_SECRET = "tu_api_secret_aqui"
```

3. Si faltan o están incorrectas, el script no podrá conectarse a MRPeasy

## 🔧 Soluciones

### Solución 1: Procesar manualmente desde la interfaz

Si MORecordInsert.exe está escribiendo a la base de datos pero no procesa automáticamente:

1. Abre "MRP Easy - Manufacturing Order Processor"
2. Haz clic en **"🔄 Fetch Orders from Database"**
3. Selecciona las órdenes que quieres procesar
4. Haz clic en **"🚀 Process Selected Orders"**

### Solución 2: Ejecutar el script automáticamente después de insertar

Si MORecordInsert.exe escribe a la base de datos, puedes:

**Opción A: Usar el procesador automático**

Ejecuta en una terminal (y déjalo corriendo):

```bash
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
python auto_process_production.py --mode continuous --interval 10
```

Esto procesará automáticamente cualquier orden nueva cada 10 segundos.

**Opción B: Integrar el script en MORecordInsert.exe**

Modifica MORecordInsert.exe para que después de insertar en la base de datos, llame a:

```python
subprocess.run([
    "python",
    r"C:\Users\Operations - Fava\Desktop\code\fava ops PO's\process_single_lot.py",
    lot_code,
    str(quantity),
    uom
])
```

### Solución 3: Verificar errores en el log

1. Abre el archivo `process_single_lot.log` en la carpeta del proyecto
2. Busca los últimos errores
3. Los errores comunes son:

#### Error: "Authentication failed (401)"
- **Causa**: Credenciales de MRPeasy incorrectas
- **Solución**: Verifica `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` en `.streamlit/secrets.toml`

#### Error: "No Manufacturing Order found with lot code"
- **Causa**: El código de lote no existe en MRPeasy o no tiene un MO asociado
- **Solución**: Verifica en MRPeasy que el lote existe y tiene un MO

#### Error: "Rate limit exceeded (429)"
- **Causa**: Demasiadas solicitudes a MRPeasy
- **Solución**: Espera 1-2 minutos y vuelve a intentar

#### Error: "Connection error"
- **Causa**: Problema de conexión a internet o MRPeasy está caído
- **Solución**: Verifica tu conexión a internet

## 📝 Verificación Final

Para verificar que todo funciona:

1. **Ejecuta el script manualmente:**
   ```bash
   python process_single_lot.py L28868 10.00 pcs
   ```

2. **Verifica en MRPeasy:**
   - Abre MRPeasy en tu navegador
   - Busca el MO asociado al lote
   - Verifica que:
     - ✅ La cantidad real se actualizó
     - ✅ El estado cambió a "Done"
     - ✅ La orden está cerrada

3. **Verifica en la interfaz:**
   - Abre "MRP Easy - Manufacturing Order Processor"
   - Haz clic en "🔄 Fetch Orders from Database"
   - Si procesaste manualmente, la orden debería aparecer como procesada

## 🆘 Si nada funciona

1. **Revisa el log completo:**
   - Abre `process_single_lot.log`
   - Copia los últimos errores
   - Compártelos para diagnóstico

2. **Prueba la conexión a MRPeasy:**
   ```bash
   python test_mrpeasy_connection.py
   ```

3. **Verifica que Python y las dependencias estén instaladas:**
   ```bash
   python --version
   pip install -r requirements.txt
   ```

## 📞 Archivos de Ayuda

- `process_single_lot.py` - Script principal
- `process_single_lot.log` - Log de errores y operaciones
- `INTEGRACION_MORECORDINSERT.md` - Guía de integración completa
- `test_process_lot.py` - Script de prueba

