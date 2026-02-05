# Opciones para Testear "MO and Recipes" en Otro Computador

Tienes **3 opciones principales** para ejecutar solo la página de "mo_and_recipes" en otro computador:

---

## 📦 **OPCIÓN 1: Usar el Ejecutable (.exe) - RECOMENDADA**

### Ventajas:
- ✅ No necesita instalar Python
- ✅ Más fácil de ejecutar (solo doble clic)
- ✅ Ya está compilado y listo

### Desventajas:
- ❌ Necesita copiar varios archivos
- ❌ El .exe puede ser grande

### Pasos:

1. **En tu computador actual**, ejecuta el script de preparación:
   ```
   PREPARAR_CARPETA_SIMPLE.bat
   ```
   Esto creará una carpeta en `dist\mo_and_recipes_completo` con todos los archivos necesarios.

2. **Copia la carpeta completa** `dist\mo_and_recipes_completo` al otro computador.

3. **En el otro computador**, ve a la carpeta y ejecuta:
   ```
   mo_and_recipes.exe
   ```

4. La aplicación se abrirá automáticamente en `http://localhost:8501`

### Archivos necesarios:
- `mo_and_recipes.exe`
- `pages/mo_and_recipes.py`
- `shared/` (toda la carpeta)
- `config.py`
- `.streamlit/secrets.toml`
- `credentials/` (toda la carpeta con los JSON)

---

## 🐍 **OPCIÓN 2: Ejecutar con Python Directamente - MÁS FLEXIBLE**

### Ventajas:
- ✅ Puedes ver errores en tiempo real
- ✅ Más fácil de debuggear
- ✅ Puedes modificar código fácilmente

### Desventajas:
- ❌ Necesita instalar Python y dependencias
- ❌ Más pasos de configuración

### Pasos:

1. **En el otro computador**, instala Python 3.8+ si no lo tienes.

2. **Copia estos archivos/carpetas**:
   ```
   pages/mo_and_recipes.py
   shared/ (toda la carpeta)
   config.py
   .streamlit/secrets.toml
   credentials/ (toda la carpeta)
   requirements.txt
   ```

3. **Crea un entorno virtual** (opcional pero recomendado):
   ```bash
   python -m venv venv
   venv\Scripts\activate  # En Windows
   ```

4. **Instala las dependencias**:
   ```bash
   pip install -r requirements.txt
   ```

5. **Ejecuta solo la página de mo_and_recipes**:
   ```bash
   streamlit run pages/mo_and_recipes.py
   ```

   O crea un script `run_mo_and_recipes.bat`:
   ```batch
   @echo off
   streamlit run pages/mo_and_recipes.py
   ```

---

## 🚀 **OPCIÓN 3: Ejecutar Directamente con Streamlit - MÁS SIMPLE**

### Ventajas:
- ✅ No necesitas home.py ni otras páginas
- ✅ Ejecuta directamente la página
- ✅ Más simple y directo

### Desventajas:
- ❌ Aún necesita Python instalado
- ❌ Necesita instalar dependencias

### Pasos:

1. **Copia estos archivos/carpetas**:
   ```
   pages/mo_and_recipes.py
   shared/ (toda la carpeta)
   config.py
   .streamlit/secrets.toml
   credentials/ (toda la carpeta)
   requirements.txt
   EJECUTAR.bat (opcional, para facilitar)
   ```

2. **Instala Python y dependencias** (igual que Opción 2)

3. **Ejecuta directamente**:
   ```bash
   streamlit run pages/mo_and_recipes.py
   ```
   
   O simplemente ejecuta:
   ```bash
   EJECUTAR.bat
   ```

---

## 📋 **Comparación Rápida**

| Característica | Opción 1 (.exe) | Opción 2 (Python) | Opción 3 (Directo) |
|----------------|-----------------|-------------------|-------------------|
| **Instalar Python** | ❌ No | ✅ Sí | ✅ Sí |
| **Instalar dependencias** | ❌ No | ✅ Sí | ✅ Sí |
| **Ver errores fácilmente** | ❌ Difícil | ✅ Fácil | ✅ Fácil |
| **Modificar código** | ❌ No | ✅ Sí | ✅ Sí |
| **Facilidad de uso** | ✅ Muy fácil | ⚠️ Media | ✅ Fácil |
| **Tamaño total** | ⚠️ Grande | ✅ Pequeño | ✅ Pequeño |

---

## 🎯 **Recomendación**

- **Para testear rápido**: Usa **Opción 1** (.exe) - solo copia y ejecuta
- **Para desarrollo/debug**: Usa **Opción 2** o **Opción 3** (Python) - más flexible

---

## ⚠️ **IMPORTANTE: Archivos Críticos**

Independientemente de la opción que elijas, **SIEMPRE necesitas**:

1. ✅ `.streamlit/secrets.toml` - Configuración y credenciales
2. ✅ `credentials/` - Archivos JSON de Google
3. ✅ `shared/` - Módulos compartidos (api_manager.py, gdocs_manager.py, etc.)
4. ✅ `config.py` - Configuración de la app

**Sin estos archivos, la aplicación NO funcionará.**

---

## 🔧 **Solución de Problemas**

### Error: "No module named X"
- **Solución**: Instala las dependencias con `pip install -r requirements.txt`

### Error: "FileNotFoundError: secrets.toml"
- **Solución**: Asegúrate de copiar `.streamlit/secrets.toml` y que esté en la ruta correcta

### Error: "No se encuentra credentials"
- **Solución**: Copia toda la carpeta `credentials/` con los archivos JSON

### La app no se abre en el navegador
- **Solución**: Abre manualmente `http://localhost:8501` en tu navegador

---

## 📝 **Notas Adicionales**

- Si solo quieres testear la funcionalidad básica, puedes usar datos de prueba
- Asegúrate de tener conexión a internet si la app necesita acceder a APIs
- El puerto 8501 puede cambiar si está ocupado (8502, 8503, etc.)
