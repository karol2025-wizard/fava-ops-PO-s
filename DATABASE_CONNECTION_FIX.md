# Database Connection Fix

## Problem
Error: `2003 (HY000): Can't connect to MySQL server on 'localhost:3306' (10061)`

This error means:
1. **MySQL server is not running**, OR
2. **Database credentials are incorrect** (currently using placeholders), OR
3. **MySQL is not installed**

## Current Configuration (Placeholders)
Your `.streamlit/secrets.toml` has placeholder values:
```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "tu_usuario"          # ❌ Placeholder
starship_db_password = "tu_contraseña"   # ❌ Placeholder
starship_db_database = "nombre_bd"       # ❌ Placeholder
```

## Solution Steps

### Step 1: Check if MySQL is Running

**Windows:**
```powershell
# Check if MySQL service is running
Get-Service -Name MySQL* | Select-Object Name, Status

# Or check if port 3306 is listening
netstat -an | findstr 3306
```

**If MySQL is not running:**
```powershell
# Start MySQL service (if installed)
Start-Service MySQL80
# Or
net start MySQL80
```

### Step 2: Update Database Configuration

Edit `.streamlit/secrets.toml` and replace the placeholder values with your actual database credentials:

```toml
# Database Configuration (REQUIRED)
starship_db_host = "localhost"           # or your MySQL server IP
starship_db_port = 3306                  # MySQL port (default: 3306)
starship_db_user = "your_actual_username"      # Replace with real username
starship_db_password = "your_actual_password" # Replace with real password
starship_db_database = "your_actual_database_name" # Replace with real database name
```

### Step 3: Verify Connection

Run the check script:
```bash
python check_database_config.py
```

### Step 4: Create Database and Table (if needed)

If the database doesn't exist, create it:

```sql
-- Connect to MySQL
mysql -u root -p

-- Create database
CREATE DATABASE your_database_name;

-- Use the database
USE your_database_name;

-- Create the required table
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

## Common Issues

### Issue 1: MySQL Not Installed
If MySQL is not installed, you need to:
1. Install MySQL Server
2. Or use a remote MySQL server
3. Or use MariaDB (compatible)

### Issue 2: MySQL Running on Different Port
If MySQL is running on a different port (not 3306):
```toml
starship_db_port = 3307  # or whatever port MySQL is using
```

### Issue 3: Remote MySQL Server
If using a remote MySQL server:
```toml
starship_db_host = "192.168.1.100"  # or the server IP/hostname
```

### Issue 4: Firewall Blocking Connection
If MySQL is on a remote server, check firewall rules:
- Windows Firewall
- MySQL server firewall
- Network firewall

## Quick Test

After updating credentials, test the connection:

```python
from shared.database_manager import DatabaseManager

try:
    db = DatabaseManager()
    result = db.fetch_all("SELECT 1 as test")
    print("✅ Connection successful!")
except Exception as e:
    print(f"❌ Connection failed: {e}")
```

## Next Steps

1. **Update `.streamlit/secrets.toml`** with real credentials
2. **Verify MySQL is running**
3. **Test connection** with `check_database_config.py`
4. **Create database/table** if needed (see SQL above)
5. **Restart Streamlit app** to load new configuration

