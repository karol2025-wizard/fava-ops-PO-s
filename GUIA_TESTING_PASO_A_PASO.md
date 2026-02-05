# 🧪 Guía Paso a Paso - Testing en Otro Computador

Guía detallada para testear `mo_and_recipes.py` optimizado en un computador nuevo.

---

## 📋 PASO 1: Preparar el Computador

### 1.1 Verificar Python
```bash
# Abre PowerShell o Terminal
python --version
# Debe mostrar Python 3.8 o superior
```

**Si no tienes Python:**
- Descarga desde: https://www.python.org/downloads/
- Durante instalación, marca ✅ "Add Python to PATH"

### 1.2 Verificar pip
```bash
pip --version
# Debe mostrar pip instalado
```

---

## 📦 PASO 2: Obtener el Código

### Opción A: Desde Git (Recomendado)
```bash
# Clonar el repositorio
git clone [URL_DEL_REPOSITORIO]
cd "fava ops PO's"
```

### Opción B: Copiar Archivos Manualmente
1. Copia toda la carpeta del proyecto
2. Asegúrate de incluir:
   - ✅ `pages/mo_and_recipes.py`
   - ✅ `shared/` (toda la carpeta)
   - ✅ `requirements.txt`
   - ✅ `.streamlit/` (si existe)

---

## 🔧 PASO 3: Instalar Dependencias

### 3.1 Crear Entorno Virtual (Recomendado)
```bash
# Crear entorno virtual
python -m venv venv

# Activar entorno virtual
# Windows PowerShell:
.\venv\Scripts\Activate.ps1

# Windows CMD:
venv\Scripts\activate.bat

# Linux/Mac:
source venv/bin/activate
```

### 3.2 Instalar Paquetes
```bash
# Instalar todas las dependencias
pip install -r requirements.txt
```

**Tiempo estimado**: 2-5 minutos

### 3.3 Verificar Instalación
```bash
# Verificar Streamlit
streamlit --version

# Verificar paquetes clave
pip list | findstr "streamlit reportlab PyPDF2"
```

---

## ⚙️ PASO 4: Configurar Secrets

### 4.1 Crear Carpeta .streamlit
```bash
# Crear carpeta si no existe
mkdir .streamlit
```

### 4.2 Crear Archivo secrets.toml
Crea el archivo `.streamlit/secrets.toml` con este contenido:

```toml
# MRPeasy API (REQUERIDO para crear MOs)
MRPEASY_API_KEY = "tu_api_key_aqui"
MRPEASY_API_SECRET = "tu_api_secret_aqui"

# Google Credentials (OPCIONAL - solo para ver recetas)
GOOGLE_CREDENTIALS_PATH = "credentials/tu-archivo.json"
```

**⚠️ IMPORTANTE:**
- Reemplaza `tu_api_key_aqui` con tu API key real de MRPeasy
- Reemplaza `tu_api_secret_aqui` con tu API secret real
- Si no tienes Google credentials, puedes omitir esa línea

### 4.3 Verificar Credenciales
```bash
# Verificar que el archivo existe
dir .streamlit\secrets.toml
# O en Linux/Mac:
ls .streamlit/secrets.toml
```

---

## 🚀 PASO 5: Ejecutar la Aplicación

### 5.1 Iniciar Streamlit
```bash
# Desde la raíz del proyecto
streamlit run pages/mo_and_recipes.py
```

**O usar el script incluido:**
```bash
# Windows
.\run_streamlit.bat

# Linux/Mac
./run_streamlit.ps1
```

### 5.2 Verificar que Funciona
1. Se abrirá automáticamente en el navegador (normalmente http://localhost:8501)
2. Deberías ver el título "🏭📋 MO and Recipes"
3. Si ves errores, revisa la consola donde ejecutaste el comando

---

## ✅ PASO 6: Testing - Verificar Caché

### Test 1: Verificar Caché de Items
1. **Abre la aplicación** en el navegador
2. **Mira el sidebar** (panel izquierdo)
3. **Busca el mensaje**: "Items cache initialized"
4. **Verifica** que muestra el número de items cargados

**✅ Éxito si ves:**
```
Items cache initialized with X items
Units cache initialized with Y units
```

**❌ Si hay error:**
- Verifica que `MRPEASY_API_KEY` y `MRPEASY_API_SECRET` están correctos
- Revisa la consola para ver el error específico

---

## ✅ PASO 7: Testing - Crear MO (Single)

### Test 2: Crear MO Individual
1. **Selecciona acción**: Click en "🏭 Generate MO"
2. **Selecciona categoría**: Elige cualquier categoría (ej: "Bases & Preparations")
3. **Selecciona item**: Elige cualquier item de la lista
4. **Ingresa cantidad**: Escribe un número (ej: 1.0)
5. **Crea el MO**: Click en "🚀 Create Manufacturing Order"

**✅ Éxito si:**
- Aparece mensaje: "✅ Manufacturing Order created successfully!"
- Se muestra el MO ID
- Se genera el PDF de routing

**🔍 Verificar en consola:**
- Busca el mensaje: "Using cached article_id" (esto confirma la optimización)

---

## ✅ PASO 8: Testing - Crear MO (Batch)

### Test 3: Crear MO en Batch
1. **Selecciona acción**: Click en "🏭 Generate MO"
2. **Selecciona categoría**: Elige una categoría
3. **Selecciona item**: Elige un item (esto auto-completa el código)
4. **Ve a tab "⚡ Batch Creation"**
5. **Completa el formulario**:
   - Item Code: (debería estar auto-completado)
   - Expected Output: 1.0
   - Start Date: MM/DD/YYYY (ej: 01/15/2025)
6. **Crea el MO**: Click en "🚀 Create Manufacturing Order"

**✅ Éxito si:**
- Aparece mensaje de éxito
- Se muestra el MO ID

**🔍 Verificar optimización en consola:**
Busca este mensaje:
```
Performance: Using cached article_id for A1234 (saved 1 API call)
```

**Esto confirma que:**
- ✅ Se usó el caché (0 API calls)
- ✅ La optimización funciona

---

## ✅ PASO 9: Testing - Ver Recetas

### Test 4: Ver Receta
1. **Selecciona acción**: Click en "📋 Print Recipe"
2. **Selecciona categoría**: Elige una categoría
3. **Selecciona item**: Elige un item
4. **Verifica**: Debe mostrar la receta

**✅ Éxito si:**
- Se muestra la receta desde Google Docs o ZIP
- Puedes descargar el PDF

**❌ Si no funciona:**
- Verifica que `GOOGLE_CREDENTIALS_PATH` está configurado (opcional)
- O que existe `recipes_split/recipespdf.zip` (opcional)

---

## 📊 PASO 10: Verificar Optimizaciones

### 10.1 Revisar Logs de Performance

**En la consola donde ejecutaste Streamlit, busca:**

✅ **Optimización aplicada:**
```
INFO: Performance: Using cached article_id for A1234 (saved 1 API call)
```

⚠️ **Fallback a API** (normal si item no está en caché):
```
WARNING: Item A1234 not found in cache, falling back to API lookup (1 API call required)
```

### 10.2 Comparar Performance

**Antes de optimización:**
- Cada MO creation = 1 API call
- 10 MOs = 10 API calls

**Después de optimización:**
- Cada MO creation = 0 API calls (usa caché)
- 10 MOs = 0 API calls

**Verifica esto:**
1. Crea varios MOs en batch
2. Revisa los logs
3. Deberías ver "saved 1 API call" para cada uno

---

## 🐛 PASO 11: Troubleshooting

### Error: "MRPEASY_API_KEY not found"
**Solución:**
1. Verifica que `.streamlit/secrets.toml` existe
2. Verifica que tiene `MRPEASY_API_KEY` y `MRPEASY_API_SECRET`
3. Reinicia Streamlit después de cambiar secrets

### Error: "Module not found"
**Solución:**
```bash
# Reinstalar dependencias
pip install -r requirements.txt
```

### Error: "Item not found in cache"
**Solución:**
1. Click en "🔄 Refresh Data" en la página
2. Espera a que cargue el caché
3. Intenta de nuevo

### La aplicación no abre en el navegador
**Solución:**
1. Copia la URL que aparece en la consola (ej: http://localhost:8501)
2. Pégala manualmente en el navegador

### Error de permisos en Windows
**Solución:**
```powershell
# Ejecutar PowerShell como Administrador
Set-ExecutionPolicy -ExecutionPolicy RemoteSigned -Scope CurrentUser
```

---

## 📝 PASO 12: Checklist Final

Antes de considerar el testing completo, verifica:

- [ ] ✅ La aplicación inicia sin errores
- [ ] ✅ El caché se carga correctamente (sidebar muestra items)
- [ ] ✅ Puedes crear MO individual
- [ ] ✅ Puedes crear MO en batch
- [ ] ✅ Los logs muestran "Performance: Using cached article_id"
- [ ] ✅ Puedes ver recetas (si Google credentials configurado)
- [ ] ✅ No hay errores en la consola

---

## 🎯 Resultados Esperados

### ✅ Testing Exitoso

Si todo funciona correctamente, deberías ver:

1. **Performance Optimizada:**
   - Logs muestran "saved 1 API call" para cada MO
   - Caché funciona correctamente
   - No hay llamadas API innecesarias

2. **Funcionalidad Completa:**
   - Creación de MO funciona (single y batch)
   - Visualización de recetas funciona
   - PDFs se generan correctamente

3. **Sin Errores:**
   - No hay errores en consola
   - No hay errores en la interfaz
   - Todo funciona como esperado

---

## 📞 Soporte

Si encuentras problemas:

1. **Revisa los logs** en la consola
2. **Verifica la configuración** en `.streamlit/secrets.toml`
3. **Consulta** `SETUP_MO_AND_RECIPES.md` para más detalles
4. **Revisa** `CHANGELOG_MO_AND_RECIPES.md` para cambios

---

**¡Listo para testear! 🚀**

Sigue estos pasos en orden y verifica cada test antes de continuar al siguiente.
