# Instrucciones para Habilitar Google Sheets API

## Problema
La Google Sheets API no está habilitada en tu proyecto de Google Cloud, lo que causa el error `PermissionError`.

## Solución

### Paso 1: Habilitar Google Sheets API

1. **Abre este enlace en tu navegador:**
   ```
   https://console.developers.google.com/apis/api/sheets.googleapis.com/overview?project=594969981919
   ```

2. **Haz clic en el botón "ENABLE" (Habilitar)**

3. **Espera unos minutos** para que los cambios se propaguen

### Paso 2: Habilitar Google Drive API (también requerida)

1. **Abre este enlace:**
   ```
   https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=594969981919
   ```

2. **Haz clic en el botón "ENABLE" (Habilitar)**

3. **Espera unos minutos** para que los cambios se propaguen

### Paso 3: Verificar

Después de habilitar las APIs, ejecuta:
```bash
python check_sheet_sharing.py
```

Deberías ver: `✅ Sheet abierto exitosamente`

## Nota Importante

- Necesitas tener permisos de administrador o editor en el proyecto de Google Cloud
- Si no tienes acceso, contacta al administrador del proyecto
- El proyecto ID es: `594969981919`

