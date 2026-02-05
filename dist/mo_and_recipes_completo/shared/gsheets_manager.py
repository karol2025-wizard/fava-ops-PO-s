import gspread
from oauth2client.service_account import ServiceAccountCredentials
import pandas as pd
import re


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
                f"Cannot read Google credentials: {str(e)}\n"
                f"File path: {self.credentials_path}\n"
                f"Verify that the file exists and you have read permissions."
            )
        except FileNotFoundError as e:
            raise FileNotFoundError(
                f"Credentials file not found: {self.credentials_path}\n"
                f"Verify that the path is correct in the configuration."
            )
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Sheets: {e}")

    def normalize_sheet_url(self, sheet_url):
        """
        Normalize Google Sheets URL by extracting the sheet ID and creating a clean URL.
        Handles various URL formats:
        - https://docs.google.com/spreadsheets/d/SHEET_ID/edit
        - https://docs.google.com/spreadsheets/d/SHEET_ID/edit?gid=0#gid=0
        - https://docs.google.com/spreadsheets/d/SHEET_ID
        """
        if not sheet_url:
            raise ValueError("Sheet URL is empty")
        
        # Pattern to extract sheet ID from various URL formats
        # Matches: /spreadsheets/d/SHEET_ID/ or /spreadsheets/d/SHEET_ID
        match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', sheet_url)
        if match:
            sheet_id = match.group(1)
            # Return a clean URL format that gspread can use
            return f"https://docs.google.com/spreadsheets/d/{sheet_id}"
        else:
            # If we can't extract the ID, return the original URL
            # gspread might still be able to handle it
            return sheet_url

    def open_sheet_by_url(self, sheet_url, worksheet_name):
        """Open a specific worksheet in a Google Sheet by URL"""
        if not self.client:
            raise ValueError("Not authenticated. Call authenticate() first.")

        # Normalize the URL to ensure it's in the correct format
        normalized_url = self.normalize_sheet_url(sheet_url)
        service_account_email = "starship-erp@starship-431114.iam.gserviceaccount.com"

        try:
            spreadsheet = self.client.open_by_url(normalized_url)
            worksheet = spreadsheet.worksheet(worksheet_name)
            return worksheet
        except PermissionError as e:
            # Capture PermissionError specifically before other exceptions
            raise Exception(
                f"❌ Permission error accessing the Google Sheet.\n\n"
                f"**Error details:** {str(e)}\n\n"
                f"**URL:** {sheet_url}\n"
                f"**Worksheet:** {worksheet_name}\n\n"
                f"**⚠️ PROBLEM:** The Google Sheet is not shared with the service account.\n\n"
                f"**Step-by-step solution:**\n"
                f"1. Open the Google Sheet in your browser: {sheet_url}\n"
                f"2. Click the **'Share'** button (top right)\n"
                f"3. Add this email: `{service_account_email}`\n"
                f"4. Give it **'Editor'** or **'Viewer'** permissions\n"
                f"5. Click **'Send'** or **'Done'**\n"
                f"6. Wait a few seconds and try again in the application\n\n"
                f"**Note:** You don't need to notify the service account, it will be added automatically."
            )
        except gspread.exceptions.SpreadsheetNotFound:
            raise Exception(
                f"❌ Could not find the Google Sheet.\n\n"
                f"**URL:** {sheet_url}\n"
                f"**Worksheet:** {worksheet_name}\n\n"
                f"**Possible causes:**\n"
                f"1. The Google Sheet is not shared with the service account\n"
                f"2. The sheet URL is incorrect\n"
                f"3. You don't have permission to access the sheet\n\n"
                f"**Step-by-step solution:**\n"
                f"1. Open the Google Sheet in your browser: {sheet_url}\n"
                f"2. Click the **'Share'** button (top right)\n"
                f"3. Add this email: `{service_account_email}`\n"
                f"4. Give it **'Editor'** or **'Viewer'** permissions\n"
                f"5. Click **'Send'** or **'Done'**\n"
                f"6. Try again in the application\n\n"
                f"**Note:** You don't need to notify the service account, it will be added automatically."
            )
        except gspread.exceptions.WorksheetNotFound:
            raise Exception(
                f"❌ Worksheet '{worksheet_name}' not found in the Google Sheet.\n\n"
                f"**Solution:**\n"
                f"- Verify that the worksheet name is exactly: `{worksheet_name}`\n"
                f"- Or update the configuration with the correct worksheet name"
            )
        except gspread.exceptions.APIError as e:
            # Intentar obtener el código de error de diferentes formas
            error_code = 'Unknown'
            error_message = str(e)
            
            # Intentar obtener el código de error del response
            if hasattr(e, 'response'):
                if isinstance(e.response, dict):
                    error_code = e.response.get('status', 'Unknown')
                elif hasattr(e.response, 'status_code'):
                    error_code = e.response.status_code
            
            # También verificar el mensaje de error para códigos HTTP
            import re
            status_match = re.search(r'(\d{3})', error_message)
            if status_match and error_code == 'Unknown':
                error_code = status_match.group(1)
            
            if error_code == 403 or '403' in error_message:
                raise Exception(
                    f"❌ Permission error (403): You don't have access to the Google Sheet.\n\n"
                    f"**URL:** {sheet_url}\n"
                    f"**Worksheet:** {worksheet_name}\n\n"
                    f"**⚠️ REQUIRED SOLUTION:**\n\n"
                    f"**Step 1:** Open the Google Sheet in your browser\n"
                    f"**Step 2:** Click the **'Share'** button (top right)\n"
                    f"**Step 3:** Add this email: `{service_account_email}`\n"
                    f"**Step 4:** Give it **'Editor'** or **'Viewer'** permissions\n"
                    f"**Step 5:** Click **'Send'** or **'Done'**\n"
                    f"**Step 6:** Wait a few seconds and try again\n\n"
                    f"**Note:** You don't need to notify the service account, it will be added automatically."
                )
            elif error_code == 404:
                raise Exception(
                    f"❌ Google Sheet not found (404).\n\n"
                    f"**URL:** {sheet_url}\n\n"
                    f"**Solution:**\n"
                    f"- Verify that the sheet URL is correct\n"
                    f"- Make sure the sheet exists and is accessible"
                )
            else:
                raise Exception(
                    f"❌ Google Sheets API error (Code: {error_code})\n\n"
                    f"**Details:** {error_message}\n\n"
                    f"**URL:** {sheet_url}\n\n"
                    f"**Solution:**\n"
                    f"- Check your internet connection\n"
                    f"- Try again in a few moments\n"
                    f"- Verify that the sheet is shared correctly"
                )
        except Exception as e:
            # Capturar cualquier otro error y proporcionar contexto útil
            error_type = type(e).__name__
            error_message = str(e)
            
            # Si el error ya tiene un formato con ❌, solo re-lanzarlo
            if "❌" in error_message:
                raise e
            
            # Check if it's a gspread error that wasn't caught before
            if 'gspread' in error_type.lower() or 'gspread' in error_message.lower():
                # Try to extract information from the gspread error
                error_lower = error_message.lower()
                if '403' in error_message or 'forbidden' in error_lower or 'permission' in error_lower:
                    raise Exception(
                        f"❌ Permission error accessing the Google Sheet.\n\n"
                        f"**Error type:** {error_type}\n"
                        f"**Details:** {error_message}\n\n"
                        f"**URL:** {sheet_url}\n"
                        f"**Worksheet:** {worksheet_name}\n\n"
                        f"**⚠️ PROBLEM:** The Google Sheet is not shared with the service account.\n\n"
                        f"**Step-by-step solution:**\n"
                        f"1. Open the Google Sheet in your browser: {sheet_url}\n"
                        f"2. Click the **'Share'** button (top right)\n"
                        f"3. Add this email: `{service_account_email}`\n"
                        f"4. Give it **'Editor'** or **'Viewer'** permissions\n"
                        f"5. Click **'Send'** or **'Done'**\n"
                        f"6. Wait a few seconds and try again in the application\n\n"
                        f"**Note:** You don't need to notify the service account, it will be added automatically."
                    )
            
            # Check if the error suggests permission or access issues
            error_lower = error_message.lower()
            if any(keyword in error_lower for keyword in ['permission', 'access', 'forbidden', 'unauthorized', '403', '404']):
                raise Exception(
                    f"❌ Access error to the Google Sheet.\n\n"
                    f"**Error type:** {error_type}\n"
                    f"**Details:** {error_message}\n\n"
                    f"**URL:** {sheet_url}\n"
                    f"**Worksheet:** {worksheet_name}\n\n"
                    f"**⚠️ MOST COMMON PROBLEM:** The Google Sheet is not shared with the service account.\n\n"
                    f"**Step-by-step solution:**\n"
                    f"1. Open the Google Sheet in your browser: {sheet_url}\n"
                    f"2. Click the **'Share'** button (top right)\n"
                    f"3. Add this email: `{service_account_email}`\n"
                    f"4. Give it **'Editor'** or **'Viewer'** permissions\n"
                    f"5. Click **'Send'** or **'Done'**\n"
                    f"6. Wait a few seconds and try again in the application\n\n"
                    f"**Note:** You don't need to notify the service account, it will be added automatically."
                )
            
            raise Exception(
                f"❌ Error opening the Google Sheet: {error_type}\n\n"
                f"**Details:** {error_message}\n\n"
                f"**URL:** {sheet_url}\n"
                f"**Worksheet:** {worksheet_name}\n\n"
                f"**Possible causes:**\n"
                f"- The Google Sheet is not shared with the service account\n"
                f"- Connection problem with Google Sheets\n"
                f"- Configuration error\n\n"
                f"**Solution:**\n"
                f"1. **Share the Google Sheet** with: `{service_account_email}`\n"
                f"   - Open the sheet → Click 'Share' → Add the email → Permissions 'Editor' or 'Viewer'\n"
                f"2. Verify that the sheet URL is correct\n"
                f"3. Check the configuration in `.streamlit/secrets.toml`\n"
                f"4. Check your internet connection\n\n"
                f"**For more help, run:** `python test_gsheet_access.py`"
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