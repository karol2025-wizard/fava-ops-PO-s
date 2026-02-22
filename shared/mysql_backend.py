"""
MySQL backend for DatabaseManager (erp_mo_to_import).
Uses MySQL when configured; otherwise DatabaseManager falls back to JSON.
"""

import logging
from typing import List, Dict, Any, Optional, Tuple

logger = logging.getLogger(__name__)

# Table used by MO Record Insert and ERP Close MO
ERP_MO_TABLE = "erp_mo_to_import"

CREATE_TABLE_SQL = f"""
CREATE TABLE IF NOT EXISTS {ERP_MO_TABLE} (
  id INT AUTO_INCREMENT PRIMARY KEY,
  lot_code VARCHAR(255) NOT NULL,
  quantity DECIMAL(12,4) NOT NULL,
  uom VARCHAR(100) NULL,
  user_operations VARCHAR(255) NULL,
  inserted_at DATETIME NULL,
  processed_at DATETIME NULL,
  failed_code TEXT NULL
);
"""


def get_mysql_config() -> Optional[Dict[str, Any]]:
    """Load MySQL config from secrets. Returns None if not configured."""
    try:
        from config import secrets
        host = secrets.get("mysql_host") or secrets.get("starship_db_host")
        port = secrets.get("mysql_port") or secrets.get("starship_db_port") or 3306
        user = secrets.get("mysql_user") or secrets.get("starship_db_user")
        password = secrets.get("mysql_password") or secrets.get("starship_db_password")
        database = secrets.get("mysql_database") or secrets.get("starship_db_database")
        if host and user and database:
            return {"host": host, "port": int(port), "user": user, "password": password or "", "database": database}
    except Exception as e:
        logger.debug(f"MySQL config not available: {e}")
    return None


def get_connection():
    """Return a MySQL connection or None if not available."""
    try:
        import pymysql
    except ImportError:
        logger.debug("PyMySQL not installed; using JSON backend.")
        return None
    cfg = get_mysql_config()
    if not cfg:
        return None
    try:
        conn = pymysql.connect(
            host=cfg["host"],
            port=cfg["port"],
            user=cfg["user"],
            password=cfg["password"],
            database=cfg["database"],
            charset="utf8mb4",
            cursorclass=pymysql.cursors.DictCursor,
        )
        return conn
    except Exception as e:
        logger.warning(f"MySQL connection failed: {e}")
        return None


def ensure_table(conn) -> bool:
    """Create erp_mo_to_import table if not exists. Returns True on success."""
    try:
        with conn.cursor() as cur:
            cur.execute(CREATE_TABLE_SQL)
        conn.commit()
        return True
    except Exception as e:
        logger.error(f"Failed to create table: {e}")
        return False


def execute_mysql(query: str, values: Tuple = None) -> int:
    """
    Run INSERT or UPDATE on MySQL for erp_mo_to_import.
    Returns number of affected rows. Raises on error.
    """
    conn = get_connection()
    if not conn:
        raise RuntimeError("MySQL not available")
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            cur.execute(query, values or ())
            conn.commit()
            return cur.rowcount
    finally:
        conn.close()


def fetch_all_mysql(query: str, values: Tuple = None) -> List[Dict[str, Any]]:
    """Run SELECT and return list of dicts. Returns [] if MySQL not available."""
    conn = get_connection()
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute(query, values or ())
            rows = cur.fetchall()
        if not rows:
            return []
        # Normalize: ensure datetime columns are serializable (keep as is for display)
        out = []
        for r in rows:
            out.append(dict(r))
        return out
    except Exception as e:
        logger.warning(f"MySQL fetch failed: {e}")
        return []
    finally:
        conn.close()


def is_mysql_available() -> bool:
    """Return True if MySQL is configured and reachable."""
    conn = get_connection()
    if not conn:
        return False
    try:
        ensure_table(conn)
        return True
    except Exception:
        return False
    finally:
        conn.close()


def migrate_json_to_mysql(json_path) -> int:
    """
    One-time migration: read rows from JSON file and insert into MySQL.
    Caller should ensure migration runs only once (e.g. flag file).
    Returns number of rows migrated.
    """
    import json
    if not json_path.exists():
        return 0
    try:
        with open(json_path, "r", encoding="utf-8") as f:
            rows = json.load(f)
    except Exception as e:
        logger.warning(f"Could not read JSON for migration: {e}")
        return 0
    if not rows or not isinstance(rows, list):
        return 0
    conn = get_connection()
    if not conn:
        return 0
    try:
        ensure_table(conn)
        with conn.cursor() as cur:
            migrated = 0
            for r in rows:
                lot_code = r.get("lot_code")
                if not lot_code:
                    continue
                cur.execute(
                    """INSERT INTO erp_mo_to_import
                       (lot_code, quantity, uom, user_operations, inserted_at, processed_at, failed_code)
                       VALUES (%s, %s, %s, %s, %s, %s, %s)""",
                    (
                        lot_code,
                        r.get("quantity", 0),
                        r.get("uom"),
                        r.get("user_operations"),
                        r.get("inserted_at"),
                        r.get("processed_at"),
                        r.get("failed_code"),
                    ),
                )
                migrated += 1
        conn.commit()
        logger.info(f"Migrated {migrated} rows from JSON to MySQL.")
        return migrated
    except Exception as e:
        logger.error(f"Migration failed: {e}")
        return 0
    finally:
        conn.close()
