# 🚀 Implementación Más Fácil - WeightLabelPrinter.spec / MO Record Insert

## 📋 Flujo con MO Record Insert (tú ingresas LOT + cantidad del sticker)

Después de que producción pone la cantidad real y se genera el sticker:
1. Tú tomas ese papel y ingresas el **LOT** y la **cantidad que dice el sticker**.
2. Eso lo haces en **MORecordInsert.exe** (o en la página equivalente en Streamlit).
3. Al registrar, el sistema debe ir a MRPEasy y cambiar **"Not scheduled"** → **"Done"**.

### Opción A: Usar la página "MO Record Insert" (recomendado, ya está lista)

1. Abre Streamlit y entra a la página **"MO Record Insert"**.
2. Ingresa **LOT Number** y **Cantidad del sticker** (y opcionalmente la unidad).
3. Clic en **"Registrar y actualizar MRPEasy → Done"**.
4. El sistema actualiza el MO en MRPEasy a **Done** con esa cantidad.

No necesitas MORecordInsert.exe: esta página hace el mismo proceso integrado con MRPEasy.

### Opción B: Conectar MORecordInsert.exe para que actualice MRPEasy

Si quieres seguir usando MORecordInsert.exe, tiene que disparar el mismo proceso al guardar:

- **Si MORecordInsert.exe puede ejecutar Python:** que al guardar ejecute algo como:
  ```bat
  python -c "import sys; sys.path.append(r'C:\Users\Operations - Fava\Desktop\code\fava ops PO''s'); from shared.auto_mo_processor import process_production_by_lot; ok, msg = process_production_by_lot('LOT_AQUI', CANTIDAD_AQUI, 'uom'); print(msg)"
  ```
  (sustituyendo LOT_AQUI, CANTIDAD_AQUI y 'uom' por los valores que el usuario ingresó).

- **Si MORecordInsert.exe escribe a una base de datos:** que inserte en la tabla `erp_mo_to_import` los campos `lot_code`, `quantity`, `uom`. Luego activa el **procesamiento automático** en la página "Auto MO Processor" para que esas filas se procesen y los MOs pasen a Done.

---

## ⭐ Opción Recomendada (WeightLabelPrinter): Base de Datos (MÁS FÁCIL)

Esta es la opción **más fácil y efectiva** porque:
- ✅ Solo necesitas agregar **1 línea de código**
- ✅ No necesitas modificar mucho tu código existente
- ✅ El procesamiento es automático y desacoplado
- ✅ Ya está todo listo para funcionar

## 📝 Cómo Implementar (3 pasos simples)

### Paso 1: Importar la función helper

En tu archivo WeightLabelPrinter.spec (o donde captures la cantidad), agrega:

```python
import sys
import os

# Agregar el path del proyecto (ajusta la ruta según tu estructura)
sys.path.append('C:/Users/Operations - Fava/Desktop/code/fava ops PO\'s')

from shared.weightlabelprinter_helper import insert_production_quantity
```

### Paso 2: Llamar la función cuando se ingresa la cantidad

Cuando el usuario ingresa la cantidad real producida en WeightLabelPrinter.spec:

```python
# Ejemplo: cuando el usuario confirma la cantidad
lot_code = "L28553"  # El LOT que están usando
cantidad_real = 100.5  # La cantidad que ingresaron
unidad = "kg"  # La unidad de medida

# Insertar en el sistema (esto es TODO lo que necesitas hacer)
if insert_production_quantity(lot_code, cantidad_real, unidad):
    print("✅ Cantidad registrada. El MO se actualizará automáticamente.")
    # El sistema automáticamente:
    # 1. Buscará el MO asociado al LOT
    # 2. Actualizará con la cantidad real
    # 3. Cambiará el estado a "Done"
    # 4. Cerrará el MO
else:
    print("❌ Error al registrar la cantidad.")
```

### Paso 3: Activar el procesamiento automático (una sola vez)

1. Abre la aplicación Streamlit
2. Ve a la página **"Auto MO Processor"**
3. Activa el checkbox **"Procesamiento Automático"**
4. ¡Listo! El sistema procesará automáticamente todas las nuevas entradas

## 🎯 Ejemplo Completo

```python
# En WeightLabelPrinter.spec

import sys
import os
sys.path.append('C:/Users/Operations - Fava/Desktop/code/fava ops PO\'s')
from shared.weightlabelprinter_helper import insert_production_quantity

def cuando_usuario_ingresa_cantidad():
    """Esta función se llama cuando el usuario ingresa la cantidad real"""
    
    # Obtener datos del sistema
    lot_code = obtener_lot_code()  # Tu función para obtener el LOT
    cantidad = obtener_cantidad()  # La cantidad ingresada por el usuario
    unidad = obtener_unidad()  # La unidad de medida
    
    # Insertar en el sistema (UNA SOLA LÍNEA)
    insert_production_quantity(lot_code, cantidad, unidad)
    
    # El resto del código de WeightLabelPrinter.spec continúa normalmente
    # El MO se actualizará automáticamente en segundo plano
```

## 🔄 ¿Cómo Funciona?

```
WeightLabelPrinter.spec
    ↓ (llama insert_production_quantity)
Base de Datos (erp_mo_to_import)
    ↓ (detectado automáticamente)
AutoMOProcessor
    ↓ (procesa automáticamente)
ProductionWorkflow
    ↓ (busca MO por LOT)
MRPEasy API
    ↓ (actualiza MO)
✅ MO cerrado con estado "Done"
```

## ⚡ Alternativa: Procesamiento Inmediato

Si prefieres que el MO se actualice **inmediatamente** sin usar la base de datos:

```python
from shared.weightlabelprinter_helper import process_production_immediately

success, message = process_production_immediately("L28553", 100.5, "kg")
if success:
    print(f"✅ {message}")
else:
    print(f"❌ {message}")
```

**Ventajas:**
- ✅ Procesamiento inmediato
- ✅ No necesita base de datos intermedia

**Desventajas:**
- ⚠️ Si falla, no hay registro para reintentar
- ⚠️ Más acoplado al sistema

## 📊 Monitoreo

Puedes ver el estado del procesamiento en:
- **Página Streamlit**: "Auto MO Processor" - muestra estadísticas y actividad reciente
- **Página Streamlit**: "ERP Close MO" - muestra entradas pendientes y fallidas

## 🛠️ Troubleshooting

### Error: "Module not found"
- Verifica que la ruta en `sys.path.append()` sea correcta
- Asegúrate de que el proyecto esté en esa ubicación

### Error: "Lot code is required"
- Verifica que estés pasando el `lot_code` correctamente
- Asegúrate de que no sea None o vacío

### El MO no se actualiza
- Verifica que el procesamiento automático esté activado en Streamlit
- Revisa los logs para ver si hay errores
- Verifica que el LOT exista en MRPEasy y esté asociado a un MO

## ✅ Resumen

**Para implementar, solo necesitas:**

1. **Importar** la función helper (1 línea)
2. **Llamar** `insert_production_quantity()` cuando se ingresa la cantidad (1 línea)
3. **Activar** el procesamiento automático en Streamlit (1 clic)

**Total: 2 líneas de código + 1 clic** 🎉
