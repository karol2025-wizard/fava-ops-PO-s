"""Script para verificar si el Google Sheet está compartido correctamente"""
import os
import sys
import gspread
from oauth2client.service_account import ServiceAccountCredentials
from config import secrets

print("Verificando acceso al Google Sheet...", flush=True)

try:
    # Cargar credenciales
    creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
    if not os.path.isabs(creds_path):
        project_root = os.path.dirname(os.path.abspath(__file__))
        creds_path = os.path.join(project_root, creds_path)
    
    print(f"Credenciales: {creds_path}", flush=True)
    
    # Autenticar
    scope = [
        'https://spreadsheets.google.com/feeds',
        'https://www.googleapis.com/auth/drive'
    ]
    credentials = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(credentials)
    print("✅ Autenticación exitosa", flush=True)
    
    # Intentar abrir el sheet
    sheet_url = secrets.get('PO_SHEET_URL')
    print(f"Intentando abrir: {sheet_url}", flush=True)
    
    try:
        spreadsheet = client.open_by_url(sheet_url)
        print(f"✅ Sheet abierto exitosamente: {spreadsheet.title}", flush=True)
        
        # Listar hojas
        worksheets = spreadsheet.worksheets()
        print(f"\nHojas disponibles:", flush=True)
        for ws in worksheets:
            print(f"  - {ws.title}", flush=True)
        
        # Intentar abrir la hoja PO
        try:
            worksheet = spreadsheet.worksheet('PO')
            print(f"\n✅ Hoja 'PO' encontrada", flush=True)
            print(f"   Filas: {worksheet.row_count}", flush=True)
            print(f"   Columnas: {worksheet.col_count}", flush=True)
        except gspread.exceptions.WorksheetNotFound:
            print(f"\n❌ Hoja 'PO' no encontrada", flush=True)
            print(f"   Hojas disponibles: {[ws.title for ws in worksheets]}", flush=True)
        
    except gspread.exceptions.SpreadsheetNotFound:
        print("\n❌ Sheet no encontrado o no compartido", flush=True)
        print("El sheet NO está compartido con la cuenta de servicio.", flush=True)
        print("Por favor, comparte el sheet con: starship-erp@starship-431114.iam.gserviceaccount.com", flush=True)
    except Exception as e:
        print(f"\n❌ Error: {type(e).__name__}: {e}", flush=True)
        import traceback
        traceback.print_exc()

except Exception as e:
    print(f"Error fatal: {e}", flush=True)
    import traceback
    traceback.print_exc()
    sys.exit(1)
