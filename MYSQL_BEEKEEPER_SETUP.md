# Connecting Beekeeper Studio to MySQL - Step by Step Guide

## ✅ Step 1: MySQL is Running
Your MySQL service (MySQL80) is already running! Good news.

## 🔑 Step 2: Get Your MySQL Root Password

When you installed MySQL, you should have created a root password. You need this to connect!

### If you remember your password:
- Skip to Step 3

### If you forgot your password:
You can reset it, but first try to connect using these common defaults:
- **Default username:** `root`
- **Password:** (the one you set during installation)

**To reset MySQL root password (if needed):**
1. Stop MySQL service:
   ```powershell
   Stop-Service MySQL80
   ```
2. Create a text file `C:\mysql-init.txt` with:
   ```
   ALTER USER 'root'@'localhost' IDENTIFIED BY 'YourNewPassword123!';
   ```
3. Start MySQL with the init file:
   ```powershell
   & "C:\Program Files\MySQL\MySQL Server 8.0\bin\mysqld.exe" --init-file=C:\mysql-init.txt
   ```
4. Close that window, then start MySQL service normally:
   ```powershell
   Start-Service MySQL80
   ```
5. Delete `C:\mysql-init.txt` for security

## 🔌 Step 3: Connect Beekeeper Studio to MySQL

1. **Open Beekeeper Studio**

2. **Click "New Connection"** (usually a + button or "New Connection" button)

3. **Select "MySQL"** as the database type

4. **Fill in the connection details:**
   ```
   Connection Name: MySQL Local (or any name you like)
   Host: localhost (or 127.0.0.1)
   Port: 3306 (default MySQL port)
   User: root (or your MySQL username)
   Password: [your MySQL root password]
   Database: (leave empty for now, or type a database name if you have one)
   ```

5. **Click "Test Connection"** or "Connect"

6. **If connection succeeds:** You're done! ✅

7. **If connection fails:** Check the error message:
   - "Access denied" = Wrong password or username
   - "Can't connect" = MySQL not running (but we verified it is)
   - "Unknown database" = That's okay if you haven't created a database yet

## 🗄️ Step 4: Create Your First Database (Optional)

After connecting in Beekeeper Studio:

1. **In Beekeeper Studio, open a new SQL query tab**

2. **Run this SQL command to create a database:**
   ```sql
   CREATE DATABASE fava_ops;
   ```

3. **Switch to that database:**
   ```sql
   USE fava_ops;
   ```

4. **Or in Beekeeper Studio:** Right-click in the connection and select "New Database" and name it `fava_ops`

## 📝 Step 5: Update Your Application Configuration

Once you have MySQL connected and a database created, update your `.streamlit/secrets.toml`:

```toml
starship_db_host = "localhost"
starship_db_port = 3306
starship_db_user = "root"                    # Your MySQL username
starship_db_password = "YourPassword123!"    # Your MySQL password
starship_db_database = "fava_ops"            # The database name you created
```

## 🧪 Step 6: Test Your Connection

In Beekeeper Studio, try running:
```sql
SELECT VERSION();
```

This should show your MySQL version (8.0.x) if everything is working!

## ❓ Troubleshooting

### Problem: "Access denied for user 'root'@'localhost'"
**Solution:** Wrong password. Try resetting it (see Step 2).

### Problem: "Can't connect to MySQL server"
**Solution:** Make sure MySQL service is running:
```powershell
Get-Service MySQL80
# If not running:
Start-Service MySQL80
```

### Problem: "Unknown database"
**Solution:** Create the database first (Step 4), or leave "Database" field empty in Beekeeper Studio connection.

### Problem: Connection works but I can't see any databases
**Solution:** That's normal for a fresh MySQL installation! You need to create databases. See Step 4.

## 🎯 Quick Connection Checklist

- [ ] MySQL service is running ✅ (we verified this)
- [ ] You know your MySQL root password
- [ ] Beekeeper Studio is installed
- [ ] Created new connection in Beekeeper Studio
- [ ] Used these settings:
  - Host: `localhost`
  - Port: `3306`
  - User: `root`
  - Password: `[your password]`
- [ ] Tested connection successfully
- [ ] Created a database (optional but recommended)
- [ ] Updated `.streamlit/secrets.toml` with your credentials

Good luck! 🚀

