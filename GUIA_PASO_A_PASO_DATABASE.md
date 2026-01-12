# Guía Paso a Paso - Configurar Base de Datos

## Problema Actual
Error: `2003 (HY000): Can't connect to MySQL server on 'localhost:3306' (10061)`

Esto significa que la aplicación no puede conectarse a MySQL porque:
1. MySQL no está instalado o no está corriendo
2. Las credenciales en el archivo de configuración son placeholders (valores de ejemplo)

---

## PASO 1: Verificar si MySQL está Instalado y Corriendo

### Opción A: Verificar desde PowerShell

1. Abre PowerShell (presiona `Windows + X` y selecciona "Windows PowerShell" o "Terminal")

2. Ejecuta este comando:
```powershell
Get-Service -Name MySQL*
```

**Resultados posibles:**

✅ **Si ves algo como esto:**
```
Name     Status
----     ------
MySQL80  Running
```
→ MySQL está instalado y corriendo. Ve al **PASO 2**.

❌ **Si ves:**
```
Get-Service: Cannot find any service with service name 'MySQL*'
```
→ MySQL no está instalado. Ve al **PASO 1B** para instalarlo.

❌ **Si ves:**
```
Name     Status
----     ------
MySQL80  Stopped
```
→ MySQL está instalado pero no está corriendo. Ejecuta:
```powershell
Start-Service MySQL80
```
Luego ve al **PASO 2**.

### Opción B: Verificar desde el Administrador de Tareas

1. Presiona `Ctrl + Shift + Esc` para abrir el Administrador de Tareas
2. Ve a la pestaña "Servicios"
3. Busca servicios que empiecen con "MySQL"
4. Si no encuentras ninguno → MySQL no está instalado
5. Si encuentras uno pero está "Detenido" → Haz clic derecho → "Iniciar"

---

## PASO 2: Obtener las Credenciales de tu Base de Datos

Necesitas saber:
- **Usuario de MySQL** (ejemplo: `root`, `admin`, `fava_user`)
- **Contraseña de MySQL** (la que configuraste al instalar MySQL)
- **Nombre de la base de datos** (ejemplo: `fava_ops`, `production_db`)

### Si no recuerdas las credenciales:

**Opción 1: Intentar con el usuario root**
- Usuario: `root`
- Contraseña: La que configuraste al instalar MySQL (o vacía si no pusiste contraseña)

**Opción 2: Verificar en MySQL Workbench o phpMyAdmin**
- Si tienes MySQL Workbench instalado, puedes ver las bases de datos ahí
- O usa phpMyAdmin si está instalado

**Opción 3: Crear nuevas credenciales (si tienes acceso root)**

1. Abre PowerShell como Administrador
2. Conecta a MySQL:
```powershell
mysql -u root -p
```
(Te pedirá la contraseña de root)

3. Crea un usuario y base de datos:
```sql
-- Crear base de datos
CREATE DATABASE fava_ops;

-- Crear usuario (reemplaza 'tu_password' con una contraseña segura)
CREATE USER 'fava_user'@'localhost' IDENTIFIED BY 'tu_password';

-- Dar permisos
GRANT ALL PRIVILEGES ON fava_ops.* TO 'fava_user'@'localhost';
FLUSH PRIVILEGES;
```

4. Anota las credenciales:
   - Usuario: `fava_user`
   - Contraseña: `tu_password`
   - Base de datos: `fava_ops`

---

## PASO 3: Editar el Archivo de Configuración

1. **Abre el archivo de configuración:**
   - Ve a la carpeta del proyecto: `C:\Users\Operations - Fava\Desktop\code\fava ops PO's`
   - Abre la carpeta `.streamlit`
   - Abre el archivo `secrets.toml` con el Bloc de notas o cualquier editor de texto

2. **Busca estas líneas (alrededor de la línea 43-47):**
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "tu_usuario"            # ❌ ESTO ES UN PLACEHOLDER
starship_db_password = "tu_contraseña"     # ❌ ESTO ES UN PLACEHOLDER
starship_db_database = "nombre_bd"         # ❌ ESTO ES UN PLACEHOLDER
```

3. **Reemplaza los valores con tus credenciales reales:**

**Ejemplo si usas root:**
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "root"
starship_db_password = "tu_contraseña_de_root"
starship_db_database = "fava_ops"
```

**Ejemplo si creaste un usuario nuevo:**
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "fava_user"
starship_db_password = "tu_password_seguro"
starship_db_database = "fava_ops"
```

4. **Guarda el archivo** (Ctrl + S)

⚠️ **IMPORTANTE:** 
- No compartas este archivo con nadie
- No lo subas a Git (debe estar en `.gitignore`)

---

## PASO 4: Crear la Base de Datos y la Tabla (si no existen)

1. **Conecta a MySQL desde PowerShell:**
```powershell
mysql -u root -p
```
(Te pedirá la contraseña)

2. **Crea la base de datos (si no existe):**
```sql
CREATE DATABASE IF NOT EXISTS fava_ops;
USE fava_ops;
```

3. **Crea la tabla requerida:**
```sql
CREATE TABLE IF NOT EXISTS erp_mo_to_import (
    id INT AUTO_INCREMENT PRIMARY KEY,
    lot_code VARCHAR(255) NOT NULL,
    quantity DECIMAL(10, 2) NOT NULL,
    uom VARCHAR(50),
    user_operations VARCHAR(255),
    inserted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    processed_at TIMESTAMP NULL,
    failed_code TEXT NULL,
    INDEX idx_lot_code (lot_code),
    INDEX idx_processed (processed_at)
);
```

4. **Verifica que se creó correctamente:**
```sql
SHOW TABLES;
DESCRIBE erp_mo_to_import;
```

5. **Sal de MySQL:**
```sql
EXIT;
```

---

## PASO 5: Verificar la Conexión

1. **Abre PowerShell en la carpeta del proyecto:**
```powershell
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
```

2. **Ejecuta el script de verificación:**
```powershell
python check_database_config.py
```

**Resultados esperados:**

✅ **Si todo está bien, verás:**
```
============================================================
Checking Database Configuration
============================================================

✅ starship_db_host: localhost
✅ starship_db_port: 3306
✅ starship_db_user: root
✅ starship_db_password: CONFIGURED (hidden)
✅ starship_db_database: fava_ops

============================================================
✅ All required configuration present!

Testing database connection...
✅ Database connection successful!
✅ Database query test successful!
✅ Table 'erp_mo_to_import' exists!
```

❌ **Si hay errores, verás mensajes específicos:**
- "Access denied" → Credenciales incorrectas (revisa PASO 3)
- "Unknown database" → La base de datos no existe (revisa PASO 4)
- "Can't connect" → MySQL no está corriendo (revisa PASO 1)

---

## PASO 6: Reiniciar la Aplicación Streamlit

1. **Si la aplicación Streamlit está corriendo, detenla:**
   - Presiona `Ctrl + C` en la terminal donde está corriendo

2. **Inicia la aplicación de nuevo:**
```powershell
streamlit run home.py
```

3. **Ve a la página "MRP Easy - Manufacturing Order Processor"**
   - Deberías ver que ahora puede conectarse a la base de datos
   - Ya no deberías ver el error de conexión

---

## Resumen Rápido

1. ✅ Verificar MySQL está corriendo
2. ✅ Obtener credenciales (usuario, contraseña, nombre de BD)
3. ✅ Editar `.streamlit/secrets.toml` con credenciales reales
4. ✅ Crear base de datos y tabla (si no existen)
5. ✅ Verificar conexión con `python check_database_config.py`
6. ✅ Reiniciar Streamlit

---

## Solución de Problemas

### Error: "Access denied for user"
- **Causa:** Usuario o contraseña incorrectos
- **Solución:** Revisa PASO 3, verifica las credenciales

### Error: "Unknown database"
- **Causa:** La base de datos no existe
- **Solución:** Ejecuta el SQL del PASO 4 para crear la base de datos

### Error: "Can't connect to MySQL server"
- **Causa:** MySQL no está corriendo
- **Solución:** Revisa PASO 1, inicia el servicio MySQL

### Error: "Table doesn't exist"
- **Causa:** La tabla `erp_mo_to_import` no existe
- **Solución:** Ejecuta el SQL del PASO 4 para crear la tabla

---

## ¿Necesitas Ayuda?

Si después de seguir estos pasos aún tienes problemas:

1. Ejecuta `python check_database_config.py` y copia el error completo
2. Verifica que MySQL está corriendo: `Get-Service MySQL*`
3. Intenta conectarte manualmente: `mysql -u root -p`
4. Revisa el archivo `DATABASE_CONNECTION_FIX.md` para más detalles

