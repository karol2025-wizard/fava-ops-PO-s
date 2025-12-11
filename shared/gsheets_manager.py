import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd


class GSheetsManager:
    def __init__(self, credentials_path=None):
        """Initialize the GSheets Manager with the provided credentials path"""
        self.credentials_path = credentials_path
        self.client = None

    def authenticate(self, credentials_path=None):
        """Authenticate with Google Sheets API"""
        if credentials_path:
            self.credentials_path = credentials_path

        if not self.credentials_path:
            raise ValueError("Credentials path not provided")

        scope = [
            'https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive'
        ]

        try:
            credentials = ServiceAccountCredentials.from_json_keyfile_name(self.credentials_path, scope)
            self.client = gspread.authorize(credentials)
            return self.client
        except PermissionError as e:
            raise PermissionError(
                f"No se pueden leer las credenciales de Google: {str(e)}\n"
                f"Ruta del archivo: {self.credentials_path}\n"
                f"Verifica que el archivo exista y tengas permisos de lectura."
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Archivo de credenciales no encontrado: {self.credentials_path}\n"
                f"Verifica que la ruta sea correcta en la configuración."
            )
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Sheets: {e}")

    def open_sheet_by_url(self, sheet_url, worksheet_name):
        """Open a specific worksheet in a Google Sheet by URL"""
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")

        try:
            spreadsheet = self.client.open_by_url(sheet_url)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(
                f"❌ No se pudo encontrar el Google Sheet.\n\n"
                f"**URL:** {sheet_url}\n\n"
                f"**Posibles causas:**\n"
                f"1. El Google Sheet no está compartido con la cuenta de servicio\n"
                f"2. La URL del sheet es incorrecta\n"
                f"3. No tienes permisos para acceder al sheet\n\n"
                f"**Solución:**\n"
                f"- Comparte el Google Sheet con la cuenta de servicio\n"
                f"- Verifica que la URL sea correcta"
            )
        except gspread.exceptions.WorksheetNotFound:
            raise Exception(
                f"❌ No se encontró la hoja '{worksheet_name}' en el Google Sheet.\n\n"
                f"**Solución:**\n"
                f"- Verifica que el nombre de la hoja sea exactamente: `{worksheet_name}`\n"
                f"- O actualiza la configuración con el nombre correcto de la hoja"
            )
        except gspread.exceptions.APIError as e:
            error_code = getattr(e, 'response', {}).get('status', 'Unknown')
            error_message = str(e)
            
            if error_code == 403:
                raise Exception(
                    f"❌ Error de permisos (403): No tienes acceso al Google Sheet.\n\n"
                    f"**URL:** {sheet_url}\n\n"
                    f"**Solución:**\n"
                    f"- Comparte el Google Sheet con la cuenta de servicio\n"
                    f"- Asegúrate de dar permisos de 'Editor' o 'Lector'\n"
                    f"- Verifica que el email de la cuenta de servicio tenga acceso"
                )
            elif error_code == 404:
                raise Exception(
                    f"❌ Google Sheet no encontrado (404).\n\n"
                    f"**URL:** {sheet_url}\n\n"
                    f"**Solución:**\n"
                    f"- Verifica que la URL del sheet sea correcta\n"
                    f"- Asegúrate de que el sheet exista y esté accesible"
                )
            else:
                raise Exception(
                    f"❌ Error de API de Google Sheets (Código: {error_code})\n\n"
                    f"**Detalles:** {error_message}\n\n"
                    f"**URL:** {sheet_url}\n\n"
                    f"**Solución:**\n"
                    f"- Verifica tu conexión a internet\n"
                    f"- Intenta nuevamente en unos momentos\n"
                    f"- Verifica que el sheet esté compartido correctamente"
                )
        except Exception as e:
            # Capturar cualquier otro error y proporcionar contexto útil
            error_type = type(e).__name__
            error_message = str(e)
            
            # Si el error ya tiene un formato con ❌, solo re-lanzarlo
            if "❌" in error_message:
                raise e
            
            # Verificar si el error sugiere problemas de permisos o acceso
            error_lower = error_message.lower()
            if any(keyword in error_lower for keyword in ['permission', 'access', 'forbidden', 'unauthorized', '403', '404']):
                raise Exception(
                    f"❌ Error de acceso al Google Sheet.\n\n"
                    f"**Detalles:** {error_message}\n\n"
                    f"**URL:** {sheet_url}\n"
                    f"**Hoja:** {worksheet_name}\n\n"
                    f"**⚠️ PROBLEMA MÁS COMÚN:** El Google Sheet no está compartido con la cuenta de servicio.\n\n"
                    f"**Solución paso a paso:**\n"
                    f"1. Abre el Google Sheet en tu navegador\n"
                    f"2. Haz clic en el botón **'Compartir'** (arriba a la derecha)\n"
                    f"3. Agrega este email: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
                    f"4. Dale permisos de **'Editor'** o **'Lector'**\n"
                    f"5. Haz clic en **'Enviar'** o **'Listo'**\n"
                    f"6. Intenta nuevamente en la aplicación\n\n"
                    f"**Nota:** No necesitas notificar a la cuenta de servicio, se agregará automáticamente."
                )
            
            raise Exception(
                f"❌ Error al abrir el Google Sheet: {error_type}\n\n"
                f"**Detalles:** {error_message}\n\n"
                f"**URL:** {sheet_url}\n"
                f"**Hoja:** {worksheet_name}\n\n"
                f"**Posibles causas:**\n"
                f"- El Google Sheet no está compartido con la cuenta de servicio\n"
                f"- Problema de conexión con Google Sheets\n"
                f"- Error en la configuración\n\n"
                f"**Solución:**\n"
                f"1. **Comparte el Google Sheet** con: `starship-erp@starship-431114.iam.gserviceaccount.com`\n"
                f"2. Verifica que la URL del sheet sea correcta\n"
                f"3. Revisa la configuración en `.streamlit/secrets.toml`\n"
                f"4. Verifica tu conexión a internet"
            )

    def get_all_records(self, worksheet):
        """Get all records from a worksheet as a list of dictionaries"""
        try:
            return worksheet.get_all_records()
        except Exception as e:
            raise Exception(f"Failed to get records: {e}")

    def get_as_dataframe(self, worksheet):
        """Get worksheet data as a pandas DataFrame"""
        try:
            data = worksheet.get_all_records()
            return pd.DataFrame(data)
        except Exception as e:
            raise Exception(f"Failed to convert to DataFrame: {e}")

    def update_worksheet(self, worksheet, df, start_cell='A1', include_headers=True):
        """Update a worksheet with a pandas DataFrame"""
        try:
            # Convert DataFrame to list of lists
            if include_headers:
                values = [df.columns.tolist()] + df.values.tolist()
            else:
                values = df.values.tolist()

            # Clear existing data
            worksheet.clear()

            # Update with new data
            worksheet.update(start_cell, values)
            return True
        except Exception as e:
            raise Exception(f"Failed to update worksheet: {e}")

    def clear_and_update_worksheet(self, worksheet, df, include_headers=True):
        """Clear worksheet and update with new data"""
        return self.update_worksheet(worksheet, df, 'A1', include_headers)