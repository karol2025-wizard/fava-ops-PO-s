# Cómo Instalar MySQL en Windows

## Opción 1: Instalador de MySQL (Recomendado)

### Paso 1: Descargar MySQL
1. Ve a: https://dev.mysql.com/downloads/installer/
2. Descarga **MySQL Installer for Windows**
3. Elige la versión **"mysql-installer-community"** (gratis)

### Paso 2: Instalar
1. Ejecuta el instalador descargado
2. Selecciona **"Developer Default"** o **"Server only"**
3. Sigue el asistente de instalación
4. **IMPORTANTE:** Cuando te pida configurar la contraseña de root, **anótala** (la necesitarás después)
5. Completa la instalación

### Paso 3: Verificar Instalación
Abre PowerShell y ejecuta:
```powershell
Get-Service -Name MySQL*
```

Deberías ver algo como:
```
Name     Status
----     ------
MySQL80  Running
```

### Paso 4: Probar Conexión
```powershell
mysql -u root -p
```
(Te pedirá la contraseña que configuraste)

---

## Opción 2: XAMPP (Más Fácil - Incluye MySQL + phpMyAdmin)

### Paso 1: Descargar XAMPP
1. Ve a: https://www.apachefriends.org/download.html
2. Descarga XAMPP para Windows
3. Instala normalmente

### Paso 2: Iniciar MySQL
1. Abre **XAMPP Control Panel**
2. Haz clic en **"Start"** junto a MySQL
3. El servicio debería iniciarse

### Paso 3: Configuración
- **Usuario por defecto:** `root`
- **Contraseña por defecto:** (vacía, sin contraseña)
- **Puerto:** 3306
- **Host:** localhost

### Paso 4: Acceder a phpMyAdmin
1. En XAMPP Control Panel, haz clic en **"Admin"** junto a MySQL
2. Se abrirá phpMyAdmin en el navegador
3. Puedes crear bases de datos y tablas desde ahí

---

## Opción 3: Usar Base de Datos Remota (Si ya tienes una)

Si ya tienes una base de datos MySQL en otro servidor:

1. **No necesitas instalar MySQL localmente**
2. Solo actualiza `.streamlit/secrets.toml` con:
   ```toml
   starship_db_host = "192.168.1.100"  # IP del servidor remoto
   starship_db_port = 3306
   starship_db_user = "tu_usuario"
   starship_db_password = "tu_contraseña"
   starship_db_database = "nombre_bd"
   ```

---

## Después de Instalar MySQL

### 1. Crear Base de Datos y Tabla

Conecta a MySQL:
```powershell
mysql -u root -p
```

Ejecuta:
```sql
CREATE DATABASE IF NOT EXISTS fava_ops;
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

EXIT;
```

### 2. Actualizar secrets.toml

Edita `.streamlit/secrets.toml`:
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "root"
starship_db_password = "la_contraseña_que_configuraste"
starship_db_database = "fava_ops"
```

### 3. Verificar

```powershell
python check_database_config.py
```

---

## Recomendación

- **Si eres principiante:** Usa **XAMPP** (Opción 2) - Es más fácil
- **Si necesitas solo MySQL:** Usa **MySQL Installer** (Opción 1)
- **Si ya tienes un servidor MySQL:** Usa **Opción 3** (remota)

