# Guía para Vincular el Proyecto con GitHub

## ✅ Verificación de Seguridad

Antes de proceder, verifica que los siguientes archivos estén en `.gitignore`:

- ✅ `.streamlit/secrets.toml` - **EXCLUIDO**
- ✅ `credentials/` - **EXCLUIDO**
- ✅ `*.json` - **EXCLUIDO** (excepto package.json)
- ✅ `test_gfs_config.py` - **EXCLUIDO**

## 🚀 Pasos para Vincular con GitHub

### Opción 1: Usando Git Bash o Terminal

Abre Git Bash o tu terminal preferida y ejecuta los siguientes comandos:

```bash
# 1. Navega al directorio del proyecto
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"

# 2. Inicializa el repositorio Git (si no está inicializado)
git init

# 3. Verifica que .gitignore esté presente
git status

# 4. Agrega todos los archivos (los sensibles serán ignorados automáticamente)
git add .

# 5. Verifica qué archivos se van a commitear (debe NO incluir secrets.toml ni credentials/)
git status

# 6. Si ves archivos sensibles en el staging, detén el proceso y revisa .gitignore

# 7. Haz el primer commit
git commit -m "Initial commit: Fava Operations PO's system"

# 8. Agrega el remote de GitHub
git remote add origin https://github.com/karol2025-wizard/fava-ops-PO-s.git

# 9. Verifica el remote
git remote -v

# 10. Cambia a la rama main (si es necesario)
git branch -M main

# 11. Push al repositorio
git push -u origin main
```

### Opción 2: Usando GitHub Desktop

1. Abre GitHub Desktop
2. File → Add Local Repository
3. Selecciona la carpeta del proyecto
4. Verifica que `.gitignore` esté funcionando (no debe mostrar secrets.toml ni credentials/)
5. Haz commit con el mensaje "Initial commit"
6. Publica el repositorio en GitHub

## ⚠️ Verificación Final ANTES de Push

**IMPORTANTE:** Antes de hacer push, verifica que NO se vayan a subir archivos sensibles:

```bash
git status
```

Debes ver:
- ❌ NO debe aparecer `secrets.toml`
- ❌ NO debe aparecer `credentials/` o archivos `.json` de credenciales
- ✅ Debe aparecer `README.md`, `.gitignore`, y archivos de código

Si ves archivos sensibles, **DETÉN EL PROCESO** y revisa `.gitignore`.

## 🔒 Si Ya Commiteaste Archivos Sensibles (Accidente)

Si accidentalmente commiteaste archivos sensibles, ejecuta:

```bash
# Remover del historial (CUIDADO: esto reescribe el historial)
git rm --cached .streamlit/secrets.toml
git rm --cached credentials/*.json
git commit -m "Remove sensitive files from git"

# Si ya hiciste push, necesitarás forzar el push (solo si es necesario)
# git push --force
```

## 📝 Notas

- El archivo `secrets.toml` debe estar en `.gitignore` y NO debe ser commiteado
- Las credenciales JSON deben estar en `credentials/` y NO deben ser commiteadas
- Si necesitas compartir la configuración, crea un archivo `secrets.toml.example` con valores de ejemplo


