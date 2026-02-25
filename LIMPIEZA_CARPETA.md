# Limpieza de carpeta – qué afecta al cierre de MO (MO Record Insert + Playwright)

## ✅ Necesarios para el flujo "cerrar y cambiar status"

- **home.py** – entrada de la app con menú (incluye MO Record Insert).
- **run_app_mo_record.bat** – inicia Streamlit con `home.py` en el puerto 8504.
- **Abrir app MO Record.vbs** – abre la app ejecutando el .bat anterior.
- **config.py** – carga de secrets (se usa desde las páginas).
- **pages/mo_record_insert.py** – página MO Record Insert.
- **shared/** – módulos del flujo (mo_update, mrpeasy_playwright_close, production_workflow, api_manager, mo_lookup, etc.).
- **.streamlit/secrets.toml** – credenciales y configuración (MRPeasy, Playwright, etc.).
- **.gitignore** – control de versión.
- **requirements.txt** (y venv) – dependencias.

---

## 🗑️ Se pueden eliminar o mover (no afectan al cierre de MO)

| Archivo | Motivo |
|--------|--------|
| **git_commit_message.txt** | Solo nota de commit; no lo usa la app. |
| **ACLARACION_CARPETAS.zip** | Archivo de aclaraciones; si ya no lo necesitas, bórralo. |
| **backup-fava-ops-2025-12-03_22-09-11.zip** | Backup antiguo; muévelo a una carpeta tipo `Backups` fuera del proyecto o bórralo si tienes otro respaldo. |

---

## ⚠️ Opcionales (otro modo de uso de la app)

Si **solo** usas **MO Record Insert** (cerrar MO + Playwright) y no usas la pantalla “solo MO and Recipes” en otra PC/puerto:

| Archivo | Uso |
|--------|-----|
| **mo_only.py** | Entrada que muestra solo “MO and Recipes” (sin menú, puerto 8502). |
| **run_streamlit.bat** | Arranca `mo_only.py` (puerto 8502). |
| **run_streamlit.ps1** | Igual que el .bat pero en PowerShell. |

Si no usas ese modo, puedes borrar **mo_only.py**, **run_streamlit.bat** y **run_streamlit.ps1**.  
Si alguna vez usas “solo MO and Recipes” en otra máquina, déjalos.

---

## Resumen rápido

- **Para limpiar sin riesgo:** borra o mueve `git_commit_message.txt`, `ACLARACION_CARPETAS.zip` y el backup zip.
- **Para limpiar más:** si no usas “solo MO and Recipes”, borra también `mo_only.py`, `run_streamlit.bat` y `run_streamlit.ps1`.
- **No borres:** `home.py`, `run_app_mo_record.bat`, `Abrir app MO Record.vbs`, `config.py`, carpeta `shared/`, `pages/`, `.streamlit/`, `requirements.txt`, `.gitignore`, ni el `venv`.
