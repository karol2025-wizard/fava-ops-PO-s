# Verificar MySQL Después de Instalar

## Paso 1: Verificar que el Servicio está Corriendo

Abre PowerShell y ejecuta:

```powershell
Get-Service -Name MySQL*
```

**Deberías ver algo como:**
```
Name     Status
----     ------
MySQL80  Running
```

Si dice "Stopped", inícialo:
```powershell
Start-Service MySQL80
```

---

## Paso 2: Probar la Conexión

```powershell
mysql -u root -p
```

Te pedirá la contraseña que configuraste durante la instalación.

**Si funciona, verás:**
```
Welcome to the MySQL monitor...
mysql>
```

Escribe `EXIT;` para salir.

---

## Paso 3: Crear la Base de Datos y Tabla

1. **Conecta a MySQL:**
```powershell
mysql -u root -p
```

2. **Ejecuta estos comandos SQL:**
```sql
-- Crear la base de datos
CREATE DATABASE IF NOT EXISTS fava_ops;

-- Usar la base de datos
USE fava_ops;

-- Crear la tabla requerida
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

-- Verificar que se creó
SHOW TABLES;

-- Salir
EXIT;
```

---

## Paso 4: Actualizar secrets.toml

Edita el archivo `.streamlit/secrets.toml`:

```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "root"
starship_db_password = "LA_CONTRASEÑA_QUE_CONFIGURASTE"
starship_db_database = "fava_ops"
```

**⚠️ IMPORTANTE:** Reemplaza `LA_CONTRASEÑA_QUE_CONFIGURASTE` con la contraseña real que pusiste durante la instalación.

---

## Paso 5: Verificar la Conexión desde Python

Desde PowerShell, en la carpeta del proyecto:

```powershell
cd "C:\Users\Operations - Fava\Desktop\code\fava ops PO's"
python check_database_config.py
```

**Deberías ver:**
```
✅ Database connection successful!
✅ Table 'erp_mo_to_import' exists!
```

---

## Solución de Problemas

### Error: "mysql: command not found"
- **Causa:** MySQL no está en el PATH
- **Solución:** Agrega MySQL al PATH o usa la ruta completa:
  ```powershell
  "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysql.exe" -u root -p
  ```

### Error: "Access denied"
- **Causa:** Contraseña incorrecta
- **Solución:** Verifica la contraseña que configuraste durante la instalación

### Error: "Can't connect to MySQL server"
- **Causa:** El servicio no está corriendo
- **Solución:** 
  ```powershell
  Start-Service MySQL80
  ```

### No recuerdo la contraseña de root
- **Solución:** Puedes resetearla siguiendo estos pasos:
  1. Detén el servicio MySQL
  2. Inicia MySQL en modo seguro
  3. Cambia la contraseña
  4. Reinicia el servicio

  O reinstala MySQL y configura una nueva contraseña.

---

## Siguiente Paso

Una vez que todo funcione, reinicia tu aplicación Streamlit:

```powershell
streamlit run home.py
```

El error de conexión debería desaparecer.

