# Configuración de Base de Datos

## Error: 'starship_db_host'

Si ves este error, significa que faltan las credenciales de la base de datos en la configuración.

## Solución

### Paso 1: Crear archivo de configuración

Crea el archivo `.streamlit/secrets.toml` en la raíz del proyecto:

**Windows:**
```bash
mkdir .streamlit
notepad .streamlit\secrets.toml
```

**Linux/Mac:**
```bash
mkdir -p .streamlit
nano .streamlit/secrets.toml
```

### Paso 2: Agregar configuración de base de datos

Copia el contenido de `secrets.toml.example` y completa con tus credenciales:

```toml
# Database Configuration (REQUIRED)
starship_db_host = "localhost"           # o la IP de tu servidor de BD
starship_db_port = 3306                  # Puerto de MySQL (default: 3306)
starship_db_user = "tu_usuario"          # Usuario de la base de datos
starship_db_password = "tu_contraseña"    # Contraseña de la base de datos
starship_db_database = "nombre_bd"       # Nombre de la base de datos

# MRPeasy API (REQUIRED)
MRPEASY_API_KEY = "tu_api_key"
MRPEASY_API_SECRET = "tu_api_secret"
```

### Paso 3: Verificar conexión

Ejecuta este script para verificar la conexión:

```python
from shared.database_manager import DatabaseManager

try:
    db = DatabaseManager()
    print("✅ Conexión a la base de datos exitosa!")
except Exception as e:
    print(f"❌ Error: {e}")
```

## Estructura de la tabla requerida

La tabla `erp_mo_to_import` debe existir con esta estructura:

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

## Verificar que la tabla existe

```sql
-- Verificar estructura
DESCRIBE erp_mo_to_import;

-- Ver entradas pendientes
SELECT * FROM erp_mo_to_import 
WHERE processed_at IS NULL 
ORDER BY inserted_at DESC;
```

## Solución de problemas

### Error: "Access denied for user"

- Verificar usuario y contraseña en `secrets.toml`
- Verificar que el usuario tiene permisos en la base de datos

### Error: "Unknown database"

- Verificar que el nombre de la base de datos es correcto
- Verificar que la base de datos existe

### Error: "Can't connect to MySQL server"

- Verificar que el servidor MySQL está ejecutándose
- Verificar host y puerto
- Verificar firewall/red

### La tabla no existe

Ejecuta el script SQL de arriba para crear la tabla.

## Seguridad

⚠️ **IMPORTANTE:**
- El archivo `.streamlit/secrets.toml` NO debe ser commiteado a Git
- Agrega `.streamlit/secrets.toml` a `.gitignore`
- Nunca compartas tus credenciales

