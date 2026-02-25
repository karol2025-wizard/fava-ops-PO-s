"""
Cerrar MO en MRPeasy por interfaz web con Playwright (flujo paso a paso).

Cuando la API no permite cambiar el estado a Done, este módulo abre el navegador,
hace login, navega directamente a la ficha del MO por ID y ejecuta:
Go to production → Start → Finish → Save → (Yes si aplica) → Consume (cantidad + Save) → Finish production.
(No se hace Release unused.)

Requiere: pip install playwright && playwright install chromium
Configuración en .streamlit/secrets.toml: mrpeasy_playwright_enabled, mrpeasy_app_url, mrpeasy_login_email, mrpeasy_login_password, mrpeasy_playwright_headless.
"""

import asyncio
import logging
import os
import re
import sys
from typing import Optional, Tuple

logger = logging.getLogger(__name__)

if sys.platform == "win32":
    asyncio.set_event_loop_policy(asyncio.WindowsProactorEventLoopPolicy())

try:
    from playwright.sync_api import sync_playwright, TimeoutError as PlaywrightTimeout
    PLAYWRIGHT_AVAILABLE = True
except ImportError:
    PLAYWRIGHT_AVAILABLE = False
    sync_playwright = None
    PlaywrightTimeout = Exception  # type: ignore


def _get_config() -> dict:
    cfg = {}
    try:
        import streamlit as st
        if hasattr(st, "secrets") and st.secrets:
            s = st.secrets
            cfg["app_url"] = (s.get("mrpeasy_app_url") or "").strip() or "https://app.mrpeasy.com"
            cfg["email"] = (s.get("mrpeasy_login_email") or s.get("mrpeasy_login_password") or "").strip()
            cfg["password"] = (s.get("mrpeasy_login_password") or "").strip()
            cfg["headless"] = bool(s.get("mrpeasy_playwright_headless", True))
            cfg["timeout_ms"] = int(s.get("mrpeasy_playwright_timeout_ms") or 30000)
    except Exception:
        pass
    if not cfg.get("app_url"):
        cfg["app_url"] = os.environ.get("MRPEASY_APP_URL", "https://app.mrpeasy.com")
    if not cfg.get("email"):
        cfg["email"] = os.environ.get("MRPEASY_LOGIN_EMAIL", "")
    if not cfg.get("password"):
        cfg["password"] = os.environ.get("MRPEASY_LOGIN_PASSWORD", "")
    return cfg


def close_mo_via_playwright(
    mo_id: int,
    lot_code: str,
    quantity: float,
    mo_number: Optional[str] = None,
) -> Tuple[bool, str]:
    """
    Cierra el MO en MRPeasy vía navegador (Playwright) cuando la API no permite Done.

    Args:
        mo_id: ID del MO.
        lot_code: Código de lote (ej. L33288).
        quantity: Cantidad producida (misma que en MO Record Insert).
        mo_number: Código del MO (ej. MO07308), opcional.

    Returns:
        (True, mensaje) si se cerró correctamente; (False, mensaje_error) si falló.
    """
    if not PLAYWRIGHT_AVAILABLE:
        return False, "Playwright no está instalado. Ejecuta: pip install playwright && playwright install chromium"

    cfg = _get_config()
    if not cfg.get("email") or not cfg.get("password"):
        return False, "Faltan mrpeasy_login_email o mrpeasy_login_password en secrets.toml"

    try:
        enabled = False
        try:
            import streamlit as st
            if hasattr(st, "secrets") and st.secrets:
                enabled = bool(st.secrets.get("mrpeasy_playwright_enabled", False))
        except Exception:
            pass
        if not enabled:
            return False, "Playwright desactivado (mrpeasy_playwright_enabled = false en secrets.toml)."

        base_url = cfg["app_url"].rstrip("/")
        orders_url = f"{base_url}/production/orders" if "/production" not in base_url else base_url
        email = cfg["email"]
        password = cfg["password"]
        headless = cfg["headless"]
        t = cfg["timeout_ms"]

        qty_str = str(int(quantity)) if quantity == int(quantity) else str(quantity)

        with sync_playwright() as p:
            browser = p.chromium.launch(headless=headless)
            context = browser.new_context(viewport={"width": 1280, "height": 720})
            context.set_default_timeout(t)
            page = context.new_page()

            try:
                page.goto(base_url, wait_until="domcontentloaded", timeout=t)
                page.wait_for_load_state("networkidle", timeout=t)
                if "signin" in page.url or page.locator("input[name='username'], input#username").count() > 0:
                    try:
                        page.wait_for_selector("input[name='username'], input#username", timeout=8000)
                        page.fill("input[name='username'], input#username", email)
                        page.fill("input[type='password'], input[name='password']", password)
                        page.click("button#inp_signin, button[name='signin']")
                        page.wait_for_load_state("networkidle", timeout=t)
                        page.wait_for_url(re.compile(r"production|admin"), timeout=15000)
                    except PlaywrightTimeout:
                        pass

                # Navegar directamente al MO por ID para no depender del filtro ni del orden de la lista.
                # (Antes se filtraba por lote y se hacía clic en el .first enlace; si el filtro fallaba
                # o la tabla mostraba otro MO primero, se cerraba el MO equivocado.)
                mo_view_url = f"{orders_url.rstrip('/')}/view/{mo_id}"
                page.goto(mo_view_url, wait_until="domcontentloaded", timeout=t)
                page.wait_for_load_state("networkidle", timeout=t)
                page.wait_for_timeout(1500)
                if "production/orders/view" not in page.url:
                    try:
                        page.wait_for_url(re.compile(r"production/orders/view"), timeout=8000)
                    except Exception:
                        pass
                # Verificar que estamos en el MO correcto (opcional: URL contiene mo_id)
                if str(mo_id) not in page.url:
                    return False, f"Tras abrir {mo_view_url} la página no muestra el MO {mo_id} (URL actual: {page.url})"
                page.wait_for_load_state("networkidle", timeout=t)

                page.wait_for_timeout(1500)
                go_clicked = False
                for sel in [
                    "a[href*='production/myplan/view/']",
                    "a.bt.bt4.bw3:has(span:has-text('Go to production'))",
                    "a:has(span:has-text('Go to production'))",
                    "span:has-text('Go to production')",
                ]:
                    loc = page.locator(sel).first
                    try:
                        loc.wait_for(state="visible", timeout=5000)
                        loc.scroll_into_view_if_needed(timeout=5000)
                        loc.click(timeout=5000)
                        go_clicked = True
                        break
                    except Exception:
                        continue
                if not go_clicked:
                    raise RuntimeError("'Go to production' no encontrado")
                page.wait_for_load_state("networkidle", timeout=t)

                page.locator("a.lnk.start.btnWork").first.click()
                page.wait_for_load_state("networkidle", timeout=t)
                page.locator("a.lnk.stop.btnWork, a[data-lbl_title='Finish']").first.click()
                page.wait_for_load_state("networkidle", timeout=t)

                qty_input = page.locator("input#inp_quantitoy, input[name='quantity']").first
                qty_input.wait_for(state="visible", timeout=t)
                qty_input.fill(qty_str)
                page.wait_for_timeout(300)

                save_btn = page.get_by_role("button", name="Save").first
                try:
                    save_btn.wait_for(state="visible", timeout=5000)
                    save_btn.click()
                except Exception:
                    page.locator("button:has-text('Save'):not(.ui-dialog-title), a:has-text('Save'):not(.ui-dialog-title)").first.click()
                page.wait_for_load_state("networkidle", timeout=t)

                try:
                    yes_loc = page.locator(f"span:has-text('Yes, {qty_str}'), a:has-text('Yes, {qty_str}')").first
                    yes_loc.wait_for(state="visible", timeout=5000)
                    yes_loc.click()
                except Exception:
                    try:
                        page.locator("span:has-text('Yes,'), a:has-text('Yes,')").first.click()
                    except Exception:
                        pass
                page.wait_for_load_state("networkidle", timeout=t)

                try:
                    consume_link = page.locator("a[href*='production/myplan/consume-quantity/'], a.button.small.primary.icon.consume").first
                    consume_link.wait_for(state="visible", timeout=5000)
                    consume_link.click()
                    page.wait_for_timeout(2500)
                    qty_locators = page.locator("input#inp_quantity, input[name='quantity']")
                    for i in range(qty_locators.count()):
                        loc = qty_locators.nth(i)
                        try:
                            if loc.is_visible():
                                loc.fill("")
                                loc.fill(qty_str)
                                break
                        except Exception:
                            continue
                    page.wait_for_timeout(500)
                    page.locator("a#btnConsumeQuantitySave, a.bt.bt1:has(span:has-text('Save'))").first.click()
                    page.wait_for_load_state("networkidle", timeout=t)
                except Exception:
                    pass

                page.locator("button:has-text('Finish production'), a:has-text('Finish production'), span:has-text('Finish production')").first.click()
                page.wait_for_load_state("networkidle", timeout=t)

                return True, "MO cerrado en MRPeasy (estado Done). Flujo Playwright completado."
            except PlaywrightTimeout as e:
                return False, f"Tiempo de espera: {e}"
            except Exception as e:
                logger.exception("Playwright step failed")
                return False, str(e)
            finally:
                context.close()
                browser.close()
    except PlaywrightTimeout as e:
        return False, f"Tiempo de espera agotado: {e}"
    except Exception as e:
        logger.exception("Playwright close MO failed")
        return False, str(e)
