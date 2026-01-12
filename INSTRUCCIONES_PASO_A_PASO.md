# 📖 INSTRUCCIONES PASO A PASO - Configuración de Base de Datos

## 🎯 ¿Qué necesitas hacer?

Completar la información de conexión a la base de datos en el archivo `.streamlit/secrets.toml`

---

## 📝 PASO 1: Abrir el archivo

1. Ve a la carpeta del proyecto: `C:\Users\Operations - Fava\Desktop\code\fava ops PO's`
2. Abre la carpeta `.streamlit` (es una carpeta oculta, puede tener un punto al inicio)
3. Abre el archivo `secrets.toml` con el Bloc de Notas o cualquier editor de texto

---

## 📝 PASO 2: Encontrar la sección de Base de Datos

Busca en el archivo esta sección (debería estar al final):

```toml
# ============================================================================
# Database Configuration (REQUIRED for erp_close_mo.py and auto_process_production.py)
# ============================================================================
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "tu_usuario"
starship_db_password = "tu_contraseña"
starship_db_database = "nombre_bd"
```

---

## 📝 PASO 3: Obtener las credenciales de la base de datos

Necesitas 5 cosas:

### 1. **Host (starship_db_host)**
   - ¿Dónde está la base de datos?
   - Si está en la misma computadora: `"localhost"`
   - Si está en otro servidor: la dirección IP o nombre del servidor (ej: `"192.168.1.100"`)

### 2. **Puerto (starship_db_port)**
   - Normalmente es `3306` (puerto estándar de MySQL)
   - Si no sabes, usa `3306`

### 3. **Usuario (starship_db_user)**
   - El nombre de usuario para conectarse a la base de datos
   - Ejemplos: `"root"`, `"admin"`, `"fava_user"`

### 4. **Contraseña (starship_db_password)**
   - La contraseña del usuario
   - Ejemplo: `"mi_password123"`

### 5. **Nombre de la Base de Datos (starship_db_database)**
   - El nombre de la base de datos donde está la tabla `erp_mo_to_import`
   - Ejemplos: `"fava_ops"`, `"production"`, `"erp_db"`

---

## 📝 PASO 4: ¿Dónde encontrar estas credenciales?

### Opción A: Si ya tienes la base de datos configurada

1. **Pregunta al administrador** de la base de datos
2. **Revisa otros archivos** de configuración del proyecto
3. **Revisa la documentación** del proyecto
4. **Si WeightLabelPrinter.exe ya funciona**, las credenciales pueden estar en su configuración

### Opción B: Si necesitas crear la base de datos nueva

Sigue las instrucciones en `QUICK_SETUP_DATABASE.md` para crear la base de datos desde cero.

---

## 📝 PASO 5: Escribir las credenciales en el archivo

Una vez que tengas las 5 credenciales, reemplaza los valores en `secrets.toml`:

**ANTES (valores de ejemplo):**
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "tu_usuario"
starship_db_password = "tu_contraseña"
starship_db_database = "nombre_bd"
```

**DESPUÉS (con tus valores reales):**
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "root"
starship_db_password = "mi_password_seguro_123"
starship_db_database = "fava_ops"
```

⚠️ **IMPORTANTE:** 
- Mantén las comillas `"` alrededor de cada valor
- No dejes espacios extra
- Escribe exactamente como está (mayúsculas/minúsculas importan)

---

## 📝 PASO 6: Guardar el archivo

1. Guarda el archivo `secrets.toml`
2. Cierra el editor

---

## 📝 PASO 7: Verificar que funciona

1. Abre la terminal/consola en la carpeta del proyecto
2. Ejecuta este comando:

```bash
python check_database_config.py
```

3. Deberías ver mensajes como:
   ```
   ✅ starship_db_host: localhost
   ✅ starship_db_port: 3306
   ✅ starship_db_user: CONFIGURED (hidden)
   ✅ starship_db_password: CONFIGURED (hidden)
   ✅ starship_db_database: fava_ops
   ✅ All required configuration present!
   ✅ Database connection successful!
   ```

Si ves errores, revisa que:
- Las credenciales estén escritas correctamente
- La base de datos esté ejecutándose
- El usuario y contraseña sean correctos

---

## 📝 PASO 8: Probar en Streamlit

1. Abre la aplicación Streamlit:
   ```bash
   streamlit run home.py
   ```

2. Ve a la página "MRP Easy - Manufacturing Order Processor"

3. Haz clic en "🔄 Fetch Orders from Database"

4. Si todo está bien, deberías ver las órdenes pendientes (o un mensaje diciendo que no hay órdenes pendientes, pero sin errores)

---

## ❓ Preguntas Frecuentes

### ¿Qué pasa si no sé cuáles son las credenciales?

**Opción 1:** Pregunta al equipo o administrador que configuró el sistema originalmente.

**Opción 2:** Si WeightLabelPrinter.exe ya está funcionando y escribiendo a la base de datos, las credenciales deben estar en algún lugar. Busca archivos de configuración relacionados.

**Opción 3:** Si es un sistema nuevo, necesitas crear la base de datos. Sigue las instrucciones en `QUICK_SETUP_DATABASE.md`.

### ¿Qué pasa si la base de datos no existe?

Necesitas crearla. Consulta `QUICK_SETUP_DATABASE.md` para instrucciones detalladas.

### ¿Cómo sé si las credenciales son correctas?

Ejecuta `python check_database_config.py`. Si dice "Database connection successful!", entonces están correctas.

### ¿Puedo usar credenciales de prueba?

Sí, pero necesitas tener una base de datos MySQL/MariaDB ejecutándose. Si no tienes una, necesitas instalarla primero.

---

## 🆘 Si sigues teniendo problemas

1. **Ejecuta el script de verificación:**
   ```bash
   python check_database_config.py
   ```
   Y comparte el mensaje de error completo.

2. **Revisa los logs** para ver qué error específico está ocurriendo.

3. **Verifica que MySQL/MariaDB esté ejecutándose:**
   - En Windows: Busca "Services" y verifica que MySQL esté "Running"
   - O intenta conectarte con: `mysql -u root -p`

---

## ✅ Resumen Rápido

1. Abre `.streamlit/secrets.toml`
2. Encuentra la sección "Database Configuration"
3. Reemplaza los 5 valores con tus credenciales reales
4. Guarda el archivo
5. Ejecuta `python check_database_config.py` para verificar
6. ¡Listo!

