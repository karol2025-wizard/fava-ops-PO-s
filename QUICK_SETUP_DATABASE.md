# ⚡ Configuración Rápida de Base de Datos

## 🔴 Error Actual

```
Missing required database configuration in secrets: starship_db_host, starship_db_port, starship_db_user, starship_db_password, starship_db_database
```

## ✅ Solución Rápida

### Paso 1: Abrir el archivo de configuración

Abre el archivo: `.streamlit/secrets.toml`

### Paso 2: Buscar la sección de Database Configuration

Busca esta sección (debería estar al final del archivo):

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

### Paso 3: Reemplazar con tus credenciales reales

**Ejemplo de configuración:**

```toml
starship_db_host = "localhost"              # Si la BD está en la misma máquina
# O
starship_db_host = "192.168.1.100"         # Si la BD está en otro servidor

starship_db_port = 3306                    # Puerto estándar de MySQL

starship_db_user = "root"                  # Tu usuario de MySQL
# O
starship_db_user = "fava_user"             # Usuario específico

starship_db_password = "mi_password_123"   # Tu contraseña

starship_db_database = "fava_ops"          # Nombre de tu base de datos
```

### Paso 4: Guardar el archivo

Guarda el archivo `.streamlit/secrets.toml`

### Paso 5: Verificar la configuración

Ejecuta:

```bash
python check_database_config.py
```

Debería mostrar:
- ✅ All required configuration present!
- ✅ Database connection successful!

## 📋 ¿Dónde encontrar las credenciales?

### Si ya tienes la base de datos configurada:

1. **Revisa otros archivos de configuración** que puedan tener estas credenciales
2. **Pregunta al administrador de la base de datos**
3. **Revisa documentación** del proyecto

### Si necesitas crear la base de datos:

1. **Conéctate a MySQL:**
   ```bash
   mysql -u root -p
   ```

2. **Crea la base de datos:**
   ```sql
   CREATE DATABASE fava_ops;
   ```

3. **Crea un usuario (opcional pero recomendado):**
   ```sql
   CREATE USER 'fava_user'@'localhost' IDENTIFIED BY 'tu_contraseña_segura';
   GRANT ALL PRIVILEGES ON fava_ops.* TO 'fava_user'@'localhost';
   FLUSH PRIVILEGES;
   ```

4. **Crea la tabla:**
   ```sql
   USE fava_ops;
   
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

5. **Actualiza `.streamlit/secrets.toml`** con las credenciales que acabas de crear

## 🔍 Verificar que WeightLabelPrinter.exe está escribiendo

Una vez configurada la base de datos, verifica que WeightLabelPrinter.exe está escribiendo datos:

```sql
SELECT * FROM erp_mo_to_import 
WHERE processed_at IS NULL 
ORDER BY inserted_at DESC 
LIMIT 10;
```

Si ves filas aquí, significa que WeightLabelPrinter.exe está funcionando correctamente.

## ⚠️ Importante

- **NO** commitees el archivo `.streamlit/secrets.toml` a Git
- **NO** compartas tus credenciales
- Asegúrate de que el archivo esté en `.gitignore`

## 🆘 ¿Necesitas ayuda?

Si no sabes cuáles son tus credenciales de base de datos:

1. **Pregunta al equipo** que configuró el sistema originalmente
2. **Revisa otros proyectos** que puedan usar la misma base de datos
3. **Contacta al administrador** de la base de datos

