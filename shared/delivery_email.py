"""
Envío de alertas por email para el Sistema de Control de Deliveries.
Configuración opcional en .streamlit/secrets.toml o .env:
  delivery_smtp_host, delivery_smtp_port, delivery_smtp_user, delivery_smtp_password,
  delivery_alert_to (email destino, o lista separada por comas).
"""

import logging
from typing import List, Tuple

logger = logging.getLogger(__name__)


def _get_smtp_config() -> dict:
    try:
        from config import secrets
    except Exception:
        secrets = {}
    return {
        "host": secrets.get("delivery_smtp_host") or "",
        "port": int(secrets.get("delivery_smtp_port") or 587),
        "user": secrets.get("delivery_smtp_user") or "",
        "password": secrets.get("delivery_smtp_password") or "",
        "to": (secrets.get("delivery_alert_to") or "").strip(),
    }


def is_email_configured() -> bool:
    cfg = _get_smtp_config()
    return bool(cfg.get("host") and cfg.get("to"))


def send_co_difference_alert(
    co_number: str,
    customer_name: str,
    delivery_date: str,
    closed_by: str,
    items_with_difference: list,
) -> Tuple[bool, str]:
    """
    Envía email al cerrar CO con diferencia.
    Asunto: ⚠ CO{number} cerrada con diferencia – {cliente}
    Contenido: CO, Cliente, Fecha, Usuario que cerró, lista productos con diferencia, motivo, cantidad faltante.
    """
    subject = f"⚠ CO{co_number} cerrada con diferencia – {customer_name}"
    lines = [
        f"CO: {co_number}",
        f"Cliente: {customer_name}",
        f"Fecha delivery: {delivery_date}",
        f"Cerrado por: {closed_by}",
        "",
        "Productos con diferencia:",
    ]
    for it in items_with_difference:
        name = it.get("product_name") or it.get("product_code") or "—"
        req = it.get("requested_qty")
        picked = it.get("picked_qty")
        diff = it.get("difference_qty")
        reason = it.get("difference_reason") or "—"
        lines.append(f"  - {name}: Solicitado {req}, Tomado {picked}, Faltante {diff}. Motivo: {reason}")
    return send_delivery_alert(subject, "\n".join(lines))


def send_delivery_alert(subject: str, body: str) -> Tuple[bool, str]:
    """
    Envía un email de alerta. Retorna (éxito, mensaje).
    Si SMTP no está configurado, retorna (False, "Email no configurado").
    """
    cfg = _get_smtp_config()
    if not cfg.get("host") or not cfg.get("to"):
        return False, "Email no configurado (delivery_smtp_host y delivery_alert_to en secrets)."

    to_addrs: List[str] = [e.strip() for e in cfg["to"].split(",") if e.strip()]
    if not to_addrs:
        return False, "No hay dirección de destino (delivery_alert_to)."

    try:
        import smtplib
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
    except ImportError as e:
        return False, f"Imports de email no disponibles: {e}"

    msg = MIMEMultipart("alternative")
    msg["Subject"] = subject
    msg["From"] = cfg.get("user") or "noreply@delivery"
    msg["To"] = ", ".join(to_addrs)
    msg.attach(MIMEText(body, "plain", "utf-8"))

    try:
        with smtplib.SMTP(cfg["host"], cfg["port"]) as server:
            if cfg.get("user") and cfg.get("password"):
                server.starttls()
                server.login(cfg["user"], cfg["password"])
            server.sendmail(msg["From"], to_addrs, msg.as_string())
        return True, "Alerta enviada por email."
    except Exception as e:
        logger.warning(f"Envio de email fallido: {e}")
        return False, str(e)
