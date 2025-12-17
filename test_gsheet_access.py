"""
Script de prueba para verificar el acceso al Google Sheet
Ejecuta este script para diagnosticar problemas de acceso
"""
import sys
import json
import os

print("Iniciando script de prueba...", file=sys.stderr)
sys.stdout.flush()

try:
    from shared.gsheets_manager import GSheetsManager
    from config import secrets
    print("Imports exitosos", file=sys.stderr)
except Exception as e:
    print(f"Error en imports: {e}", file=sys.stderr)
    import traceback
    traceback.print_exc()
    sys.exit(1)

def test_gsheet_access():
    print("=" * 60)
    print("PRUEBA DE ACCESO A GOOGLE SHEETS")
    print("=" * 60)
    
    # 1. Verificar configuración
    print("\n1. Verificando configuración...")
    creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
    po_sheet_url = secrets.get('PO_SHEET_URL')
    po_worksheet_name = secrets.get('PO_WORKSHEET_NAME', 'PO')
    
    if not creds_path:
        print("❌ ERROR: GOOGLE_CREDENTIALS_PATH no está configurado")
        return
    
    if not po_sheet_url:
        print("❌ ERROR: PO_SHEET_URL no está configurado")
        return
    
    print(f"✅ Credenciales: {creds_path}")
    print(f"✅ URL del Sheet: {po_sheet_url}")
    print(f"✅ Nombre de la hoja: {po_worksheet_name}")
    
    # 2. Verificar archivo de credenciales
    print("\n2. Verificando archivo de credenciales...")
    if not os.path.isabs(creds_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(project_root, creds_path)
    
    if not os.path.exists(creds_path):
        print(f"❌ ERROR: El archivo de credenciales no existe: {creds_path}")
        return
    
    print(f"✅ Archivo de credenciales encontrado: {creds_path}")
    
    # 3. Leer email de la cuenta de servicio
    try:
        with open(creds_path, 'r') as f:
            creds_data = json.load(f)
            service_email = creds_data.get('client_email', 'NOT FOUND')
            print(f"✅ Email de cuenta de servicio: {service_email}")
    except Exception as e:
        print(f"❌ ERROR al leer credenciales: {e}")
        return
    
    # 4. Intentar autenticación
    print("\n3. Intentando autenticación...")
    try:
        gsheets_manager = GSheetsManager(credentials_path=creds_path)
        gsheets_manager.authenticate()
        print("✅ Autenticación exitosa")
    except Exception as e:
        print(f"❌ ERROR en autenticación: {e}")
        return
    
    # 5. Intentar abrir el sheet
    print("\n4. Intentando abrir el Google Sheet...")
    print(f"   URL: {po_sheet_url}")
    print(f"   Hoja: {po_worksheet_name}")
    
    try:
        worksheet = gsheets_manager.open_sheet_by_url(po_sheet_url, po_worksheet_name)
        print("✅ Sheet abierto exitosamente")
        
        # 6. Intentar leer datos
        print("\n5. Intentando leer datos del sheet...")
        df = gsheets_manager.get_as_dataframe(worksheet)
        print(f"✅ Datos leídos exitosamente")
        print(f"   Filas: {len(df)}")
        print(f"   Columnas: {list(df.columns)}")
        
        if len(df) > 0:
            print("\n   Primeras filas:")
            print(df.head().to_string())
        
    except Exception as e:
        error_type = type(e).__name__
        error_message = str(e)
        print(f"\n❌ ERROR al abrir/leer el sheet:")
        print(f"   Tipo: {error_type}")
        print(f"   Mensaje: {error_message}")
        print(f"\n{'='*60}")
        print("DIAGNÓSTICO:")
        print("="*60)
        
        if "PermissionError" in error_type or "permission" in error_message.lower():
            print("\n⚠️ PROBLEMA DE PERMISOS DETECTADO")
            print("\nSOLUCIÓN:")
            print(f"1. Abre el Google Sheet en tu navegador:")
            print(f"   {po_sheet_url}")
            print(f"\n2. Haz clic en el botón 'Compartir' (arriba a la derecha)")
            print(f"\n3. Agrega este email: {service_email}")
            print(f"\n4. Dale permisos de 'Editor' o 'Lector'")
            print(f"\n5. Haz clic en 'Enviar' o 'Listo'")
            print(f"\n6. Espera unos segundos y vuelve a intentar")
        
        elif "SpreadsheetNotFound" in error_type or "404" in error_message:
            print("\n⚠️ SHEET NO ENCONTRADO")
            print("\nSOLUCIÓN:")
            print(f"1. Verifica que la URL sea correcta: {po_sheet_url}")
            print(f"2. Asegúrate de que el sheet exista y esté accesible")
            print(f"3. Verifica que el sheet esté compartido con: {service_email}")
        
        elif "403" in error_message:
            print("\n⚠️ ERROR 403 - ACCESO DENEGADO")
            print("\nSOLUCIÓN:")
            print(f"1. El sheet NO está compartido con la cuenta de servicio")
            print(f"2. Comparte el sheet con: {service_email}")
            print(f"3. Dale permisos de 'Editor' o 'Lector'")
        
        return
    
    print("\n" + "="*60)
    print("✅ TODAS LAS PRUEBAS PASARON EXITOSAMENTE")
    print("="*60)

if __name__ == "__main__":
    try:
        test_gsheet_access()
    except Exception as e:
        print(f"\n❌ ERROR FATAL: {e}")
        import traceback
        traceback.print_exc()

