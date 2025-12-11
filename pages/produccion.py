import streamlit as st
from shared.gsheets_manager import GSheetsManager
from shared.gdocs_manager import GDocsManager
from config import secrets
import pandas as pd
import re
import os
from typing import Dict, List, Any

# Optional database import - only needed if using database
try:
    from shared.database_manager import DatabaseManager
    DATABASE_AVAILABLE = True
except ImportError:
    DATABASE_AVAILABLE = False
    DatabaseManager = None  # Set to None so we can check later

# Page configuration
st.set_page_config(
    page_title="Production",
    page_icon="🍳",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Fava Cuisine Color Palette
FAVA_COLORS = {
    'milk': '#FFFDF5',           # Background
    'avocado': '#D9DEA7',        # Light accent
    'fava_bean': '#72992E',      # Primary green
    'kombu_green': '#384A2A',    # Dark green
    'raisin_black': '#29221A'    # Text/Dark
}

# Custom CSS with Fava Cuisine colors
st.markdown(f"""
    <style>
    /* Main background - Milk */
    .main {{
        background-color: {FAVA_COLORS['milk']};
    }}
    .stApp {{
        background-color: {FAVA_COLORS['milk']};
    }}
    
    /* Production header */
    .production-header {{
        text-align: center;
        padding: 40px 0;
        margin-bottom: 50px;
    }}
    .production-header h1 {{
        color: {FAVA_COLORS['raisin_black']};
        font-size: 48px;
        font-weight: 700;
        margin-bottom: 10px;
    }}
    
    /* Main option buttons (Print Recipes / Generate MO) */
    .main-option-button {{
        height: 200px !important;
        border-radius: 20px !important;
        font-size: 28px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        border: 4px solid {FAVA_COLORS['fava_bean']} !important;
        background: linear-gradient(135deg, {FAVA_COLORS['avocado']} 0%, #E8EDC8 100%) !important;
        color: {FAVA_COLORS['raisin_black']} !important;
        box-shadow: 0 6px 12px rgba(56, 74, 42, 0.2) !important;
        width: 100% !important;
    }}
    .main-option-button:hover {{
        transform: translateY(-8px) !important;
        box-shadow: 0 12px 24px rgba(56, 74, 42, 0.3) !important;
        border-color: {FAVA_COLORS['kombu_green']} !important;
        background: linear-gradient(135deg, #E8EDC8 0%, {FAVA_COLORS['avocado']} 100%) !important;
    }}
    
    /* Section title */
    .section-title {{
        color: {FAVA_COLORS['kombu_green']};
        font-size: 36px;
        font-weight: 700;
        margin-bottom: 30px;
        padding-bottom: 15px;
        border-bottom: 4px solid {FAVA_COLORS['fava_bean']};
    }}
    
    /* Category buttons */
    .category-button {{
        height: 100px !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        border-radius: 15px !important;
        transition: all 0.3s ease !important;
        background-color: white !important;
        color: {FAVA_COLORS['kombu_green']} !important;
        border: 3px solid {FAVA_COLORS['avocado']} !important;
        box-shadow: 0 4px 8px rgba(56, 74, 42, 0.15) !important;
        width: 100% !important;
    }}
    .category-button:hover {{
        transform: translateY(-4px) !important;
        box-shadow: 0 8px 16px rgba(56, 74, 42, 0.25) !important;
        border-color: {FAVA_COLORS['fava_bean']} !important;
        background-color: {FAVA_COLORS['avocado']} !important;
        color: {FAVA_COLORS['raisin_black']} !important;
    }}
    
    /* Recipe/item buttons */
    .recipe-button {{
        background-color: white;
        padding: 20px;
        margin: 10px 0;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(56, 74, 42, 0.1);
        border: 2px solid {FAVA_COLORS['avocado']};
        transition: all 0.2s ease;
        cursor: pointer;
        text-align: center;
        font-weight: 600;
        font-size: 16px;
        color: {FAVA_COLORS['kombu_green']};
    }}
    .recipe-button:hover {{
        box-shadow: 0 4px 12px rgba(56, 74, 42, 0.2);
        transform: translateY(-2px);
        border-color: {FAVA_COLORS['fava_bean']};
        background-color: {FAVA_COLORS['milk']};
    }}
    
    /* Preparation item */
    .preparation-item {{
        background-color: white;
        padding: 15px 20px;
        margin: 10px 0;
        border-radius: 12px;
        box-shadow: 0 2px 6px rgba(56, 74, 42, 0.1);
        border-left: 5px solid {FAVA_COLORS['fava_bean']};
        transition: all 0.2s ease;
        color: {FAVA_COLORS['kombu_green']};
    }}
    .preparation-item:hover {{
        box-shadow: 0 4px 12px rgba(56, 74, 42, 0.2);
        transform: translateX(5px);
        border-left-color: {FAVA_COLORS['kombu_green']};
    }}
    
    /* Back button */
    .back-button {{
        margin-bottom: 20px;
    }}
    
    /* Recipe details */
    .recipe-details {{
        background-color: white;
        padding: 25px;
        border-radius: 15px;
        box-shadow: 0 4px 8px rgba(56, 74, 42, 0.1);
        margin: 20px 0;
        border: 2px solid {FAVA_COLORS['avocado']};
    }}
    .recipe-details h3 {{
        color: {FAVA_COLORS['kombu_green']};
        border-bottom: 3px solid {FAVA_COLORS['fava_bean']};
        padding-bottom: 10px;
        margin-bottom: 15px;
    }}
    .recipe-ingredients, .recipe-instructions {{
        margin: 15px 0;
    }}
    .recipe-ingredients ul, .recipe-instructions ol {{
        margin-left: 20px;
    }}
    .recipe-ingredients li, .recipe-instructions li {{
        margin: 8px 0;
        color: {FAVA_COLORS['raisin_black']};
    }}
    
    /* Action buttons */
    .action-button {{
        padding: 15px 30px;
        border-radius: 10px;
        font-size: 16px;
        font-weight: 600;
        border: none;
        cursor: pointer;
        transition: all 0.3s ease;
    }}
    .action-button.print {{
        background-color: {FAVA_COLORS['fava_bean']};
        color: white;
    }}
    .action-button.print:hover {{
        background-color: {FAVA_COLORS['kombu_green']};
    }}
    .action-button.mo {{
        background-color: {FAVA_COLORS['kombu_green']};
        color: white;
    }}
    .action-button.mo:hover {{
        background-color: {FAVA_COLORS['raisin_black']};
    }}
    
    /* General Streamlit button overrides for categories */
    .stButton > button {{
        transition: all 0.3s ease !important;
    }}
    
    /* Info boxes */
    .info-box {{
        background-color: {FAVA_COLORS['avocado']};
        padding: 15px;
        border-radius: 10px;
        margin: 15px 0;
        border-left: 5px solid {FAVA_COLORS['fava_bean']};
        color: {FAVA_COLORS['raisin_black']};
    }}
    
    /* Style main option buttons */
    button[key="main_print_recipes"],
    button[key="main_generate_mo"] {{
        height: 200px !important;
        border-radius: 20px !important;
        font-size: 28px !important;
        font-weight: 700 !important;
        transition: all 0.3s ease !important;
        border: 4px solid {FAVA_COLORS['fava_bean']} !important;
        background: linear-gradient(135deg, {FAVA_COLORS['avocado']} 0%, #E8EDC8 100%) !important;
        color: {FAVA_COLORS['raisin_black']} !important;
        box-shadow: 0 6px 12px rgba(56, 74, 42, 0.2) !important;
    }}
    button[key="main_print_recipes"]:hover,
    button[key="main_generate_mo"]:hover {{
        transform: translateY(-8px) !important;
        box-shadow: 0 12px 24px rgba(56, 74, 42, 0.3) !important;
        border-color: {FAVA_COLORS['kombu_green']} !important;
        background: linear-gradient(135deg, #E8EDC8 0%, {FAVA_COLORS['avocado']} 100%) !important;
    }}
    
    /* Style category buttons */
    button[key^="category_"] {{
        height: 100px !important;
        font-size: 20px !important;
        font-weight: 600 !important;
        border-radius: 15px !important;
        transition: all 0.3s ease !important;
        background-color: white !important;
        color: {FAVA_COLORS['kombu_green']} !important;
        border: 3px solid {FAVA_COLORS['avocado']} !important;
        box-shadow: 0 4px 8px rgba(56, 74, 42, 0.15) !important;
    }}
    button[key^="category_"]:hover {{
        transform: translateY(-4px) !important;
        box-shadow: 0 8px 16px rgba(56, 74, 42, 0.25) !important;
        border-color: {FAVA_COLORS['fava_bean']} !important;
        background-color: {FAVA_COLORS['avocado']} !important;
        color: {FAVA_COLORS['raisin_black']} !important;
    }}
    </style>
    <script>
    // Apply styles to buttons after page load
    function applyButtonStyles() {{
        // Style main option buttons
        const mainButtons = document.querySelectorAll('button[key="main_print_recipes"], button[key="main_generate_mo"]');
        mainButtons.forEach(btn => {{
            btn.style.height = '200px';
            btn.style.borderRadius = '20px';
            btn.style.fontSize = '28px';
            btn.style.fontWeight = '700';
        }});
        
        // Style category buttons
        const categoryButtons = document.querySelectorAll('button[key^="category_"]');
        categoryButtons.forEach(btn => {{
            btn.style.height = '100px';
            btn.style.fontSize = '20px';
            btn.style.fontWeight = '600';
            btn.style.borderRadius = '15px';
        }});
    }}
    
    // Run on load
    if (document.readyState === 'loading') {{
        document.addEventListener('DOMContentLoaded', applyButtonStyles);
    }} else {{
        applyButtonStyles();
    }}
    
    // Run after Streamlit updates
    setTimeout(applyButtonStyles, 100);
    setInterval(applyButtonStyles, 500);
    </script>
    """, unsafe_allow_html=True)

# Initialize session state
if 'main_option' not in st.session_state:
    st.session_state.main_option = None  # 'print_recipes' or 'generate_mo'
if 'selected_section' not in st.session_state:
    st.session_state.selected_section = None
if 'selected_recipe' not in st.session_state:
    st.session_state.selected_recipe = None
if 'preparations_data' not in st.session_state:
    st.session_state.preparations_data = {}
if 'recipes_data' not in st.session_state:
    st.session_state.recipes_data = {}
if 'gsheets_manager' not in st.session_state:
    st.session_state.gsheets_manager = None
if 'gdocs_manager' not in st.session_state:
    st.session_state.gdocs_manager = None

# Configuration - Update this with your Google Sheet URL
# You can also set this in secrets.toml as PRODUCTION_SHEET_URL
PRODUCTION_SHEET_URL = secrets.get('PRODUCTION_SHEET_URL', '')
# Structure: 'by_sheet' (one sheet per section) or 'by_category' (one sheet with category column)
SHEET_STRUCTURE = secrets.get('PRODUCTION_SHEET_STRUCTURE', 'by_sheet')  # or 'by_category'
# If using 'by_category', specify the category column name
CATEGORY_COLUMN = secrets.get('PRODUCTION_CATEGORY_COLUMN', 'Category')
# Column name for preparation/recipe name
NAME_COLUMN = secrets.get('PRODUCTION_NAME_COLUMN', 'Name')
# Column name for ingredients (optional)
INGREDIENTS_COLUMN = secrets.get('PRODUCTION_INGREDIENTS_COLUMN', 'Ingredients')

# Database configuration
USE_DATABASE = secrets.get('PRODUCTION_USE_DATABASE', False)
PRODUCTION_TABLE_NAME = secrets.get('PRODUCTION_TABLE_NAME', '')
PRODUCTION_NAME_COLUMN_DB = secrets.get('PRODUCTION_NAME_COLUMN_DB', 'name')  # Column name in DB table
PRODUCTION_ID_COLUMN_DB = secrets.get('PRODUCTION_ID_COLUMN_DB', 'id')  # Optional: ID column

# Google Docs configuration - try st.secrets first (Streamlit native), then fallback to config
try:
    PRODUCTION_DOCS_URL = getattr(st.secrets, 'PRODUCTION_DOCS_URL', secrets.get('PRODUCTION_DOCS_URL', 'https://docs.google.com/document/d/1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs/edit'))
    USE_GOOGLE_DOCS = getattr(st.secrets, 'PRODUCTION_USE_GOOGLE_DOCS', secrets.get('PRODUCTION_USE_GOOGLE_DOCS', True))
except AttributeError:
    # st.secrets might not have the keys, use config.py
    PRODUCTION_DOCS_URL = secrets.get('PRODUCTION_DOCS_URL', 'https://docs.google.com/document/d/1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs/edit')
    USE_GOOGLE_DOCS = secrets.get('PRODUCTION_USE_GOOGLE_DOCS', True)
except:
    # st.secrets might not be available at all
    PRODUCTION_DOCS_URL = secrets.get('PRODUCTION_DOCS_URL', 'https://docs.google.com/document/d/1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs/edit')
    USE_GOOGLE_DOCS = secrets.get('PRODUCTION_USE_GOOGLE_DOCS', True)

# Recipe categories - organized list
RECIPE_CATEGORIES = [
    "Dips",
    "Sauces", 
    "Appetizers",
    "Desserts",
    "To-Reheat"
]

# Keyword mapping for filtering preparations by section
SECTION_KEYWORDS = {
    "Dips": ["dip", "dips"],
    "Appetizers": ["appetizer", "appetizers", "starter", "starters"],
    "Breads": ["bread", "breads", "pita", "naan", "flatbread"],
    "Desserts": ["dessert", "desserts", "sweet", "cake", "cookie"],
    "Butcher": ["butcher", "meat", "chicken", "beef", "lamb", "pork"],
    "Saute": ["saute", "sauté", "sauteed"],
    "To-Reheat": ["reheat", "re-heat", "to reheat", "to re-heat", "warm", "heat up"],
    "Sauces": ["sauce", "sauces", "salsa"],
    "Proteins": ["protein", "proteins", "fish", "tofu", "lentil", "bean"]
}

def load_recipes_from_google_docs():
    """Load recipes from Google Docs and organize them by section"""
    if not USE_GOOGLE_DOCS or not PRODUCTION_DOCS_URL:
        return {}
    
    try:
        # Initialize GDocs Manager
        if not st.session_state.gdocs_manager:
            # Try to get credentials path from st.secrets first (Streamlit native), then fallback to config
            try:
                creds_path = getattr(st.secrets, 'GOOGLE_CREDENTIALS_PATH', None) or secrets.get('GOOGLE_CREDENTIALS_PATH')
            except AttributeError:
                creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
            except:
                creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
            
            if not creds_path:
                st.error("Google credentials path not configured. Please set GOOGLE_CREDENTIALS_PATH in .streamlit/secrets.toml")
                with st.expander("🔍 Debug Information"):
                    st.write("**Available secrets keys from config.py:**", list(secrets.keys()))
                    try:
                        # Try to show st.secrets keys
                        if hasattr(st.secrets, '_to_dict'):
                            st.write("**Available secrets keys from st.secrets:**", list(st.secrets._to_dict().keys()))
                        else:
                            st.write("**st.secrets is available but keys cannot be listed**")
                            # Try to access it directly
                            try:
                                test_path = getattr(st.secrets, 'GOOGLE_CREDENTIALS_PATH', 'NOT FOUND')
                                st.write(f"**GOOGLE_CREDENTIALS_PATH from st.secrets:** {test_path}")
                            except:
                                st.write("**Cannot access st.secrets.GOOGLE_CREDENTIALS_PATH**")
                    except Exception as e:
                        st.write(f"**st.secrets not available:** {str(e)}")
                    st.write("**Current working directory:**", os.getcwd())
                    st.write("**Secrets file path:**", os.path.join(os.getcwd(), '.streamlit', 'secrets.toml'))
                    secrets_file_path = os.path.join(os.getcwd(), '.streamlit', 'secrets.toml')
                    if os.path.exists(secrets_file_path):
                        st.write("**Secrets file exists:** ✅ Yes")
                        with open(secrets_file_path, 'r') as f:
                            st.code(f.read(), language='toml')
                    else:
                        st.write("**Secrets file exists:** ❌ No")
                return {}
            
            # Convert relative path to absolute path
            if not os.path.isabs(creds_path):
                # Get the project root directory (where home.py is located)
                project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                creds_path = os.path.join(project_root, creds_path)
            
            # Verify the file exists
            if not os.path.exists(creds_path):
                st.error(f"Credentials file not found at: {creds_path}")
                st.info(f"Please check that the file exists and the path is correct.")
                return {}
            
            gdocs_manager = GDocsManager(credentials_path=creds_path)
            gdocs_manager.authenticate()
            st.session_state.gdocs_manager = gdocs_manager
        
        gdocs_manager = st.session_state.gdocs_manager
        
        # Get document content
        text_content, document = gdocs_manager.get_document_content(PRODUCTION_DOCS_URL)
        
        # Parse recipes from text
        all_recipes = gdocs_manager.parse_recipes_from_text(text_content)
        
        # Organize recipes by section using keywords
        recipes_by_section = {}
        
        # Initialize sections
        for section in SECTION_KEYWORDS.keys():
            recipes_by_section[section] = []
        
        # Categorize recipes
        for recipe in all_recipes:
            recipe_name = recipe.get('name', '').lower()
            categorized = False
            
            for section, keywords in SECTION_KEYWORDS.items():
                for keyword in keywords:
                    if keyword.lower() in recipe_name:
                        recipes_by_section[section].append(recipe)
                        categorized = True
                        break
                if categorized:
                    break
        
        # Remove empty sections and store full recipe data
        recipes_by_section = {k: v for k, v in recipes_by_section.items() if v}
        
        # Also store recipes by name for easy lookup
        recipes_dict = {recipe['name']: recipe for section_recipes in recipes_by_section.values() for recipe in section_recipes}
        st.session_state.recipes_data = recipes_dict
        
        return recipes_by_section
    
    except Exception as e:
        error_str = str(e)
        # Check if it's an API disabled error
        if "SERVICE_DISABLED" in error_str or "has not been used" in error_str or "is disabled" in error_str:
            st.error("⚠️ Google Docs API is not enabled")
            st.warning("""
            **To fix this issue, you need to enable the Google Docs API:**
            
            1. **Enable Google Docs API:**
               - Visit: https://console.developers.google.com/apis/api/docs.googleapis.com/overview?project=594969981919
               - Click "Enable" button
            
            2. **Enable Google Drive API (also required):**
               - Visit: https://console.developers.google.com/apis/api/drive.googleapis.com/overview?project=594969981919
               - Click "Enable" button
            
            3. **Wait a few minutes** for the changes to propagate
            
            4. **Refresh this page** after enabling the APIs
            
            **Alternative:** You can also use Google Sheets instead of Google Docs by setting `PRODUCTION_USE_GOOGLE_DOCS = false` in secrets.toml
            """)
        else:
            st.error(f"Error loading recipes from Google Docs: {error_str}")
            with st.expander("Error Details"):
                st.code(error_str, language='text')
        return {}

def load_preparations_from_database():
    """Load preparations data from database by filtering with keywords"""
    if not DATABASE_AVAILABLE:
        st.error("Database module is not available. Please install mysql-connector-python.")
        return {}
    
    if not USE_DATABASE or not PRODUCTION_TABLE_NAME:
        return {}
    
    try:
        db = DatabaseManager()
        preparations_data = {}
        
        # Validate table and column names (basic SQL injection prevention)
        # Only allow alphanumeric, underscore, and dash characters
        if not re.match(r'^[a-zA-Z0-9_]+$', PRODUCTION_TABLE_NAME):
            st.error(f"Invalid table name: {PRODUCTION_TABLE_NAME}")
            return {}
        
        if not re.match(r'^[a-zA-Z0-9_]+$', PRODUCTION_NAME_COLUMN_DB):
            st.error(f"Invalid column name: {PRODUCTION_NAME_COLUMN_DB}")
            return {}
        
        # Get all preparations from the table
        # Using backticks for MySQL identifiers
        query = f"SELECT DISTINCT `{PRODUCTION_NAME_COLUMN_DB}` FROM `{PRODUCTION_TABLE_NAME}` WHERE `{PRODUCTION_NAME_COLUMN_DB}` IS NOT NULL AND `{PRODUCTION_NAME_COLUMN_DB}` != ''"
        
        results = db.fetch_all(query)
        
        if not results:
            st.info("No preparations found in database.")
            return {}
        
        # Initialize sections
        for section in SECTION_KEYWORDS.keys():
            preparations_data[section] = []
        
        # Filter and categorize each preparation
        for row in results:
            prep_name = row.get(PRODUCTION_NAME_COLUMN_DB, '')
            if not prep_name:
                continue
            
            prep_name_lower = prep_name.lower()
            categorized = False
            
            # Check each section's keywords
            for section, keywords in SECTION_KEYWORDS.items():
                for keyword in keywords:
                    # Use word boundary to match whole words
                    pattern = r'\b' + re.escape(keyword.lower()) + r'\b'
                    if re.search(pattern, prep_name_lower):
                        if prep_name not in preparations_data[section]:
                            preparations_data[section].append(prep_name)
                        categorized = True
                        break
                if categorized:
                    break
        
        # Sort each section's preparations alphabetically
        for section in preparations_data:
            preparations_data[section].sort()
        
        # Remove empty sections
        preparations_data = {k: v for k, v in preparations_data.items() if v}
        
        return preparations_data
    
    except Exception as e:
        st.error(f"Error loading data from database: {str(e)}")
        return {}

def load_preparations_from_gsheets():
    """Load preparations data from Google Sheets"""
    if not PRODUCTION_SHEET_URL:
        return {}
    
    try:
        # Initialize GSheets Manager
        if not st.session_state.gsheets_manager:
            creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
            if not creds_path:
                st.error("Google credentials path not configured. Please set GOOGLE_CREDENTIALS_PATH in secrets.")
                return {}
            
            gsheets_manager = GSheetsManager(credentials_path=creds_path)
            gsheets_manager.authenticate()
            st.session_state.gsheets_manager = gsheets_manager
        
        gsheets_manager = st.session_state.gsheets_manager
        preparations_data = {}
        
        if SHEET_STRUCTURE == 'by_sheet':
            # Each section has its own sheet
            sections = ["Dips", "Appetizers", "Breads", "Desserts", "Butcher", 
                       "Saute", "To-Reheat", "Sauces", "Proteins"]
            
            for section in sections:
                try:
                    worksheet = gsheets_manager.open_sheet_by_url(PRODUCTION_SHEET_URL, section)
                    df = gsheets_manager.get_as_dataframe(worksheet)
                    
                    if not df.empty:
                        # Get preparation names from the name column
                        if NAME_COLUMN in df.columns:
                            preparations = df[NAME_COLUMN].dropna().tolist()
                            preparations_data[section] = preparations
                        else:
                            # If name column doesn't exist, use first column
                            preparations = df.iloc[:, 0].dropna().tolist()
                            preparations_data[section] = preparations
                except Exception as e:
                    # Section sheet doesn't exist, skip it
                    continue
        
        elif SHEET_STRUCTURE == 'by_category':
            # One sheet with a category column
            try:
                # Try to open the first sheet or a specific sheet name
                sheet_name = secrets.get('PRODUCTION_SHEET_NAME', 'Sheet1')
                worksheet = gsheets_manager.open_sheet_by_url(PRODUCTION_SHEET_URL, sheet_name)
                df = gsheets_manager.get_as_dataframe(worksheet)
                
                if not df.empty and CATEGORY_COLUMN in df.columns:
                    # Group by category
                    for category, group in df.groupby(CATEGORY_COLUMN):
                        if NAME_COLUMN in group.columns:
                            preparations = group[NAME_COLUMN].dropna().tolist()
                            preparations_data[category] = preparations
                        else:
                            preparations = group.iloc[:, 0].dropna().tolist()
                            preparations_data[category] = preparations
            except Exception as e:
                st.error(f"Error loading data: {str(e)}")
                return {}
        
        return preparations_data
    
    except Exception as e:
        st.error(f"Error connecting to Google Sheets: {str(e)}")
        return {}

# Load data from Google Docs, database, or Google Sheets, otherwise use sample data
if USE_GOOGLE_DOCS and PRODUCTION_DOCS_URL:
    if not st.session_state.preparations_data:
        with st.spinner("Loading recipes from Google Docs..."):
            st.session_state.preparations_data = load_recipes_from_google_docs()
    PREPARATIONS_DATA = st.session_state.preparations_data
elif USE_DATABASE and PRODUCTION_TABLE_NAME:
    if not st.session_state.preparations_data:
        with st.spinner("Loading preparations from database..."):
            st.session_state.preparations_data = load_preparations_from_database()
    PREPARATIONS_DATA = st.session_state.preparations_data
elif PRODUCTION_SHEET_URL:
    if not st.session_state.preparations_data:
        with st.spinner("Loading preparations from Google Sheets..."):
            st.session_state.preparations_data = load_preparations_from_gsheets()
    PREPARATIONS_DATA = st.session_state.preparations_data
else:
    # Sample data for preparations (fallback if Google Sheets not configured)
    PREPARATIONS_DATA = {
    "Dips": [
        "Hummus",
        "Baba Ganoush",
        "Tzatziki",
        "Tahini Sauce",
        "Garlic Dip",
        "Spicy Red Pepper Dip"
    ],
    "Appetizers": [
        "Falafel",
        "Stuffed Grape Leaves",
        "Spinach Fatayer",
        "Cheese Fatayer",
        "Meat Sambousek",
        "Vegetable Spring Rolls"
    ],
    "Breads": [
        "Pita Bread",
        "Naan",
        "Flatbread",
        "Focaccia",
        "Dinner Rolls",
        "Garlic Bread"
    ],
    "Desserts": [
        "Baklava",
        "Kunafa",
        "Rice Pudding",
        "Halva",
        "Date Cookies",
        "Honey Cake"
    ],
    "Butcher": [
        "Chicken Preparation",
        "Beef Preparation",
        "Lamb Preparation",
        "Meat Marination",
        "Meat Cutting",
        "Meat Grinding"
    ],
    "Saute": [
        "Vegetable Saute",
        "Mushroom Saute",
        "Onion Saute",
        "Pepper Saute",
        "Mixed Vegetables",
        "Garlic Saute"
    ],
    "To-Reheat": [
        "Reheat Rice",
        "Reheat Grains",
        "Reheat Vegetables",
        "Reheat Proteins",
        "Reheat Sauces",
        "Reheat Breads"
    ],
    "Sauces": [
        "Marinara Sauce",
        "Alfredo Sauce",
        "Pesto Sauce",
        "White Sauce",
        "Red Pepper Sauce",
        "Herb Sauce"
    ],
    "Proteins": [
        "Grilled Chicken",
        "Roasted Beef",
        "Braised Lamb",
        "Fish Preparation",
        "Tofu Preparation",
        "Lentil Preparation"
    ]
}

# Header
st.markdown('<div class="production-header">', unsafe_allow_html=True)
st.markdown('<h1>🍳 Production</h1>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Helper functions for recipe actions
def print_recipe(recipe_name):
    """Print recipe function"""
    st.success(f"🖨️ Printing recipe: {recipe_name}")
    # TODO: Implement actual printing functionality
    # This could generate a PDF or send to printer

def generate_mo(recipe_name):
    """Generate Manufacturing Order function"""
    st.success(f"📋 Generating MO for: {recipe_name}")
    # TODO: Implement MO generation functionality
    # This could create a manufacturing order in the ERP system

# Main page flow
# Level 1: Recipe selected - show recipe details
if st.session_state.selected_recipe:
    recipe_name = st.session_state.selected_recipe
    recipe = st.session_state.recipes_data.get(recipe_name, {})
    
    # Back button
    if st.button("← Back to Recipe List", key="back_to_recipes", use_container_width=True):
        st.session_state.selected_recipe = None
        st.rerun()
    
    # Recipe title
    st.markdown(f'<div class="section-title">{recipe_name}</div>', unsafe_allow_html=True)
    
    # Recipe details
    if recipe:
        st.markdown('<div class="recipe-details">', unsafe_allow_html=True)
        
        # Ingredients
        if recipe.get('ingredients'):
            st.markdown("### Ingredients")
            for ingredient in recipe['ingredients']:
                st.markdown(f"- {ingredient}")
        
        # Instructions
        if recipe.get('instructions'):
            st.markdown("### Instructions")
            for i, instruction in enumerate(recipe['instructions'], 1):
                st.markdown(f"{i}. {instruction}")
        
        st.markdown('</div>', unsafe_allow_html=True)
    
    # Action buttons
    col1, col2, col3, col4 = st.columns([1, 1, 1, 1])
    with col2:
        if st.button("🖨️ Print Recipe", key="print_recipe", use_container_width=True, type="primary"):
            print_recipe(recipe_name)
    with col3:
        if st.button("📋 Generate MO", key="generate_mo_recipe", use_container_width=True, type="primary"):
            generate_mo(recipe_name)

# Level 2: Section selected - show recipes list for that category
elif st.session_state.selected_section:
    # Back button
    if st.button("← Back to Categories", key="back_to_categories", use_container_width=True):
        st.session_state.selected_section = None
        st.rerun()
    
    # Section title
    section_name = st.session_state.selected_section
    st.markdown(f'<div class="section-title">{section_name}</div>', unsafe_allow_html=True)
    
    # Show preparations/recipes list
    preparations = PREPARATIONS_DATA.get(section_name, [])
    
    if preparations:
        st.markdown(f"### Recipe List ({len(preparations)} items)")
        
        # Check if we have recipe objects (from Google Docs) or just strings
        has_recipe_objects = isinstance(preparations[0], dict) if preparations else False
        
        if has_recipe_objects:
            # Display recipes as clickable buttons
            for recipe in preparations:
                recipe_name = recipe.get('name', 'Unknown Recipe')
                if st.button(recipe_name, key=f"recipe_{recipe_name}", use_container_width=True):
                    st.session_state.selected_recipe = recipe_name
                    st.rerun()
        else:
            # Display as list items (for database or sheets data)
            for prep in preparations:
                if isinstance(prep, str):
                    prep_name = prep
                else:
                    prep_name = prep.get(NAME_COLUMN, str(prep))
                
                # Try to find recipe in recipes_data if available
                if prep_name in st.session_state.recipes_data:
                    if st.button(prep_name, key=f"recipe_{prep_name}", use_container_width=True):
                        st.session_state.selected_recipe = prep_name
                        st.rerun()
                else:
                    st.markdown(f'<div class="preparation-item">{prep_name}</div>', unsafe_allow_html=True)
    else:
        st.info(f"No recipes found for {section_name}")
        
        # Show configuration help if no data
        if not USE_GOOGLE_DOCS and not USE_DATABASE and not PRODUCTION_SHEET_URL:
            with st.expander("ℹ️ How to Connect Your Data Source"):
                st.markdown("""
                **Option 1: Connect to Google Docs (Recommended)**
                1. Set `PRODUCTION_USE_GOOGLE_DOCS = true` in your `.streamlit/secrets.toml` file
                2. Set `PRODUCTION_DOCS_URL` with your Google Doc URL
                3. Make sure your Google credentials are configured (`GOOGLE_CREDENTIALS_PATH`)
                4. Share your Google Doc with the service account email
                
                **Option 2: Connect to Database**
                1. Set `PRODUCTION_USE_DATABASE = true` in your `.streamlit/secrets.toml` file
                2. Set `PRODUCTION_TABLE_NAME` with your table name (e.g.: "recipes", "preparations")
                3. Set `PRODUCTION_NAME_COLUMN_DB` with the column name that contains recipe names
                4. The system will automatically filter recipes by keywords
                
                **Option 3: Connect to Google Sheets**
                1. Set `PRODUCTION_SHEET_URL` in your `.streamlit/secrets.toml` file
                2. Make sure your Google credentials are configured (`GOOGLE_CREDENTIALS_PATH`)
                3. Share your Google Sheet with the service account email
                """)

# Level 3: Print Recipes selected - show categories
elif st.session_state.main_option == 'print_recipes':
    # Back button to main menu
    if st.button("← Back to Main Menu", key="back_to_main", use_container_width=True):
        st.session_state.main_option = None
        st.session_state.selected_section = None
        st.rerun()
    
    st.markdown(f'<div class="section-title">📋 Select a Category</div>', unsafe_allow_html=True)
    
    # Show all categories from RECIPE_CATEGORIES
    # Create columns for categories (2 columns layout for better visibility)
    num_cols = 2
    
    if RECIPE_CATEGORIES:
        for i in range(0, len(RECIPE_CATEGORIES), num_cols):
            cols = st.columns(num_cols)
            for j, category in enumerate(RECIPE_CATEGORIES[i:i+num_cols]):
                with cols[j]:
                    # Count recipes in this category
                    category_recipes = PREPARATIONS_DATA.get(category, [])
                    count = len(category_recipes) if category_recipes else 0
                    
                    # Create button text with count
                    if count > 0:
                        button_text = f"{category}\n({count} recipe{'s' if count != 1 else ''})"
                    else:
                        button_text = f"{category}\n(0 recipes)"
                    
                    if st.button(
                        button_text,
                        key=f"category_{category}",
                        use_container_width=True,
                        type="secondary"
                    ):
                        st.session_state.selected_section = category
                        st.rerun()
    else:
        st.info("No categories configured. Please check the configuration.")
    
    # Add reload button at the bottom if data source is configured
    st.markdown('<div style="margin: 30px 0;"></div>', unsafe_allow_html=True)
    if USE_GOOGLE_DOCS and PRODUCTION_DOCS_URL:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Recipes", use_container_width=True):
                st.session_state.preparations_data = {}
                st.session_state.recipes_data = {}
                st.session_state.gdocs_manager = None
                st.rerun()
    elif USE_DATABASE and PRODUCTION_TABLE_NAME:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Data", use_container_width=True):
                st.session_state.preparations_data = {}
                st.rerun()
    elif PRODUCTION_SHEET_URL:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Data", use_container_width=True):
                st.session_state.preparations_data = {}
                st.session_state.gsheets_manager = None
                st.rerun()

# Level 4: Generate MO selected
elif st.session_state.main_option == 'generate_mo':
    # Back button to main menu
    if st.button("← Back to Main Menu", key="back_to_main_mo", use_container_width=True):
        st.session_state.main_option = None
        st.rerun()
    
    st.markdown(f'<div class="section-title">🏭 Generate Manufacturing Order</div>', unsafe_allow_html=True)
    
    st.info("""
    **Generate MO Functionality**
    
    This functionality will allow you to generate manufacturing orders (MO) for production.
    Options to create and manage MOs will be available soon.
    """)
    
    # Placeholder for future MO generation functionality
    # This could link to erp_close_mo.py or have its own implementation
    st.markdown("""
    <div class="info-box">
        <strong>Note:</strong> The Generate MO functionality is under development. 
        Please use the "Print Recipes" option to access available recipes.
    </div>
    """, unsafe_allow_html=True)

# Level 5: Main landing page - show two main options
else:
    # Main options: Print Recipes and Generate MO
    st.markdown('<div style="margin: 40px 0;"></div>', unsafe_allow_html=True)
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button(
            "📋 Print Recipes",
            key="main_print_recipes",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.main_option = 'print_recipes'
            st.rerun()
    
    with col2:
        if st.button(
            "🏭 Generate MO",
            key="main_generate_mo",
            use_container_width=True,
            type="primary"
        ):
            st.session_state.main_option = 'generate_mo'
            st.rerun()
    
    # Add some spacing and info
    st.markdown('<div style="margin: 60px 0;"></div>', unsafe_allow_html=True)
    
    # Reload button if data source is configured (small, at bottom)
    if USE_GOOGLE_DOCS and PRODUCTION_DOCS_URL:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Recipes", use_container_width=True):
                st.session_state.preparations_data = {}
                st.session_state.recipes_data = {}
                st.session_state.gdocs_manager = None
                st.session_state.selected_recipe = None
                st.rerun()
    elif USE_DATABASE and PRODUCTION_TABLE_NAME:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Data", use_container_width=True):
                st.session_state.preparations_data = {}
                st.rerun()
    elif PRODUCTION_SHEET_URL:
        col1, col2, col3 = st.columns([2, 1, 2])
        with col2:
            if st.button("🔄 Reload Data", use_container_width=True):
                st.session_state.preparations_data = {}
                st.session_state.gsheets_manager = None
                st.rerun()

