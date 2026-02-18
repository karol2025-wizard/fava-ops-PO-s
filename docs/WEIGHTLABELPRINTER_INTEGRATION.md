# Integración con WeightLabelPrinter.spec

Este documento explica cómo integrar el sistema automático de procesamiento de MOs con WeightLabelPrinter.spec.

## Resumen

Cuando se ingresa la cantidad real producida en WeightLabelPrinter.spec para un LOT específico, el sistema automáticamente:

1. **Busca el MO asociado** usando el código LOT
2. **Actualiza el MO** con la cantidad real producida
3. **Cambia el estado** de "not booked" (0) a "Done" (20)
4. **Cierra la Orden de Manufactura**

## Opciones de Integración

### Opción 1: Integración mediante Base de Datos (Recomendada)

WeightLabelPrinter.spec inserta las entradas directamente en la tabla `erp_mo_to_import`:

```sql
INSERT INTO erp_mo_to_import (lot_code, quantity, uom, inserted_at)
VALUES ('L28553', 100.5, 'kg', NOW());
```

El sistema automático (`AutoMOProcessor`) monitorea esta tabla y procesa las entradas automáticamente.

**Campos requeridos:**
- `lot_code`: Código del LOT (ej: L28553)
- `quantity`: Cantidad real producida (debe ser > 0)
- `uom`: Unidad de medida (opcional, ej: kg, lb, gr)
- `inserted_at`: Timestamp de inserción (se puede usar NOW())

**Campos opcionales:**
- `user_operations`: Información adicional del usuario
- `item_code`: Código del item (se puede obtener automáticamente del LOT)

### Opción 2: Llamada Directa desde Python

Si WeightLabelPrinter.spec está escrito en Python, puedes llamar directamente a la función:

```python
import sys
import os

# Agregar el path del proyecto
sys.path.append('/ruta/al/proyecto')

from shared.auto_mo_processor import process_production_by_lot

# Cuando se ingresa la cantidad en WeightLabelPrinter.spec:
lot_code = "L28553"  # Obtenido del sistema
quantity = 100.5     # Cantidad ingresada por el usuario
uom = "kg"           # Unidad de medida

# Procesar automáticamente
success, message = process_production_by_lot(
    lot_code=lot_code,
    quantity=quantity,
    uom=uom
)

if success:
    print(f"✅ MO actualizado exitosamente: {message}")
else:
    print(f"❌ Error al actualizar MO: {message}")
```

### Opción 3: API REST (Si se implementa)

Si prefieres una integración mediante API REST, puedes crear un endpoint que llame a `process_production_by_lot()`.

## Uso de la Página de Streamlit

La página `auto_mo_processor.py` proporciona una interfaz para:

1. **Procesamiento Automático**: Activa el checkbox para procesar automáticamente nuevas entradas cada X segundos
2. **Procesamiento Manual**: Procesa todas las entradas pendientes con un solo clic
3. **Entrada Manual**: Permite procesar un LOT específico inmediatamente

### Acceso a la Página

```
http://localhost:8501/auto_mo_processor
```

O desde el menú de Streamlit, busca "Auto MO Processor".

## Flujo Completo

```
┌─────────────────────────┐
│ WeightLabelPrinter.spec │
│ Usuario ingresa cantidad│
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ Inserta en              │
│ erp_mo_to_import        │
│ (lot_code, quantity)    │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ AutoMOProcessor         │
│ Detecta nueva entrada   │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ ProductionWorkflow      │
│ 1. Busca MO por LOT     │
│ 2. Actualiza cantidad   │
│ 3. Cambia estado a Done │
│ 4. Cierra MO            │
└───────────┬─────────────┘
            │
            ▼
┌─────────────────────────┐
│ MRPEasy API             │
│ MO actualizado          │
│ Estado: Done (20)       │
└─────────────────────────┘
```

## Códigos de Estado MRPeasy

- **0**: Not Booked (Estado inicial cuando se crea el MO)
- **10**: In Progress (En progreso)
- **20**: Done (Completado - estado final)

El sistema cambia automáticamente de **0** (Not Booked) a **20** (Done) cuando se ingresa la cantidad real.

## Manejo de Errores

El sistema maneja los siguientes casos de error:

1. **LOT no encontrado**: Si no existe un MO asociado al LOT, se marca como fallido
2. **Múltiples MOs**: Si hay más de un MO con el mismo LOT, se requiere intervención manual
3. **Cantidad inválida**: Si la cantidad es 0 o negativa, se marca como fallido
4. **Error de API**: Si MRPeasy no responde, se reintenta automáticamente (hasta 3 veces)

Las entradas fallidas se marcan con `failed_code` en la base de datos y pueden ser revisadas en la página `erp_close_mo.py`.

## Logging

Todos los eventos se registran en los logs del sistema:

- **INFO**: Procesamiento exitoso
- **WARNING**: Advertencias (ej: múltiples MOs encontrados)
- **ERROR**: Errores que requieren atención

## Pruebas

Para probar el sistema:

1. Crea un MO en `mo_and_recipes.py` con un LOT específico
2. Inserta una entrada en `erp_mo_to_import` con ese LOT y una cantidad
3. Ejecuta el procesador automático o manual
4. Verifica en MRPeasy que el MO cambió a estado "Done"

## Soporte

Para problemas o preguntas sobre la integración, revisa:
- Logs del sistema
- Página `erp_close_mo.py` para entradas fallidas
- Documentación de `ProductionWorkflow` en `shared/production_workflow.py`
