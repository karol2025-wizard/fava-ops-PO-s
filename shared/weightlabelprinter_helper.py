"""
WeightLabelPrinter Helper Module

Este módulo proporciona una función simple para que WeightLabelPrinter.spec
pueda insertar fácilmente las cantidades producidas en el sistema.

OPCIÓN MÁS FÁCIL Y EFECTIVA:
Solo necesitas llamar a insert_production_quantity() cuando el usuario ingresa la cantidad.

También permite leer la cantidad correcta desde el historial de la impresora (view/history)
para usarla en MO Record Insert al escanear el lote.
"""

import json
import logging
import os
import sqlite3
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from shared.database_manager import DatabaseManager

logger = logging.getLogger(__name__)


def _resolve_db_path(path: str) -> Optional[str]:
    """Si path es una carpeta, devuelve el primer .db/.sqlite dentro (o en subcarpeta dist); si es archivo, lo devuelve tal cual."""
    if not path or not os.path.exists(path):
        return None
    if os.path.isfile(path):
        return path
    if os.path.isdir(path):
        for name in sorted(os.listdir(path)):
            if name.endswith(".db") or name.endswith(".sqlite") or name.endswith(".sqlite3"):
                return os.path.join(path, name)
        # fava-touchscreen: el .db suele estar en dist/
        dist_dir = os.path.join(path, "dist")
        if os.path.isdir(dist_dir):
            for name in sorted(os.listdir(dist_dir)):
                if name.endswith(".db") or name.endswith(".sqlite") or name.endswith(".sqlite3"):
                    return os.path.join(dist_dir, name)
    return None


def _get_label_printer_db_path() -> Optional[str]:
    """Ruta a la base de datos SQLite de WeightLabelPrinter (donde guarda el historial)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            path = st.secrets.get("weightlabelprinter_db_path") or st.secrets.get("weightlabelprinter", {}).get("db_path")
            if path:
                resolved = _resolve_db_path(path)
                if resolved:
                    return resolved
                if os.path.isfile(path):
                    return path  # ruta directa a un .db
                # Si es carpeta y no hay .db, no devolver carpeta (isfile fallaría); seguir al fallback
    except Exception:
        pass
    env_path = os.environ.get("WEIGHTLABELPRINTER_DB_PATH")
    if env_path:
        resolved = _resolve_db_path(env_path)
        if resolved:
            return resolved
        if os.path.isfile(env_path):
            return env_path
    # Fallback: fava-touchscreen (dist o raíz) y carpeta del proyecto (por si copian el .db ahí)
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        code_dir = os.path.dirname(project_root)
        search_dirs = [
            os.path.join(code_dir, "fava-touchscreen", "dist"),
            os.path.join(code_dir, "fava-touchscreen"),
            project_root,
            os.path.join(project_root, "data", "production"),
        ]
        for search_dir in search_dirs:
            if os.path.isdir(search_dir):
                found = _resolve_db_path(search_dir)
                if found:
                    return found
    except Exception:
        pass
    return None


def _get_label_printer_history_path() -> Optional[str]:
    """Ruta al archivo de historial de la impresora (WeightLabelPrinter view/history)."""
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            # .streamlit/secrets.toml: weightlabelprinter_history_path = "C:/path/to/history.json"
            path = st.secrets.get("weightlabelprinter_history_path") or st.secrets.get("weightlabelprinter", {}).get("history_path")
            if path:
                return path
    except Exception:
        pass
    return os.environ.get("WEIGHTLABELPRINTER_HISTORY_PATH")


def _aggregate_print_history(entries: list) -> Tuple[Optional[float], Optional[str]]:
    """
    Agrega entradas de historial como en HistorySidebar (Weight Label Printer).

    - Entradas CON container_type → Total # of Entries (count) + container_type como uom.
    - Entradas SIN container_type → Total Weight (suma de weight) + uom del primer registro.

    Returns:
        (quantity, uom) o (None, None).
    """
    if not entries:
        return None, None
    valid = [e for e in entries if e.get("voided_at") is None]
    if not valid:
        return None, None
    entries_with_container = [e for e in valid if e.get("container_type")]
    entries_without_container = [e for e in valid if not e.get("container_type")]

    # Total Weight (ej. 116 kg): entradas sin container_type
    if entries_without_container:
        total_weight = 0.0
        for e in entries_without_container:
            try:
                total_weight += float(e.get("weight", 0) or 0)
            except (TypeError, ValueError):
                pass
        uom = (entries_without_container[0].get("uom") or "").strip() or None
        return (total_weight if total_weight else None), uom

    # Total # of Entries (ej. 2 bag (4.5 L)): entradas con container_type
    if entries_with_container:
        total_entries_count = entries_with_container[0].get("total_entries_count")
        count = int(total_entries_count) if total_entries_count is not None else len(entries_with_container)
        container_type = (entries_with_container[0].get("container_type") or "").strip() or None
        return float(count), container_type

    return None, None


def _fetch_print_history_from_sqlite(db_path: str, lot_code: str) -> List[Dict[str, Any]]:
    """
    Lee el historial de impresión para un lote desde la base SQLite de WeightLabelPrinter / fava-touchscreen.
    Prueba todas las tablas que tengan columna de lote (lot, lot_code, lot_number) y cantidad (weight, quantity, etc.).
    """
    if not os.path.isfile(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        conn.row_factory = sqlite3.Row
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        lot_trim = lot_code.strip()
        lot_alt = ("L" + lot_trim) if not lot_trim.upper().startswith("L") else (lot_trim[1:] if len(lot_trim) > 1 else lot_trim)
        for table in tables:
            try:
                cur.execute(f"PRAGMA table_info({table})")
                info = cur.fetchall()
                cols = [r[1] for r in info]
                cols_lower = [c.lower() for c in cols]
                lot_col = None
                for c in ["lot_code", "lot", "lot_number", "lotnumber"]:
                    if c in cols_lower:
                        lot_col = cols[cols_lower.index(c)]
                        break
                if not lot_col:
                    continue
                weight_col = None
                for c in ["weight", "quantity", "number_of_bags", "qty", "count"]:
                    if c in cols_lower:
                        weight_col = cols[cols_lower.index(c)]
                        break
                if not weight_col:
                    continue
                uom_col = None
                if "uom" in cols_lower:
                    uom_col = cols[cols_lower.index("uom")]
                elif "unit" in cols_lower:
                    uom_col = cols[cols_lower.index("unit")]
                void_col = None
                for c in ["voided_at", "is_voided", "deleted_at", "voided"]:
                    if c in cols_lower:
                        void_col = cols[cols_lower.index(c)]
                        break
                ct_col = None
                if "container_type" in cols_lower:
                    ct_col = cols[cols_lower.index("container_type")]
                elif "container" in cols_lower:
                    ct_col = cols[cols_lower.index("container")]
                select_list = [lot_col, weight_col]
                if uom_col:
                    select_list.append(uom_col)
                if ct_col:
                    select_list.append(ct_col)
                if void_col:
                    select_list.append(void_col)
                placeholders = " OR TRIM(CAST({} AS TEXT)) = ?".format(lot_col) if lot_alt != lot_trim else ""
                cur.execute(
                    f'SELECT {", ".join(select_list)} FROM "{table}" WHERE TRIM(CAST({lot_col} AS TEXT)) = ?' + placeholders,
                    (lot_trim, lot_alt) if lot_alt != lot_trim else (lot_trim,),
                )
                rows = cur.fetchall()
                entries = []
                for row in rows:
                    r = dict(row)
                    if void_col and r.get(void_col):
                        try:
                            if r.get(void_col) in (1, "1", True, "true", "yes"):
                                continue
                        except Exception:
                            pass
                        if str(r.get(void_col) or "").strip():
                            continue
                    entry = {"lot": lot_code, "weight": r.get(weight_col), "uom": r.get(uom_col) if uom_col else ""}
                    if ct_col and r.get(ct_col):
                        entry["container_type"] = r.get(ct_col)
                    entry["voided_at"] = r.get(void_col) if void_col else None
                    entries.append(entry)
                if entries:
                    conn.close()
                    return entries
            except (sqlite3.OperationalError, sqlite3.ProgrammingError):
                continue
        conn.close()
    except Exception as e:
        logger.debug("Could not read label printer SQLite %s: %s", db_path, e)
    return []


def _get_label_printer_mysql_config() -> Optional[Dict[str, Any]]:
    """MySQL config para leer erp_lot_label_print (misma base que Weight Label Printer)."""
    def _from(s):
        if not s:
            return None
        # weightlabelprinter_mysql_* tiene prioridad (base "starship" del .exe)
        host = s.get("weightlabelprinter_mysql_host") or s.get("mysql_host") or s.get("starship_db_host")
        port = int(s.get("weightlabelprinter_mysql_port") or s.get("mysql_port") or s.get("starship_db_port") or 3306)
        user = s.get("weightlabelprinter_mysql_user") or s.get("mysql_user") or s.get("starship_db_user")
        password = s.get("weightlabelprinter_mysql_password") or s.get("mysql_password") or s.get("starship_db_password") or ""
        database = (
            s.get("weightlabelprinter_mysql_database")
            or s.get("mysql_database")
            or s.get("starship_db_database")
        )
        if host and user and database:
            return {"host": host, "port": port, "user": user, "password": password, "database": database}
        return None
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            cfg = _from(st.secrets)
            if cfg:
                return cfg
    except Exception:
        pass
    try:
        from config import secrets
        cfg = _from(secrets)
        if cfg:
            return cfg
    except Exception:
        pass
    # Fallback: mismo DB que el .exe (credentials/config.py DB_CONFIG) — no poner password en git
    try:
        from credentials.config import DB_CONFIG
        if DB_CONFIG and DB_CONFIG.get("host") and DB_CONFIG.get("user") and DB_CONFIG.get("database"):
            return {
                "host": DB_CONFIG["host"],
                "port": int(DB_CONFIG.get("port", 3306)),
                "user": DB_CONFIG["user"],
                "password": DB_CONFIG.get("password", ""),
                "database": DB_CONFIG["database"],
            }
    except Exception:
        pass
    return None


def _fetch_print_history_from_mysql(lot_code: str) -> List[Dict[str, Any]]:
    """
    Lee el historial de impresión desde MySQL (tabla erp_lot_label_print).
    Es la misma tabla que usa Weight Label Printer / fava-touchscreen.
    """
    cfg = _get_label_printer_mysql_config()
    if not cfg:
        return []
    try:
        import pymysql
    except ImportError:
        logger.debug("pymysql not installed; cannot read label printer from MySQL")
        return []
    lot_trim = lot_code.strip()
    lot_alt = ("L" + lot_trim) if not lot_trim.upper().startswith("L") else (lot_trim[1:] if len(lot_trim) > 1 else lot_trim)
    entries = []
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
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT lot_code, weight, uom, container_type, voided_at
                FROM erp_lot_label_print
                WHERE (lot_code = %s OR lot_code = %s)
                  AND (voided_at IS NULL OR voided_at = 0 OR voided_at = '')
                ORDER BY inserted_at DESC
                """,
                (lot_trim, lot_alt),
            )
            rows = cur.fetchall()
        conn.close()
        for r in rows:
            entry = {"lot": lot_code, "weight": r.get("weight"), "uom": r.get("uom") or ""}
            if r.get("container_type"):
                entry["container_type"] = r.get("container_type")
            entry["voided_at"] = r.get("voided_at")
            entries.append(entry)
    except Exception as e:
        logger.debug("Could not read label printer from MySQL %s: %s", cfg.get("database"), e)
    return entries


def _normalize_lot_key(entry_lot: str) -> str:
    """Lote normalizado para agrupar (siempre con L si es numérico)."""
    s = (entry_lot or "").strip()
    if not s:
        return ""
    if s.upper().startswith("L") and len(s) > 1:
        return s.upper()
    return "L" + s.upper()


def _get_label_printer_summary_from_json(since_date: str) -> List[Dict[str, Any]]:
    """
    Resumen por lote desde data/production/label_printer_history.json (fallback si MySQL vacío).
    Filtra por fecha si las entradas tienen timestamp/printed_at/inserted_at.
    """
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_json = os.path.join(project_root, "data", "production", "label_printer_history.json")
        if not os.path.isfile(default_json):
            return []
        with open(default_json, "r", encoding="utf-8") as f:
            data = json.load(f)
        if not isinstance(data, list):
            return []
        since_d = datetime.strptime(since_date, "%Y-%m-%d").date()
        by_lot: Dict[str, List[Dict[str, Any]]] = {}
        for e in data:
            if e.get("voided_at"):
                continue
            lot_raw = e.get("lot") or e.get("lot_code") or ""
            lot = _normalize_lot_key(lot_raw)
            if not lot:
                continue
            ts = e.get("timestamp") or e.get("printed_at") or e.get("inserted_at") or e.get("date")
            if ts:
                try:
                    if isinstance(ts, str) and len(ts) >= 10:
                        t_date = datetime.fromisoformat(ts.replace("Z", "+00:00")).date()
                    else:
                        continue
                except Exception:
                    t_date = None
                if t_date is not None and t_date < since_d:
                    continue
            by_lot.setdefault(lot, []).append(e)
        result = []
        for lot, entries in by_lot.items():
            qty, uom = _aggregate_print_history(entries)
            if qty is None or qty <= 0:
                continue
            first_at = last_at = None
            for e in entries:
                t = e.get("timestamp") or e.get("printed_at") or e.get("inserted_at")
                if t:
                    try:
                        dt = datetime.fromisoformat(str(t).replace("Z", "+00:00")) if isinstance(t, str) else t
                        if first_at is None or dt < first_at:
                            first_at = dt
                        if last_at is None or dt > last_at:
                            last_at = dt
                    except Exception:
                        pass
            has_container = any(e.get("container_type") for e in entries)
            result.append({
                "lot_code": lot,
                "total_entries": int(qty) if has_container else 0,
                "total_weight": float(qty) if not has_container else 0.0,
                "quantity": float(qty),
                "uom": uom,
                "first_at": first_at,
                "last_at": last_at,
            })
        result.sort(key=lambda x: (x["last_at"] or datetime.min), reverse=True)
        return result
    except Exception as e:
        logger.debug("Could not read label printer summary from JSON: %s", e)
        return []


def _get_label_printer_summary_from_sqlite(since_date: str) -> List[Dict[str, Any]]:
    """
    Resumen por lote desde el .db de WeightLabelPrinter (fallback).
    Obtiene todos los lotes únicos y agrega por lote.
    """
    db_path = _get_label_printer_db_path()
    if not db_path or not os.path.isfile(db_path):
        return []
    try:
        conn = sqlite3.connect(db_path)
        cur = conn.cursor()
        cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        tables = [r[0] for r in cur.fetchall()]
        lot_col = None
        for table in tables:
            try:
                cur.execute(f"PRAGMA table_info({table})")
                cols = [r[1] for r in cur.fetchall()]
                cols_lower = [c.lower() for c in cols]
                for c in ["lot_code", "lot", "lot_number"]:
                    if c in cols_lower:
                        lot_col = cols[cols_lower.index(c)]
                        break
                if not lot_col:
                    continue
                time_col = None
                for tc in ["inserted_at", "created_at", "printed_at", "timestamp"]:
                    if tc in cols_lower:
                        time_col = cols[cols_lower.index(tc)]
                        break
                cur.execute(f'SELECT DISTINCT TRIM(CAST("{lot_col}" AS TEXT)) FROM "{table}"')
                lots = [r[0] for r in cur.fetchall() if r and r[0]]
            except (sqlite3.OperationalError, sqlite3.ProgrammingError):
                continue
            break
        conn.close()
        if not lot_col or not lots:
            return []
        result = []
        for lot_raw in lots:
            lot = _normalize_lot_key(lot_raw)
            if not lot:
                continue
            entries = _fetch_print_history_from_sqlite(db_path, lot_raw)
            if not entries:
                continue
            qty, uom = _aggregate_print_history(entries)
            if qty is None or qty <= 0:
                continue
            has_container = bool(entries and entries[0].get("container_type"))
            result.append({
                "lot_code": lot,
                "total_entries": int(qty) if has_container else 0,
                "total_weight": float(qty) if not has_container else 0.0,
                "quantity": float(qty),
                "uom": uom,
                "first_at": None,
                "last_at": None,
            })
        result.sort(key=lambda x: x["lot_code"])
        return result
    except Exception as e:
        logger.debug("Could not read label printer summary from SQLite: %s", e)
        return []


def get_label_printer_summary_since(since_date: str) -> List[Dict[str, Any]]:
    """
    Devuelve un resumen por lote desde una fecha.
    Fuentes (en orden): MySQL erp_lot_label_print → JSON → SQLite .db.

    Args:
        since_date: Fecha mínima en formato 'YYYY-MM-DD' (ej. '2025-02-01').

    Returns:
        Lista de dicts con: lot_code, total_entries, total_weight, quantity, uom, first_at, last_at.
    """
    # 1) MySQL (tabla erp_lot_label_print)
    cfg = _get_label_printer_mysql_config()
    if cfg:
        try:
            import pymysql
            conn = pymysql.connect(
                host=cfg["host"],
                port=cfg["port"],
                user=cfg["user"],
                password=cfg["password"],
                database=cfg["database"],
                charset="utf8mb4",
                cursorclass=pymysql.cursors.DictCursor,
            )
            with conn.cursor() as cur:
                cur.execute(
                    """
                    SELECT
                        lot_code,
                        SUM(CASE WHEN (container_type IS NOT NULL AND TRIM(COALESCE(container_type,'')) != '') THEN 1 ELSE 0 END) AS entries_count,
                        SUM(CASE WHEN (container_type IS NULL OR TRIM(COALESCE(container_type,'')) = '') AND weight IS NOT NULL THEN COALESCE(weight, 0) ELSE 0 END) AS total_weight,
                        MIN(inserted_at) AS first_at,
                        MAX(inserted_at) AS last_at,
                        MAX(COALESCE(container_type, uom)) AS uom_pref,
                        MAX(uom) AS uom_fall
                    FROM erp_lot_label_print
                    WHERE (voided_at IS NULL OR voided_at = 0 OR voided_at = '')
                      AND inserted_at >= %s
                    GROUP BY lot_code
                    HAVING entries_count > 0 OR total_weight > 0
                    ORDER BY last_at DESC
                    """,
                    (since_date,),
                )
                rows = cur.fetchall()
            conn.close()
            if rows:
                result = []
                for r in rows:
                    entries_count = int(r.get("entries_count") or 0)
                    total_weight = float(r.get("total_weight") or 0)
                    quantity = entries_count if entries_count > 0 else total_weight
                    uom = (r.get("uom_pref") or r.get("uom_fall") or "").strip() or None
                    result.append({
                        "lot_code": (r.get("lot_code") or "").strip(),
                        "total_entries": entries_count,
                        "total_weight": total_weight,
                        "quantity": quantity,
                        "uom": uom,
                        "first_at": r.get("first_at"),
                        "last_at": r.get("last_at"),
                    })
                return result
        except Exception as e:
            logger.debug("MySQL label printer summary failed: %s", e)

    # 2) JSON por defecto
    json_result = _get_label_printer_summary_from_json(since_date)
    if json_result:
        return json_result

    # 3) SQLite .db
    sqlite_result = _get_label_printer_summary_from_sqlite(since_date)
    if sqlite_result:
        return sqlite_result

    return []


def get_label_printer_quantity(lot_code: str) -> Tuple[Optional[float], Optional[str]]:
    """
    Obtiene la cantidad (y unidad) impresa para un lote desde el sistema de la impresora de etiquetas.

    Fuentes (en orden):
    1. Archivo de historial de WeightLabelPrinter (secrets weightlabelprinter_history_path o
       WEIGHTLABELPRINTER_HISTORY_PATH). Soporta:
       - Formato HistorySidebar: lista de entradas con "lot"/"lot_code", "weight", "uom",
         "container_type", "voided_at". Se agrega como Total Weight (suma) o Total Entries (count).
       - Formato simple: "quantity"/"actual_qty" y "uom" por entrada (se usa la más reciente).
    2. Production records (records.json) de este proyecto.

    Returns:
        (quantity, uom) o (None, None) si no hay dato.
    """
    if not lot_code or not str(lot_code).strip():
        return None, None
    lot_code = lot_code.strip()

    def _lot_matches(entry_lot: str, lot_code: str) -> bool:
        """True si el lote de la entrada coincide con lot_code (acepta L32570 y 32570)."""
        if not entry_lot or not lot_code:
            return False
        entry = (entry_lot or "").strip().upper()
        code = (lot_code or "").strip().upper()
        if entry == code:
            return True
        if code.startswith("L") and len(code) > 1 and entry == code[1:]:
            return True
        if not code.startswith("L") and entry == "L" + code:
            return True
        return False

    def _read_json_history(filepath: str) -> Tuple[Optional[float], Optional[str]]:
        """Lee JSON de historial y devuelve (quantity, uom) para lot_code (acepta L32570 y 32570)."""
        if not os.path.isfile(filepath):
            return None, None
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                data = json.load(f)
            if not isinstance(data, list):
                return None, None
            entries = [
                e for e in data
                if _lot_matches((e.get("lot") or e.get("lot_code") or ""), lot_code)
            ]
            if not entries:
                return None, None
            # Total Weight (weight+uom) o Total Entries (container_type + total_entries_count)
            if any("weight" in e for e in entries) or any(e.get("container_type") for e in entries):
                return _aggregate_print_history(entries)
            def _ts(e):
                t = e.get("timestamp") or e.get("printed_at") or e.get("date") or ""
                return (t or "")
            entries.sort(key=_ts, reverse=True)
            last = entries[0]
            q = last.get("quantity") or last.get("actual_qty") or last.get("qty")
            if q is not None:
                try:
                    q = float(q)
                except (TypeError, ValueError):
                    return None, None
            u = (last.get("uom") or last.get("unit") or "").strip() or None
            return q, u
        except Exception as e:
            logger.debug("Could not read label printer history file %s: %s", filepath, e)
            return None, None

    # 1) JSON por defecto del proyecto (Total Weight / Total Entries por lote)
    #    data/production/label_printer_history.json — mismo formato que HistorySidebar
    try:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        default_json = os.path.join(project_root, "data", "production", "label_printer_history.json")
        if os.path.isfile(default_json):
            q, u = _read_json_history(default_json)
            if q is not None:
                return q, u
    except Exception:
        pass

    # 2) MySQL: tabla erp_lot_label_print (Weight Label Printer / fava-touchscreen)
    entries_mysql = _fetch_print_history_from_mysql(lot_code)
    if entries_mysql:
        q, u = _aggregate_print_history(entries_mysql)
        if q is not None and q > 0:
            return q, u

    # 3) Archivo .db SQLite (si existiera en fava-touchscreen/dist o data/production)
    db_path = _get_label_printer_db_path()
    if db_path and os.path.isfile(db_path):
        entries = _fetch_print_history_from_sqlite(db_path, lot_code)
        if entries:
            q, u = _aggregate_print_history(entries)
            if q is not None and q > 0:
                return q, u

    # 4) Archivo JSON de historial (secrets: weightlabelprinter_history_path o env)
    history_path = _get_label_printer_history_path()
    if history_path and os.path.isfile(history_path):
        q, u = _read_json_history(history_path)
        if q is not None:
            return q, u

    # 5) Production records (records.json)
    try:
        from shared.json_storage import JSONStorage
        storage = JSONStorage()
        records = storage.get_production_records(lot=lot_code, limit=1)
        if records:
            r = records[0]
            actual = r.get("actual_qty")
            if actual is not None:
                try:
                    return float(actual), None
                except (TypeError, ValueError):
                    pass
    except Exception as e:
        logger.debug("Could not read production records for lot %s: %s", lot_code, e)

    return None, None


def insert_production_quantity(
    lot_code: str,
    quantity: float,
    uom: Optional[str] = None,
    user_operations: Optional[str] = None
) -> bool:
    """
    Inserta una cantidad producida en el sistema para procesamiento automático.
    
    Esta es la función MÁS FÁCIL de usar. Solo necesitas llamarla cuando
    WeightLabelPrinter.spec captura la cantidad real producida.
    
    Args:
        lot_code: Código del LOT (ej: "L28553")
        quantity: Cantidad real producida (debe ser > 0)
        uom: Unidad de medida (opcional, ej: "kg", "lb", "gr")
        user_operations: Información adicional del usuario (opcional)
    
    Returns:
        True si se insertó correctamente, False si hubo error
    
    Example:
        # En WeightLabelPrinter.spec, cuando el usuario ingresa la cantidad:
        from shared.weightlabelprinter_helper import insert_production_quantity
        
        lot_code = "L28553"  # Del sistema
        cantidad_real = 100.5  # Ingresada por el usuario
        unidad = "kg"  # Del sistema
        
        if insert_production_quantity(lot_code, cantidad_real, unidad):
            print("✅ Cantidad registrada. El MO se actualizará automáticamente.")
        else:
            print("❌ Error al registrar la cantidad.")
    """
    if not lot_code or not lot_code.strip():
        logger.error("Lot code is required")
        return False
    
    if not quantity or quantity <= 0:
        logger.error(f"Invalid quantity: {quantity}. Must be > 0")
        return False
    
    try:
        db = DatabaseManager()
        
        # Insertar en erp_mo_to_import
        query = """
        INSERT INTO erp_mo_to_import (lot_code, quantity, uom, user_operations, inserted_at)
        VALUES (%s, %s, %s, %s, %s)
        """
        
        current_time = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        db.execute_query(
            query,
            (
                lot_code.strip(),
                float(quantity),
                uom.strip() if uom else None,
                user_operations if user_operations else None,
                current_time
            )
        )
        
        logger.info(
            f"Production quantity inserted: LOT={lot_code}, Qty={quantity}, UOM={uom}"
        )
        
        return True
        
    except Exception as e:
        logger.error(f"Error inserting production quantity: {str(e)}", exc_info=True)
        return False


# Función alternativa: procesamiento inmediato (si prefieres no usar la base de datos)
def process_production_immediately(
    lot_code: str,
    quantity: float,
    uom: Optional[str] = None
) -> tuple[bool, str]:
    """
    Procesa inmediatamente la producción sin usar la base de datos.
    
    Esta función actualiza el MO directamente sin pasar por la tabla.
    Úsala si prefieres procesamiento inmediato en lugar de procesamiento automático.
    
    Args:
        lot_code: Código del LOT
        quantity: Cantidad producida
        uom: Unidad de medida (opcional)
    
    Returns:
        Tuple de (success, message)
    
    Example:
        from shared.weightlabelprinter_helper import process_production_immediately
        
        success, message = process_production_immediately("L28553", 100.5, "kg")
        if success:
            print(f"✅ {message}")
        else:
            print(f"❌ {message}")
    """
    try:
        from shared.auto_mo_processor import process_production_by_lot
        return process_production_by_lot(lot_code, quantity, uom)
    except Exception as e:
        logger.error(f"Error processing production immediately: {str(e)}", exc_info=True)
        return False, f"Error: {str(e)}"
