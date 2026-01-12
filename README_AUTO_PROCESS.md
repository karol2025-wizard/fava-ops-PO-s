# Procesamiento Automático de Producción

Este sistema procesa automáticamente las entradas de producción desde `WeightLabelPrinter.exe` y actualiza MRPeasy con las cantidades reales y el estado.

## Archivos

1. **`auto_process_production.py`** - Script principal para procesamiento automático
2. **`process_single_lot.py`** - Script para procesar un solo lot inmediatamente

## Opciones de Implementación

### Opción 1: Procesamiento Automático Continuo (Recomendado)

Ejecuta un servicio que monitorea la base de datos continuamente:

```bash
# Procesar una vez y salir
python auto_process_production.py --mode once --limit 10

# Modo continuo (monitorea cada 30 segundos)
python auto_process_production.py --mode continuous --interval 30
```

**Ventajas:**
- No requiere modificar WeightLabelPrinter.exe
- Procesa automáticamente todas las entradas nuevas
- Se puede ejecutar como servicio de Windows

**Configuración como Servicio de Windows:**
1. Crear un archivo `.bat`:
```batch
@echo off
cd /d "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
python auto_process_production.py --mode continuous --interval 30
```

2. Usar NSSM (Non-Sucking Service Manager) o Task Scheduler para ejecutarlo como servicio

### Opción 2: Procesamiento Inmediato desde WeightLabelPrinter.exe

Si WeightLabelPrinter.exe puede ejecutar scripts externos, agregar esta llamada después de insertar en la base de datos:

```python
# Desde WeightLabelPrinter.exe (si es Python) o como proceso externo
import subprocess
subprocess.run([
    "python", 
    "process_single_lot.py", 
    lot_code, 
    str(quantity), 
    uom
])
```

O desde línea de comandos:
```bash
python process_single_lot.py L28718 2.00 tray
```

**Ventajas:**
- Procesamiento inmediato
- No requiere servicio continuo

**Desventajas:**
- Requiere modificar WeightLabelPrinter.exe o agregar hook

### Opción 3: Trigger de Base de Datos (Avanzado)

Si la base de datos soporta triggers, crear un trigger que ejecute el script cuando se inserte una nueva fila.

## Flujo de Trabajo

1. **Trabajador ingresa LOT en WeightLabelPrinter.exe**
   - Se inserta en tabla `erp_mo_to_import`:
     - `lot_code` (ej: L28718)
     - `quantity` (cantidad real)
     - `uom` (unidad)
     - `inserted_at` (timestamp)
     - `processed_at` = NULL (pendiente)

2. **Sistema automático detecta nueva entrada**
   - `auto_process_production.py` encuentra la entrada
   - Llama a `ProductionWorkflow.process_production_completion()`

3. **ProductionWorkflow procesa:**
   - Busca MO por Lot Code en MRPeasy
   - Actualiza cantidad real (`actual_quantity`)
   - Cambia estado a "Done" (20)
   - Genera resumen de producción
   - Marca entrada como procesada (`processed_at` = ahora)

4. **Resultado:**
   - MRPeasy actualizado automáticamente
   - Estado cambiado a "Done"
   - Resumen disponible para impresión

## Logs

Los logs se guardan en:
- `production_auto_process.log` - Log del procesamiento automático
- Consola - Salida en tiempo real

## Monitoreo

Para verificar que está funcionando:

```bash
# Ver últimas líneas del log
tail -f production_auto_process.log

# Ver entradas pendientes en la base de datos
# (Desde la página Streamlit "MRP Easy - Manufacturing Order Processor")
```

## Solución de Problemas

### Las entradas no se procesan automáticamente

1. Verificar que el script está ejecutándose:
   ```bash
   python auto_process_production.py --mode once
   ```

2. Verificar logs:
   ```bash
   cat production_auto_process.log
   ```

3. Verificar base de datos:
   - Entradas con `processed_at IS NULL`
   - Sin `failed_code`

### Error: "No Manufacturing Order found with lot code"

- Verificar que el Lot Code existe en MRPeasy
- Verificar que la MO tiene el Lot Code en `target_lots`

### Error: "Multiple Manufacturing Orders found"

- Contactar supervisor - hay múltiples MOs con el mismo Lot Code
- Requiere intervención manual

## Configuración Recomendada

**Para producción:**
- Ejecutar `auto_process_production.py` en modo continuo
- Configurar como servicio de Windows
- Intervalo de 30 segundos (ajustable según volumen)

**Para desarrollo/pruebas:**
- Ejecutar manualmente: `python auto_process_production.py --mode once`
- Verificar resultados en la página Streamlit

