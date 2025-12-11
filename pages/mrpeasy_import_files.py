import streamlit as st
import pandas as pd
import gspread
import datetime
from shared.gsheets_manager import GSheetsManager
from config import secrets
from oauth2client.service_account import ServiceAccountCredentials

# Page configuration
st.set_page_config(
    page_title="MRPEasy Import Files",
    page_icon="📊",
    layout="wide"
)

# Get the current date
current_date = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M-%S")

# Define Google Sheet URLs
GOOGLE_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1r-iKbJAIEBBeC-lKANTRvbF8auh0U0kZy03YPxsz0hw'
PRODUCTS_SHEET_URL = 'https://docs.google.com/spreadsheets/d/1PKEY_ofj9dUxuvV1v9yaR81AcOS-2ghragW_pw6_EgI'

def authenticate_gsheets():
    scope = ["https://spreadsheets.google.com/feeds",
             'https://www.googleapis.com/auth/spreadsheets',
             "https://www.googleapis.com/auth/drive.file",
             "https://www.googleapis.com/auth/drive"]
    creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
    if not creds_path:
        st.error("GOOGLE_CREDENTIALS_PATH not configured in secrets")
        return None
    creds = ServiceAccountCredentials.from_json_keyfile_name(creds_path, scope)
    client = gspread.authorize(creds)
    return client

def fetch_sheet_as_csv(client, sheet_name):
    try:
        sh = client.open_by_url(GOOGLE_SHEET_URL)
        worksheet = sh.worksheet(sheet_name)
        data = worksheet.get_all_records()
        df = pd.DataFrame(data)
        return df.to_csv(index=False)
    except gspread.exceptions.WorksheetNotFound:
        st.error(f"Worksheet {sheet_name} not found.")
        return None


st.title("Generate Import CSV Files for MRPEasy")

# CSS to change button colors
st.markdown("""
    <style>
    .button-dlroutings button {
        background-color: #4CAF50; /* Green */
        color: white;
    }
    .button-dlbom button {
        background-color: #2196F3; /* Blue */
        color: white;
    }
    .button-dlproducts button {
        background-color: #2196F3; /* Blue */
        color: white;
    }
    .button-dlpurchaseterms button {
        background-color: #2196F3; /* Blue */
        color: white;
    }
    .button-boxheroinventory button {
        background-color: #FF9800; /* Orange */
        color: white;
    }
    .button-updateboxheroitems button {
        background-color: #9C27B0; /* Purple */
        color: white;
    }
    .button-inspectboxhero button {
        background-color: #607D8B; /* Blue Gray */
        color: white;
    }
    .button-cleanupboxhero button {
        background-color: #F44336; /* Red */
        color: white;
    }
    </style>
    """, unsafe_allow_html=True)


if st.button('Routings'):
    client = authenticate_gsheets()
    if client:
        csv_data = fetch_sheet_as_csv(client, 'Final-Routings')
        if csv_data:
            st.download_button(label=":green[Download Routings CSV]", data=csv_data, file_name=f"routings_{current_date}.csv", mime='text/csv', key='dlroutings')

if st.button('BOM'):
    client = authenticate_gsheets()
    if client:
        csv_data = fetch_sheet_as_csv(client, 'Final-BOM')
        if csv_data:
            st.download_button(label=":green[Download BOM CSV]", data=csv_data, file_name=f"bom_{current_date}.csv", mime='text/csv', key='dlbom')

if st.button('Products'):
    client = authenticate_gsheets()
    if client:
        csv_data = fetch_sheet_as_csv(client, 'Final-Products')
        if csv_data:
            st.download_button(label=":green[Download Products CSV]", data=csv_data, file_name=f"products_{current_date}.csv", mime='text/csv', key='dlproducts')

if st.button('Purchase Terms'):
    client = authenticate_gsheets()
    if client:
        csv_data = fetch_sheet_as_csv(client, 'Final-Purchase-Terms')
        if csv_data:
            st.download_button(label=":green[Download Purchase Terms CSV]", data=csv_data, file_name=f"purchase_terms_{current_date}.csv", mime='text/csv', key='dlpurchaseterms')


