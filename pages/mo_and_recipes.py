import streamlit as st
import logging
from typing import Optional, List, Dict, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import base64
import tempfile
import json
from io import BytesIO

from shared.api_manager import APIManager
from shared.gdocs_manager import GDocsManager
from config import secrets
from googleapiclient.errors import HttpError
from reportlab.lib import colors
import os
from reportlab.lib.pagesizes import letter
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph, Spacer, Image, Flowable
from reportlab.lib.enums import TA_LEFT, TA_CENTER
from reportlab.graphics.barcode import code128
import requests
from PIL import Image as PILImage

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class BarCode128(Flowable):
    """A custom Flowable for Code 128 barcodes"""

    def __init__(self, value, width=3 * inch, height=0.5 * inch):
        Flowable.__init__(self)
        self.value = value
        self.barWidth = width
        self.barHeight = height

    def wrap(self, availWidth, availHeight):
        """Returns the size this flowable will take up"""
        return self.barWidth, self.barHeight

    def draw(self):
        """Draw the barcode"""
        barcode = code128.Code128(self.value, barWidth=0.01 * inch, barHeight=self.barHeight)
        x = (self.barWidth - barcode.width) / 2  # Center the barcode
        barcode.drawOn(self.canv, x, 0)


@st.cache_data(ttl=3600*6, show_spinner=False)  # 6 hours cache
def fetch_items_cache(api_key: str, api_secret: str) -> List[Dict]:
    """Fetch and cache all items for 6 hours"""
    api = APIManager()
    items = api.fetch_all_products()
    logger.info(f"Items cache initialized with {len(items) if items else 0} items")
    return items if items else []


@st.cache_data(ttl=3600*6, show_spinner=False)  # 6 hours cache
def fetch_units_cache(api_key: str, api_secret: str) -> List[Dict]:
    """Fetch and cache all units for 6 hours"""
    api = APIManager()
    units = api.fetch_units()
    logger.info(f"Units cache initialized with {len(units) if units else 0} units")
    return units if units else []


def get_cache_info() -> Dict[str, Any]:
    """Get cache metadata from session state"""
    if 'cache_metadata' not in st.session_state:
        st.session_state.cache_metadata = {
            'items_loaded': False,
            'units_loaded': False,
            'last_updated': None
        }
    return st.session_state.cache_metadata


def clear_all_caches():
    """Clear all cached data"""
    fetch_items_cache.clear()
    fetch_units_cache.clear()
    st.session_state.cache_metadata = {
        'items_loaded': False,
        'units_loaded': False,
        'last_updated': None
    }
    logger.info("All caches cleared")


def initialize_session_state():
    """
    Initialize session state variables for the state machine flow.
    
    FLOW STATE MACHINE:
    ===================
    
    1. action_selected (str | None)
       - Values: 'recipe' | 'mo' | None
       - Activated: When user selects primary action (View Recipe or Create MO)
       - Purpose: Determines the main workflow path
    
    2. category_selected (str | None) [alias: selected_category]
       - Values: category name string | None
       - Activated: When user selects a category in Step 2
       - Purpose: Filters items by category
    
    3. item_selected (dict | None) [alias: selected_item]
       - Values: item dict | None
       - Activated: When user selects an item in Step 3
       - Purpose: Stores the selected item for MO creation or recipe viewing
    
    4. mo_number (int | None) [alias: created_mo_id]
       - Values: MO ID integer | None
       - Activated: After successful MO creation
       - Purpose: Stores the created MO ID for routing PDF generation
    
    5. show_routing (bool)
       - Values: True | False
       - Activated: After MO creation and routing PDF is ready to display
       - Purpose: Controls visibility of routing PDF download/view
    
    LEGACY STATES (maintained for compatibility):
    =============================================
    - selected_team: Team/Area selection (Step 1)
    - step: Current step number (1-4)
    - show_recipe: Display recipe from Google Docs
    - current_recipe: Recipe data from Google Docs
    - gdocs_manager: GDocsManager instance
    """
    # ============================================
    # STATE MACHINE - Core Flow States
    # ============================================
    
    # State 1: Action Selection (recipe | mo)
    if 'action_selected' not in st.session_state:
        st.session_state.action_selected = None  # 'recipe' | 'mo' | None
    
    # State 2: Category Selection
    if 'category_selected' not in st.session_state:
        st.session_state.category_selected = None
    # Legacy alias for backward compatibility
    if 'selected_category' not in st.session_state:
        st.session_state.selected_category = None
    
    # State 3: Item Selection
    if 'item_selected' not in st.session_state:
        st.session_state.item_selected = None
    # Legacy alias for backward compatibility
    if 'selected_item' not in st.session_state:
        st.session_state.selected_item = None
    
    # State 4: MO Number (after MO creation)
    if 'mo_number' not in st.session_state:
        st.session_state.mo_number = None
    # Legacy alias for backward compatibility
    if 'created_mo_id' not in st.session_state:
        st.session_state.created_mo_id = None
    
    # State 5: Show Routing PDF
    if 'show_routing' not in st.session_state:
        st.session_state.show_routing = False
    
    # ============================================
    # LEGACY STATES (maintained for compatibility)
    # ============================================
    
    # Team/Area selection (Step 1)
    if 'selected_team' not in st.session_state:
        st.session_state.selected_team = None
    
    # Step counter (1-4)
    if 'step' not in st.session_state:
        st.session_state.step = 1
    
    # Recipe display states
    if 'show_recipe' not in st.session_state:
        st.session_state.show_recipe = False
    if 'current_recipe' not in st.session_state:
        st.session_state.current_recipe = None
    if 'recipe_item_code' not in st.session_state:
        st.session_state.recipe_item_code = None
    
    # Google Docs manager instance
    if 'gdocs_manager' not in st.session_state:
        st.session_state.gdocs_manager = None
    
    # Routing PDF Generator states
    if 'routing_mo_data' not in st.session_state:
        st.session_state.routing_mo_data = None
    if 'routing_mo_id' not in st.session_state:
        st.session_state.routing_mo_id = None
    if 'routing_mo_full_data' not in st.session_state:
        st.session_state.routing_mo_full_data = None
    if 'routing_pdf_file' not in st.session_state:
        st.session_state.routing_pdf_file = None
    if 'routing_pdf_bytes' not in st.session_state:
        st.session_state.routing_pdf_bytes = None


def sync_legacy_states():
    """
    Synchronize legacy state variables with new state machine variables.
    This ensures backward compatibility during migration.
    
    Mappings:
    - selected_category <-> category_selected
    - selected_item <-> item_selected
    - created_mo_id <-> mo_number
    """
    # Sync category
    if 'category_selected' in st.session_state and st.session_state.category_selected is not None:
        st.session_state.selected_category = st.session_state.category_selected
    elif 'selected_category' in st.session_state and st.session_state.selected_category is not None:
        st.session_state.category_selected = st.session_state.selected_category
    
    # Sync item
    if 'item_selected' in st.session_state and st.session_state.item_selected is not None:
        st.session_state.selected_item = st.session_state.item_selected
    elif 'selected_item' in st.session_state and st.session_state.selected_item is not None:
        st.session_state.item_selected = st.session_state.selected_item
    
    # Sync MO number
    if 'mo_number' in st.session_state and st.session_state.mo_number is not None:
        st.session_state.created_mo_id = st.session_state.mo_number
    elif 'created_mo_id' in st.session_state and st.session_state.created_mo_id is not None:
        st.session_state.mo_number = st.session_state.created_mo_id


def reset_state_machine():
    """
    Reset all state machine variables to initial state.
    Called when user clicks "Start Over" or begins a new workflow.
    """
    st.session_state.action_selected = None
    st.session_state.category_selected = None
    st.session_state.selected_category = None
    st.session_state.item_selected = None
    st.session_state.selected_item = None
    st.session_state.mo_number = None
    st.session_state.created_mo_id = None
    st.session_state.show_routing = False
    st.session_state.selected_team = None
    st.session_state.step = 1
    st.session_state.show_recipe = False
    st.session_state.current_recipe = None
    st.session_state.recipe_item_code = None
    st.session_state.routing_mo_data = None
    st.session_state.routing_mo_id = None
    st.session_state.routing_mo_full_data = None
    st.session_state.routing_pdf_file = None
    st.session_state.routing_pdf_bytes = None


# STATE TRANSITIONS DOCUMENTATION
# ===============================
# 
# Valid state transitions:
# 
# 1. INITIAL → action_selected
#    Trigger: User clicks "View Recipe" or "Create MO" button
#    Sets: action_selected = 'recipe' | 'mo'
# 
# 2. action_selected → category_selected
#    Trigger: User selects a category from the filtered list
#    Sets: category_selected = category_name
#    Requires: selected_team must be set
# 
# 3. category_selected → item_selected
#    Trigger: User selects an item from the category
#    Sets: item_selected = item_dict
#    Requires: category_selected must be set
# 
# 4. item_selected + action='mo' → mo_number
#    Trigger: MO creation API call succeeds
#    Sets: mo_number = mo_id (integer)
#    Requires: item_selected and action_selected='mo'
# 
# 5. mo_number → show_routing
#    Trigger: Routing PDF generation completes successfully
#    Sets: show_routing = True
#    Requires: mo_number must be set
# 
# RESET TRANSITION:
#    Trigger: User clicks "Start Over" or resets workflow
#    Action: reset_state_machine() called
#    Result: All states reset to None/False


# Team name mapping: original_name -> display_name
TEAM_NAME_MAPPING = {
    'Alejandro Team': 'Dips and Sauces',
    'Assembly Team': 'Kits',
    'Butcher Team': 'Raw proteins',
    'Grill Team': 'To re heat',
    'Theadora Team': 'Appetizers',
    'Samia Team': 'Dessert',
    'Jorge Team': 'Preparation Bases',
    'Rawad': 'Others',
    'Bread Team': 'Bread'
}

# Expected items by team (for validation)
EXPECTED_ITEMS_BY_TEAM = {
    'Jorge Team': [
        'A1233', 'A1635', 'A1615', 'A1619', 'A1861', 'A1639', 'A1574', 'A1490',
        'A1634', 'A1600', 'A1942', 'A1631', 'A1315', 'A1691', 'A1693', 'A1696',
        'A1646', 'A1640', 'A1176', 'A1903', 'A1011', 'A1650', 'A1641'
    ],
    'Alejandro Team': [
        'A1564', 'A1563', 'A1566', 'A1549', 'A1280', 'A1612', 'A1545', 'A1575',
        'A1550', 'A1565', 'A1616', 'A1649', 'A1544', 'A1871'
    ],
    'Assembly Team': [
        'A1689', 'A1684', 'A1685', 'A1026', 'A1688', 'A1737', 'A1686', 'A1629',
        'A1385', 'A1678'
    ],
    'Samia Team': [
        'A1567', 'A1568', 'A1606', 'A1652', 'A1604', 'A1017', 'A1015', 'A1602',
        'A1603', 'A1633'
    ],
    'Rawad': [
        'A1876', 'A1935', 'A1925', 'A1628', 'A1553', 'A1907'
    ],
    'Theadora Team': [
        'A1632', 'A1613', 'A1607'
    ],
    'Butcher Team': [
        'A1499', 'A1614', 'A1547', 'A1543', 'A1647'
    ],
    'Grill Team': [
        'A1049', 'A1653', 'A1697', 'A1720', 'A1452', 'A1698', 'A1694', 'A1692',
        'A1690', 'A1551', 'A1643'
    ],
    'Bread Team': [
        'A1558', 'A1561'
    ]
}

# Reverse mapping: display_name -> original_name
TEAM_NAME_REVERSE_MAPPING = {v: k for k, v in TEAM_NAME_MAPPING.items()}

# Category icons for better visual accessibility
CATEGORY_ICONS = {
    'Bases & Preparations': '🥘',
    'Dips & Sauces': '🥄',
    'Cooked Proteins': '🍖',
    'Raw & Marinated Proteins': '🥩',
    'Ready to Reheat': '🔥',
    'Desserts': '🍰',
    'Bread & Dough': '🍞',
    'Kits': '📦',
    'Frozen Products': '🧊',
    'Spices & Seasonings': '🌶️',
    'Appetizers & Sides': '🥗',
    'Other Products': '📋'
}

# Professional category mapping based on product characteristics
PROFESSIONAL_CATEGORIES = {
    'Bases & Preparations': {
        'keywords': ['base', 'stock', 'syrup', 'cornstarch', 'eggplant grilled', 'chickpea cooked for garnish', 'beet steamed'],
        'item_codes': ['A1635', 'A1634', 'A1600', 'A1646', 'A1616', 'A1650', 'A1176', 'A1315', 'A1233', 'A1615', 'A1649']
    },
    'Dips & Sauces': {
        'keywords': ['hummus', 'mutabbal', 'mouhammara', 'tarator', 'mayo', 'yogourt', 'yogurt', 'sauce', 'marinade', 'terbyelli', 'confit tomatoes', 'labneh', 'tajin'],
        'item_codes': ['A1564', 'A1563', 'A1566', 'A1565', 'A1545', 'A1550', 'A1544', 'A1549', 'A1280', 'A1871', 'A1612', 'A1575', 'A1049', 'A1452', 'A1720', 'A1640', 'A1551', 'A1553', 'A1026', 'A1641']
    },
    'Cooked Proteins': {
        'keywords': ['cooked', 'sous vide', 'grilled', 'steamed'],
        'item_codes': ['A1619', 'A1861', 'A1574', 'A1490', 'A1942', 'A1903']
    },
    'Raw & Marinated Proteins': {
        'keywords': ['raw', 'marinated', 'kawarma', 'ground'],
        'item_codes': ['A1876', 'A1499', 'A1547', 'A1543', 'A1653', 'A1614', 'A1647', 'A1631']
    },
    'Ready to Reheat': {
        'keywords': ['to reheat', 'reheat', 'dukka', 'potato spices mix'],
        'item_codes': ['A1696', 'A1691', 'A1693', 'A1697', 'A1694', 'A1698', 'A1690', 'A1692', 'A1643', 'A1907']
    },
    'Desserts': {
        'keywords': ['ice cream', 'cookie', 'kunafa', 'safarjal', 'baklava', 'halva'],
        'item_codes': ['A1017', 'A1015', 'A1604', 'A1633', 'A1935', 'A1925']
    },
    'Bread & Dough': {
        'keywords': ['bread', 'dough'],
        'item_codes': ['A1558', 'A1561']
    },
    'Kits': {
        'keywords': ['kit', 'marinated cucumbers', 'falafel not cooked frozen', 'fried pita'],
        'item_codes': ['A1689', 'A1684', 'A1685', 'A1686', 'A1688', 'A1737', 'A1629', 'A1385']
    },
    'Frozen Products': {
        'keywords': ['frozen'],
        'item_codes': ['A1017', 'A1935', 'A1925', 'A1614']
    },
    'Spices & Seasonings': {
        'keywords': ['spice', 'spices'],
        'item_codes': []
    },
    'Appetizers & Sides': {
        'keywords': ['borek', 'kibbeh', 'pickles', 'cucumbers', 'yalanji frozen', 'pistachio kibbeh not cooked', 'shrimp kataifi'],
        'item_codes': ['A1567', 'A1568', 'A1652', 'A1606', 'A1632', 'A1628', 'A1603', 'A1602', 'A1607', 'A1613']
    }
}


def get_professional_category(item: Dict) -> str:
    """
    Assign a professional category to an item based on its title and code.
    
    Args:
        item: Item dictionary with 'title' and 'code' keys
        
    Returns:
        str: Professional category name
    """
    title = (item.get('title', '') or '').lower()
    code = item.get('code', '')
    
    # First check by item code (most reliable)
    for category, data in PROFESSIONAL_CATEGORIES.items():
        if code in data.get('item_codes', []):
            return category
    
    # Then check by keywords in title (order matters - check more specific first)
    # Check for "to reheat" first (more specific), also dukka and potato spices mix
    if 'to reheat' in title or 'reheat' in title or 'dukka' in title or 'potato spices mix' in title:
        return 'Ready to Reheat'
    
    # Check for frozen (but exclude items that go to other categories)
    if 'frozen' in title:
        # Yalanji, Pistachio Kibbeh, and Shrimp Kataifi go to Appetizers & Sides
        if 'yalanji' in title or 'pistachio kibbeh' in title or 'shrimp kataifi' in title:
            return 'Appetizers & Sides'
        # Falafel not cooked frozen goes to Kits
        if 'falafel' in title and 'not cooked' in title:
            return 'Kits'
        return 'Frozen Products'
    
    # Check for kit, marinated cucumbers, falafel not cooked frozen, fried pita
    if 'kit' in title or ('marinated' in title and 'cucumber' in title) or ('falafel' in title and 'not cooked' in title and 'frozen' in title) or ('fried pita' in title):
        return 'Kits'
    
    # Check for bread/dough (but exclude dough for borek which goes to Appetizers & Sides)
    if ('bread' in title or 'dough' in title) and 'borek' not in title:
        return 'Bread & Dough'
    
    # Check for desserts
    if any(dessert in title for dessert in ['ice cream', 'cookie', 'kunafa', 'safarjal', 'baklava', 'halva']):
        return 'Desserts'
    
    # Check for cooked proteins (but not sauces)
    # Exclude eggplant grilled and chickpea cooked for garnish (they go to Bases & Preparations)
    if ('cooked' in title or 'sous vide' in title or 'grilled' in title or 'steamed' in title) and 'sauce' not in title:
        # But exclude items that are clearly bases or sauces, or specific items that go to Bases & Preparations
        if 'base' not in title and 'sauce' not in title and 'eggplant grilled' not in title and 'chickpea cooked for garnish' not in title:
            return 'Cooked Proteins'
    
    # Check for raw/marinated proteins
    if ('raw' in title or 'marinated' in title) and ('protein' in title or any(protein in title for protein in ['lamb', 'beef', 'chicken', 'octopus', 'salmon', 'shrimp', 'kabab', 'shawarma', 'kawarma'])):
        return 'Raw & Marinated Proteins'
    
    # Check for dips and sauces
    if any(dip in title for dip in ['hummus', 'mutabbal', 'mouhammara', 'tarator', 'mayo', 'yogourt', 'yogurt', 'sauce', 'marinade', 'terbyelli', 'confit tomatoes', 'labneh', 'tajin']):
        return 'Dips & Sauces'
    
    # Check for bases and preparations
    if any(base in title for base in ['base', 'stock', 'syrup', 'cornstarch', 'eggplant grilled', 'chickpea cooked for garnish', 'beet steamed']):
        return 'Bases & Preparations'
    
    # Check for spices and seasonings (tajin goes to Dips & Sauces, dukka and potato spices mix go to Ready to Reheat)
    if any(spice in title for spice in ['spice', 'spices']) and 'dukka' not in title and 'tajin' not in title and 'potato spices mix' not in title:
        return 'Spices & Seasonings'
    
    # Check for appetizers and sides
    if any(app in title for app in ['borek', 'kibbeh', 'pickles', 'cucumbers', 'yalanji frozen', 'pistachio kibbeh not cooked', 'shrimp kataifi']):
        return 'Appetizers & Sides'
    
    # Default fallback category (should never reach here if item codes are properly mapped)
    logger.warning(f"Item {code} ({title}) not mapped to any category, using 'Other Products'")
    return 'Other Products'


def get_display_team_name(original_name: str) -> str:
    """Convert original team name to display name"""
    return TEAM_NAME_MAPPING.get(original_name, original_name)


def get_original_team_name(display_name: str) -> str:
    """Convert display team name back to original name"""
    return TEAM_NAME_REVERSE_MAPPING.get(display_name, display_name)


def validate_items_for_team(team_name: str, items: List[Dict]) -> Dict[str, Any]:
    """Validate that expected items are present for a team"""
    expected_codes = EXPECTED_ITEMS_BY_TEAM.get(team_name, [])
    if not expected_codes:
        return {
            'has_validation': False,
            'found': [],
            'missing': [],
            'extra': []
        }
    
    # Get item codes from actual items
    actual_codes = [item.get('code', '') for item in items if item.get('code')]
    
    # Find matches
    found = [code for code in expected_codes if code in actual_codes]
    missing = [code for code in expected_codes if code not in actual_codes]
    extra = [code for code in actual_codes if code not in expected_codes]
    
    return {
        'has_validation': True,
        'found': found,
        'missing': missing,
        'extra': extra,
        'total_expected': len(expected_codes),
        'total_found': len(found),
        'coverage': (len(found) / len(expected_codes) * 100) if expected_codes else 0
    }


def display_cache_status(items: List[Dict], units: List[Dict]):
    """Display cache status in sidebar"""
    st.sidebar.header("📦 Cache Status")

    cache_info = get_cache_info()
    
    # Display last updated time
    if cache_info['last_updated']:
        last_updated = cache_info['last_updated'].strftime("%Y-%m-%d %H:%M:%S")
        st.sidebar.text(f"Last Updated: {last_updated}")

        # Calculate time remaining
        expiry_time = cache_info['last_updated'] + timedelta(hours=6)
        time_remaining = expiry_time - datetime.now()
        hours_remaining = time_remaining.total_seconds() / 3600
        
        if hours_remaining > 0:
            st.sidebar.success(f"Valid for: {hours_remaining:.1f} hours")
        else:
            st.sidebar.warning("Cache expired")

    # Display cache stats
    if items or units:
        st.sidebar.metric("Cached Items", len(items))
        st.sidebar.metric("Cached Units", len(units))

    # Add clear cache button
    if st.sidebar.button("🔄 Clear Cache"):
        clear_all_caches()
        st.sidebar.success("Cache cleared successfully")
        st.rerun()


def get_unit_by_id(unit_id: int, units: List[Dict]) -> str:
    """Get unit name by unit_id"""
    if not units or not unit_id:
        return 'unit'
    
    for unit in units:
        if unit.get('unit_id') == unit_id:
            return unit.get('title', 'unit')
    
    return 'unit'


def get_item_by_article_id(article_id: int, items: List[Dict]) -> Optional[Dict]:
    """Get item details by article_id"""
    if not items:
        return None
    for item in items:
        if item.get('article_id') == article_id:
            return item
    return None


def parse_operation_description(description_str):
    """Parse the JSON string from operation description"""
    try:
        return json.loads(description_str)
    except (json.JSONDecodeError, TypeError):
        return None


def download_image(url, max_size=(100, 100)):
    """Download and resize image from URL"""
    try:
        response = requests.get(url, timeout=10)
        if response.status_code == 200:
            img = PILImage.open(BytesIO(response.content))
            img.thumbnail(max_size, PILImage.Resampling.LANCZOS)
            
            # Save to temporary file
            temp_img = tempfile.NamedTemporaryFile(delete=False, suffix='.png')
            img.save(temp_img.name, 'PNG')
            return temp_img.name
        return None
    except Exception as e:
        logger.error(f"Error downloading image: {e}")
        return None


def get_gdocs_manager():
    """Initialize and return GDocsManager instance"""
    if 'gdocs_manager' not in st.session_state or st.session_state.gdocs_manager is None:
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH')
        if not creds_path:
            return None
        
        # Convert relative path to absolute path
        if not os.path.isabs(creds_path):
            project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
            creds_path = os.path.join(project_root, creds_path)
        
        if not os.path.exists(creds_path):
            logger.error(f"Credentials file not found at: {creds_path}")
            return None
        
        try:
            gdocs_manager = GDocsManager(credentials_path=creds_path)
            gdocs_manager.authenticate()
            st.session_state.gdocs_manager = gdocs_manager
            return gdocs_manager
        except Exception as e:
            logger.error(f"Error authenticating with Google Docs: {e}")
            return None
    
    return st.session_state.gdocs_manager


def parse_date_to_timestamp(date_str: str, date_format: str = "MM/DD/YYYY") -> int:
    """
    Parse a date string in MM/DD/YYYY format to Unix timestamp.
    
    Args:
        date_str: Date string in MM/DD/YYYY format
        date_format: Format of the date string (default: MM/DD/YYYY)
    
    Returns:
        Unix timestamp as integer
    
    Raises:
        ValueError: If date string is invalid
    """
    try:
        if date_format == "MM/DD/YYYY":
            # Parse MM/DD/YYYY format
            month, day, year = map(int, date_str.split('/'))
            date_obj = datetime(year, month, day)
            return int(date_obj.timestamp())
        else:
            raise ValueError(f"Unsupported date format: {date_format}")
    except (ValueError, AttributeError) as e:
        raise ValueError(f"Invalid date format. Expected MM/DD/YYYY, got: {date_str}") from e


def validate_batch_order_input(item_code: str, quantity: float, start_date: str) -> Tuple[bool, str]:
    """
    Validate batch order creation input.
    
    Args:
        item_code: Item code string
        quantity: Quantity as float
        start_date: Start date in MM/DD/YYYY format
    
    Returns:
        Tuple of (is_valid, error_message)
    """
    # Validate item_code
    if not item_code or not item_code.strip():
        return False, "Item code is required"
    
    # Validate quantity
    try:
        quantity_float = float(quantity)
        if quantity_float <= 0:
            return False, "Quantity must be greater than 0"
    except (ValueError, TypeError):
        return False, "Quantity must be a valid number"
    
    # Validate start_date
    if not start_date or not start_date.strip():
        return False, "Start date is required"
    
    try:
        parse_date_to_timestamp(start_date)
    except ValueError as e:
        return False, str(e)
    
    return True, ""


def create_mo_batch(api: APIManager, item_code: str, quantity: float, start_date_str: str) -> Tuple[bool, Optional[int], str]:
    """
    Create a manufacturing order with validation.
    
    Args:
        api: APIManager instance
        item_code: Item code string
        quantity: Quantity as float
        start_date_str: Start date in MM/DD/YYYY format
    
    Returns:
        Tuple of (success, mo_id, message)
    """
    # Validate input
    is_valid, error_msg = validate_batch_order_input(item_code, quantity, start_date_str)
    if not is_valid:
        return False, None, error_msg
    
    try:
        # Parse date to timestamp
        start_date_timestamp = parse_date_to_timestamp(start_date_str)
        
        # Create the manufacturing order
        response = api.create_manufacturing_order(
            item_code=item_code.strip(),
            quantity=float(quantity),
            assigned_id=1,
            start_date=start_date_timestamp
        )
        
        if response.ok:
            # Handle response - could be int or dict
            response_data = response.json()
            
            if isinstance(response_data, int):
                mo_id = response_data
            elif isinstance(response_data, dict):
                mo_id = response_data.get('man_ord_id') or response_data.get('id')
            else:
                return False, None, f"Unexpected response format: {response_data}"
            
            return True, mo_id, f"Manufacturing Order created successfully! (ID: {mo_id})"
        else:
            return False, None, f"Failed to create Manufacturing Order: {response.text}"
    
    except ValueError as e:
        return False, None, f"Validation error: {str(e)}"
    except Exception as e:
        logger.error(f"Error creating MO: {str(e)}")
        return False, None, f"Error: {str(e)}"


def extract_item_info_from_pdf_text(text_content):
    """Extract item name and code from PDF text content"""
    import re
    
    if not text_content:
        return None, None
    
    # Look for item code pattern (A####)
    code_pattern = r'\b(A\d{4})\b'
    code_match = re.search(code_pattern, text_content, re.IGNORECASE)
    extracted_code = code_match.group(1).upper() if code_match else None
    
    # Try to extract item name - look for lines that might contain the item name
    lines = text_content.split('\n')
    extracted_name = None
    
    # Look for the first substantial line that might be the title
    # Usually the item name appears early in the document
    for i, line in enumerate(lines[:20]):  # Check first 20 lines
        line_stripped = line.strip()
        if not line_stripped or len(line_stripped) < 3:
            continue
        
        # Skip common header/footer text
        skip_patterns = ['page', 'recipe', 'ingredients', 'instructions', 'method', 'preparation']
        if any(skip in line_stripped.lower() for skip in skip_patterns):
            continue
        
        # If line contains the code, it's likely the title line
        if extracted_code and extracted_code.upper() in line_stripped.upper():
            # Extract name part (everything before or after the code)
            parts = re.split(r'\b' + re.escape(extracted_code) + r'\b', line_stripped, flags=re.IGNORECASE)
            for part in parts:
                part = part.strip(' -()[]{}')
                if len(part) > 3:  # Meaningful name (reduced from 5 to catch shorter names)
                    # Clean up the name
                    part = re.sub(r'^\s*[-:\s]+\s*', '', part)  # Remove leading dashes/colons
                    part = re.sub(r'\s*[-:\s]+\s*$', '', part)  # Remove trailing dashes/colons
                    if len(part) > 3:
                        extracted_name = part
                        break
            if extracted_name:
                break
        
        # If line looks like a title (short, no numbers except code, contains letters)
        if len(line_stripped) < 100 and re.search(r'[A-Za-z]', line_stripped):
            # Check if it contains common item name patterns
            if re.search(r'[A-Za-z]{3,}', line_stripped):
                if not extracted_name or len(line_stripped) > len(extracted_name):
                    extracted_name = line_stripped.strip(' -:()[]{}')
    
    # Clean up extracted name
    if extracted_name:
        extracted_name = extracted_name.strip(' -:()[]{}')
        # Remove common prefixes/suffixes
        extracted_name = re.sub(r'^(recipe|item|name):?\s*', '', extracted_name, flags=re.IGNORECASE)
        extracted_name = extracted_name.strip()
    
    return extracted_name, extracted_code


def find_recipe_pdf_from_zip(item_code, item_title, zip_path=None):
    """Find recipe PDF from ZIP file by item code or title"""
    import zipfile
    import re
    from PyPDF2 import PdfReader
    from io import BytesIO
    
    # Default path to recipes ZIP
    if zip_path is None:
        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        zip_path = os.path.join(project_root, 'recipes_split', 'recipespdf.zip')
    
    if not os.path.exists(zip_path):
        logger.warning(f"Recipes ZIP not found at: {zip_path}")
        return None
    
    try:
        item_code_lower = item_code.lower().strip()
        item_code_upper = item_code.upper().strip()
        item_title_lower = item_title.lower().strip()
        
        # Create search variations - more comprehensive
        title_variations = [
            item_title_lower,
            item_title_lower.replace(' - ', ' '),
            item_title_lower.replace('-', ' '),
            item_title_lower.split(' - ')[0],
            item_title_lower.split('(')[0].strip(),
            item_title_lower.replace('tray', '').strip(),
            item_title_lower.replace('bag', '').strip(),
            item_title_lower.replace(' - bag', '').strip(),
            item_title_lower.replace(' - tray', '').strip(),
        ]
        # Remove duplicates and empty strings, keep only meaningful variations
        title_variations = list(set([v for v in title_variations if v and len(v) > 2]))
        
        with zipfile.ZipFile(zip_path, 'r') as zip_file:
            # Get all PDF files
            pdf_files = [f for f in zip_file.namelist() if f.lower().endswith('.pdf')]
            
            # Search through each PDF
            for pdf_name in pdf_files:
                try:
                    # Read PDF from ZIP
                    pdf_data = zip_file.read(pdf_name)
                    pdf_reader = PdfReader(BytesIO(pdf_data))
                    
                    # Extract text from all pages
                    full_text = ""
                    for page in pdf_reader.pages:
                        full_text += page.extract_text() + "\n"
                    
                    full_text_lower = full_text.lower()
                    
                    # Extract item info from PDF
                    pdf_item_name, pdf_item_code = extract_item_info_from_pdf_text(full_text)
                    
                    # Check if this PDF contains the item code - be more flexible
                    # First check: direct code match in text (case insensitive)
                    code_in_text = item_code_lower in full_text_lower or item_code_upper in full_text
                    
                    # Also check for code without spaces or with different formatting
                    code_no_spaces = item_code_upper.replace(' ', '')
                    code_in_text = code_in_text or code_no_spaces in full_text.replace(' ', '')
                    
                    # Second check: extracted code matches
                    extracted_code_matches = pdf_item_code and pdf_item_code.upper() == item_code_upper
                    
                    # If code is found in text, it's a match (even if extraction failed)
                    if code_in_text:
                        # Found matching PDF by code - return it with extracted info
                        # Use extracted code if available, otherwise use searched code
                        final_code = pdf_item_code if pdf_item_code else item_code_upper
                        return {
                            'type': 'pdf',
                            'pdf_data': pdf_data,
                            'pdf_name': pdf_name,
                            'text_content': full_text,
                            'item_name': pdf_item_name,  # Name extracted from PDF
                            'item_code': final_code   # Code from PDF or searched code
                        }
                    
                    # Check if this PDF contains any title variation
                    for title_var in title_variations:
                        if title_var and len(title_var) > 2 and title_var in full_text_lower:
                            # If we found a title match, check if code also matches
                            if extracted_code_matches:
                                # Perfect match: both title and code match
                                return {
                                    'type': 'pdf',
                                    'pdf_data': pdf_data,
                                    'pdf_name': pdf_name,
                                    'text_content': full_text,
                                    'item_name': pdf_item_name,
                                    'item_code': pdf_item_code
                                }
                            elif not pdf_item_code:
                                # Title matches but no code found in PDF - still return it
                                # (might be a valid match if code extraction failed)
                                return {
                                    'type': 'pdf',
                                    'pdf_data': pdf_data,
                                    'pdf_name': pdf_name,
                                    'text_content': full_text,
                                    'item_name': pdf_item_name,
                                    'item_code': item_code_upper  # Use searched code as fallback
                                }
                            
                except Exception as e:
                    logger.warning(f"Error reading PDF {pdf_name}: {e}")
                    continue
        
        return None
        
    except Exception as e:
        logger.error(f"Error reading recipes ZIP: {e}")
        return None


def find_recipe_by_item_code(item_code, item_title, doc_url):
    """Find recipe in Google Docs by item code or title - improved search"""
    import re
    gdocs_manager = get_gdocs_manager()
    if not gdocs_manager:
        return None
    
    try:
        text_content, document = gdocs_manager.get_document_content(doc_url)
        lines = text_content.split('\n')
        
        # Normalize search terms
        item_code_lower = item_code.lower().strip() if item_code else ''
        item_code_upper = item_code.upper().strip() if item_code else ''
        item_title_lower = item_title.lower().strip() if item_title else ''
        
        # Log search parameters for debugging
        logger.info(f"Searching for recipe - Code: {item_code}, Title: {item_title}")
        
        # Create variations of the title for better matching
        title_variations = [
            item_title_lower,
            item_title_lower.replace(' - ', ' '),
            item_title_lower.replace('-', ' '),
            item_title_lower.split(' - ')[0],  # Just the main name
            item_title_lower.split('(')[0].strip(),  # Without code in parentheses
            item_title_lower.replace('tray', '').strip(),  # Without "tray"
            item_title_lower.replace('bag', '').strip(),  # Without "bag"
            item_title_lower.replace('tray', '').replace('bag', '').strip(),  # Without both
            item_title_lower.replace('tray', '').strip().replace('  ', ' '),  # Clean up double spaces
            item_title_lower.replace('bag', '').strip().replace('  ', ' '),  # Clean up double spaces
        ]
        # Remove empty variations and duplicates
        title_variations = list(set([v.strip() for v in title_variations if v and len(v.strip()) > 2]))
        
        # Helper function to check if a line looks like a recipe title (more flexible)
        def is_likely_recipe_title(line, has_code=False):
            """Check if line is likely a recipe title - more flexible version"""
            if not line or len(line) > 200:  # Too long to be a title
                return False
            line_lower = line.lower()
            
            # If it has the code, be more lenient
            if has_code:
                # If it ends with colon, it's likely a title
                if line.rstrip().endswith(':'):
                    return True
                # If it's relatively short and contains the code, likely a title
                if len(line) < 100:
                    return True
                # If it matches common title patterns
                if re.match(r'^[A-Za-z0-9\s\-\(\):]+$', line) and len(line) < 80:
                    return True
            
            # Standard title checks
            if line.rstrip().endswith(':'):
                return True
            if gdocs_manager._is_recipe_title(line):
                return True
            return False
        
        # Search for recipe by code or title
        current_recipe = None
        found_recipe = False
        recipe_start_idx = -1
        
        # First pass: find where the recipe starts - prioritize code matches
        for i, line in enumerate(lines):
            line_stripped = line.strip()
            if not line_stripped:
                continue
            
            line_lower = line_stripped.lower()
            line_upper = line_stripped.upper()
            
            # Check if this line contains the item code (case-insensitive)
            # Also check for code patterns like A1551 or A 1551 or A-1551
            code_in_line = False
            if item_code_lower:
                # Direct match
                code_in_line = item_code_lower in line_lower or item_code_upper in line_upper
                # Pattern match (A1551, A 1551, A-1551, etc.)
                if not code_in_line:
                    code_pattern = item_code_lower.replace('a', '').strip()
                    if code_pattern and code_pattern.isdigit():
                        # Try variations: A1551, A 1551, A-1551
                        variations = [
                            f'a{code_pattern}',
                            f'a {code_pattern}',
                            f'a-{code_pattern}',
                            f'a_{code_pattern}',
                        ]
                        code_in_line = any(var in line_lower for var in variations)
            
            if code_in_line:
                # Found the code - check if this line or nearby lines are recipe titles
                if is_likely_recipe_title(line_stripped, has_code=True):
                    found_recipe = True
                    recipe_start_idx = i
                    current_recipe = {
                        'name': line_stripped.replace(':', '').strip(),
                        'ingredients': [],
                        'instructions': [],
                        'full_text': []
                    }
                    break
                
                # If code is in the line but it's not clearly a title, check surrounding lines
                # Check previous line (sometimes code is on a separate line)
                if i > 0:
                    prev_line = lines[i-1].strip()
                    if prev_line and is_likely_recipe_title(prev_line, has_code=False):
                        # Check if previous line also contains code or title
                        prev_lower = prev_line.lower()
                        if any(tv in prev_lower for tv in title_variations if tv):
                            found_recipe = True
                            recipe_start_idx = i - 1
                            current_recipe = {
                                'name': prev_line.replace(':', '').strip(),
                                'ingredients': [],
                                'instructions': [],
                                'full_text': []
                            }
                            break
                
                # Check next few lines for title
                for j in range(i, min(i + 5, len(lines))):
                    next_line = lines[j].strip()
                    if next_line and is_likely_recipe_title(next_line, has_code=False):
                        found_recipe = True
                        recipe_start_idx = j
                        current_recipe = {
                            'name': next_line.replace(':', '').strip(),
                            'ingredients': [],
                            'instructions': [],
                            'full_text': []
                        }
                        break
                
                # If we found code but no clear title nearby, use the line with code as title
                if not found_recipe and len(line_stripped) < 150:
                    found_recipe = True
                    recipe_start_idx = i
                    current_recipe = {
                        'name': line_stripped.replace(':', '').strip(),
                        'ingredients': [],
                        'instructions': [],
                        'full_text': []
                    }
                    break
            
            if found_recipe:
                break
        
        # Second pass: if not found by code, try matching by title variations
        if not found_recipe:
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_lower = line_stripped.lower()
                
                # Check if this line matches any variation of the title
                for title_var in title_variations:
                    if title_var and len(title_var) > 3:
                        # Check if title variation is in the line (word boundary matching)
                        # Use word boundaries to avoid partial matches
                        pattern = r'\b' + re.escape(title_var) + r'\b'
                        if re.search(pattern, line_lower, re.IGNORECASE):
                            if is_likely_recipe_title(line_stripped, has_code=False):
                                found_recipe = True
                                recipe_start_idx = i
                                current_recipe = {
                                    'name': line_stripped.replace(':', '').strip(),
                                    'ingredients': [],
                                    'instructions': [],
                                    'full_text': []
                                }
                                break
                if found_recipe:
                    break
        
        # Third pass: very flexible - any line with code (fallback)
        if not found_recipe and item_code_lower:
            for i, line in enumerate(lines):
                line_stripped = line.strip()
                if not line_stripped:
                    continue
                
                line_lower = line_stripped.lower()
                
                # More flexible: code anywhere in line, accept as recipe start
                code_in_line = item_code_lower in line_lower or item_code_upper in line_upper
                
                # Also check for code pattern variations (A1551, A 1551, A-1551)
                if not code_in_line and item_code_lower.startswith('a') and len(item_code_lower) == 5:
                    code_pattern = item_code_lower.replace('a', '').strip()
                    if code_pattern and code_pattern.isdigit():
                        variations = [
                            f'a{code_pattern}',
                            f'a {code_pattern}',
                            f'a-{code_pattern}',
                            f'a_{code_pattern}',
                        ]
                        code_in_line = any(var in line_lower for var in variations)
                
                if code_in_line:
                    found_recipe = True
                    recipe_start_idx = i
                    current_recipe = {
                        'name': line_stripped.replace(':', '').strip(),
                        'ingredients': [],
                        'instructions': [],
                        'full_text': []
                    }
                    break
        
        # Second pass: collect recipe content
        if found_recipe and current_recipe:
            for i in range(recipe_start_idx + 1, len(lines)):
                line_stripped = lines[i].strip()
                
                # Stop if we hit another recipe title (but not the same one)
                if line_stripped:
                    if gdocs_manager._is_recipe_title(line_stripped) and current_recipe['name'].lower() not in line_stripped.lower():
                        # Check if it's a different recipe by looking for item codes
                        # Only break if we find a different item code
                        line_lower = line_stripped.lower()
                        # If this line has a different item code pattern (A####), it's a new recipe
                        import re
                        codes_in_line = re.findall(r'a\d{4}', line_lower)
                        if codes_in_line and item_code_lower not in codes_in_line:
                            break
                    
                    current_recipe['full_text'].append(line_stripped)
                    
                    # Try to categorize as ingredient or instruction
                    if gdocs_manager._is_ingredient_line(line_stripped):
                        current_recipe['ingredients'].append(line_stripped)
                    elif gdocs_manager._is_instruction_line(line_stripped):
                        current_recipe['instructions'].append(line_stripped)
                    else:
                        # Default: add to instructions if it looks like a sentence
                        if line_stripped.endswith('.') or len(line_stripped) > 50:
                            current_recipe['instructions'].append(line_stripped)
                        else:
                            current_recipe['ingredients'].append(line_stripped)
        
        if found_recipe and current_recipe:
            logger.info(f"Recipe found for {item_code}: {current_recipe['name']}")
            return current_recipe
        
        logger.warning(f"Recipe not found for code: {item_code}, title: {item_title}")
        return None
    except HttpError as e:
        error_msg = str(e)
        error_code = e.resp.status if hasattr(e, 'resp') else None
        logger.error(f"Google Docs API error ({error_code}): {error_msg}")
        
        # Store error info for display
        error_info = {
            'type': 'general',
            'message': f'Error accessing Google Docs',
            'details': error_msg,
            'code': error_code
        }
        
        # Check for specific error types
        if error_code == 401 or "UNAUTHENTICATED" in error_msg or "CREDENTIALS_MISSING" in error_msg:
            error_info['type'] = 'authentication'
            error_info['message'] = 'Authentication failed. Check your service account credentials.'
        elif error_code == 403:
            if "SERVICE_DISABLED" in error_msg or "API has not been used" in error_msg or "is disabled" in error_msg:
                error_info['type'] = 'api_disabled'
                error_info['message'] = 'Google Docs API is not enabled for this project.'
            else:
                error_info['type'] = 'permission'
                error_info['message'] = 'Permission denied. Check if the service account has access to the document.'
        elif error_code == 404:
            error_info['type'] = 'not_found'
            error_info['message'] = 'Document not found. Check the document URL.'
        
        st.session_state.recipe_error = error_info
        return None
    except Exception as e:
        error_msg = str(e)
        logger.error(f"Error finding recipe: {error_msg}")
        # Store error info for display
        st.session_state.recipe_error = {
            'type': 'general',
            'message': f'Error accessing Google Docs: {error_msg}',
            'details': error_msg
        }
        return None


def generate_recipe_pdf_from_gdocs(recipe_data, item_code, item_title):
    """Generate PDF from Google Docs recipe data"""
    # Create a temporary file for the PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_filename = temp_pdf.name
    temp_pdf.close()
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, 
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'RecipeTitle',
        parent=styles['Heading1'],
        fontSize=20,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    section_style = ParagraphStyle(
        'SectionStyle',
        parent=styles['Heading2'],
        fontSize=14,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=12,
        spaceBefore=16,
        fontName='Helvetica-Bold'
    )
    
    body_style = ParagraphStyle(
        'BodyStyle',
        parent=styles['Normal'],
        fontSize=11,
        leading=14,
        spaceAfter=8
    )
    
    # Add title
    title = Paragraph(item_title, title_style)
    elements.append(title)
    
    # Add item code
    code_para = Paragraph(f'<b>Item Code:</b> {item_code}', body_style)
    elements.append(code_para)
    elements.append(Spacer(1, 0.2*inch))
    
    # Add ingredients section
    if recipe_data.get('ingredients'):
        ingredients_title = Paragraph('INGREDIENTS', section_style)
        elements.append(ingredients_title)
        
        for ingredient in recipe_data['ingredients']:
            ing_para = Paragraph(f"• {ingredient}", body_style)
            elements.append(ing_para)
        
        elements.append(Spacer(1, 0.2*inch))
    
    # Add instructions section
    if recipe_data.get('instructions'):
        instructions_title = Paragraph('INSTRUCTIONS', section_style)
        elements.append(instructions_title)
        
        for i, instruction in enumerate(recipe_data['instructions'], 1):
            inst_para = Paragraph(f"{i}. {instruction}", body_style)
            elements.append(inst_para)
    
    # If no structured data, use full text
    if not recipe_data.get('ingredients') and not recipe_data.get('instructions'):
        if recipe_data.get('full_text'):
            for line in recipe_data['full_text']:
                para = Paragraph(line, body_style)
                elements.append(para)
    
    # Build PDF
    doc.build(elements)
    return pdf_filename


def generate_mo_recipe_pdf(mo_data, mo_full_data, items_cache, units_cache):
    """Generate PDF from MO data with BOM summary and operations"""
    # Create a temporary file for the PDF
    temp_pdf = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
    pdf_filename = temp_pdf.name
    temp_pdf.close()
    
    # Create PDF document
    doc = SimpleDocTemplate(pdf_filename, pagesize=letter, 
                           rightMargin=0.5*inch, leftMargin=0.5*inch,
                           topMargin=0.75*inch, bottomMargin=0.5*inch)
    
    # Container for PDF elements
    elements = []
    
    # Styles
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle(
        'CustomTitle',
        parent=styles['Heading1'],
        fontSize=18,
        textColor=colors.HexColor('#1E3A8A'),
        spaceAfter=8,
        alignment=TA_CENTER,
        fontName='Helvetica-Bold'
    )
    
    subtitle_style = ParagraphStyle(
        'CustomSubtitle',
        parent=styles['Normal'],
        fontSize=12,
        textColor=colors.HexColor('#4B5563'),
        spaceAfter=20,
        alignment=TA_CENTER,
        fontName='Helvetica'
    )
    
    section_header_style = ParagraphStyle(
        'SectionHeader',
        parent=styles['Heading2'],
        fontSize=12,
        fontName='Helvetica-Bold',
        spaceAfter=12,
        alignment=TA_LEFT
    )
    
    header_style = ParagraphStyle(
        'CustomHeader',
        parent=styles['Normal'],
        fontSize=10,
        fontName='Helvetica-Bold',
        textColor=colors.white,
        alignment=TA_CENTER
    )
    
    cell_style = ParagraphStyle(
        'CustomCell',
        parent=styles['Normal'],
        fontSize=9,
        fontName='Helvetica',
        leading=12
    )
    
    # Add title
    title = Paragraph(mo_data.get('item_title', 'Recipe'), title_style)
    elements.append(title)
    
    # Add expected output
    quantity = mo_data.get('quantity', 0)
    unit = mo_data.get('unit', '')
    expected_output = Paragraph(f'Expected Output: {quantity} {unit}', subtitle_style)
    elements.append(expected_output)
    elements.append(Spacer(1, 0.1*inch))
    
    # Add lot code and barcode if available
    lot_code = mo_data.get('lot_code')
    if lot_code:
        # Create a centered table for lot code and barcode
        lot_code_para = Paragraph(f'<b>Lot Code: {lot_code}</b>', subtitle_style)
        lot_barcode = BarCode128(lot_code, width=2.5*inch, height=0.5*inch)
        
        # Create table to center the barcode
        lot_table_data = [
            [lot_code_para],
            [lot_barcode]
        ]
        lot_table = Table(lot_table_data, colWidths=[7.5*inch])
        lot_table.setStyle(TableStyle([
            ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
            ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ]))
        elements.append(lot_table)
        elements.append(Spacer(1, 0.2*inch))
    
    # Add Recipe Summary section
    recipe_summary_title = Paragraph('Recipe Summary', section_header_style)
    elements.append(recipe_summary_title)
    
    # Build BOM summary table
    bom_table_data = []
    bom_header_row = [
        Paragraph('INGREDIENTS', header_style),
        Paragraph('QUANTITY', header_style),
        Paragraph('UNIT', header_style)
    ]
    bom_table_data.append(bom_header_row)
    
    # Process parts
    parts = mo_full_data.get('parts', [])
    for part in parts:
        article_id = part.get('article_id')
        booked = part.get('booked', 0)
        
        # Get item details
        item = get_item_by_article_id(article_id, items_cache)
        if item:
            item_title = item.get('title', 'Unknown Item')
            unit_id = item.get('unit_id')
            unit = get_unit_by_id(unit_id, units_cache)
            
            # Format quantity
            qty_display = f"{booked:.2f}".rstrip('0').rstrip('.')
            
            row = [
                Paragraph(item_title, cell_style),
                Paragraph(qty_display, cell_style),
                Paragraph(unit, cell_style)
            ]
            bom_table_data.append(row)
    
    # Create BOM table
    bom_col_widths = [4.5*inch, 1.5*inch, 1.5*inch]
    bom_table = Table(bom_table_data, colWidths=bom_col_widths, repeatRows=1)
    
    # Style the BOM table
    bom_table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#6B7280')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (0, -1), 'LEFT'),
        ('ALIGN', (1, 1), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 1), (-1, -1), 'MIDDLE'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 6),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    
    bom_table.setStyle(bom_table_style)
    elements.append(bom_table)
    elements.append(Spacer(1, 0.3*inch))
    
    # Add Operations/Routing section
    # Prepare operations table data
    table_data = []
    
    # Header row
    header_row = [
        Paragraph('STEP', header_style),
        Paragraph('INGREDIENTS', header_style),
        Paragraph('PROCEDURE', header_style),
        Paragraph('EQUIPMENT', header_style)
    ]
    table_data.append(header_row)
    
    # Process operations
    operations = mo_full_data.get('operations', [])
    temp_image_files = []  # Keep track of temp files to clean up
    
    for operation in operations:
        description_str = operation.get('description', '{}')
        operation_data = parse_operation_description(description_str)
        
        if not operation_data:
            continue
        
        step_name = operation_data.get('step', 'Step')
        name = operation_data.get('name', '')
        step_text = f"{step_name}<br/>{name}" if name else step_name
        
        # Build ingredients text
        ingredients_list = operation_data.get('ingredients', [])
        ingredients_text = ''
        for ing in ingredients_list:
            item = ing.get('item', '')
            amount = ing.get('amount', '')
            ingredients_text += f"• {item} – {amount}<br/>"
        
        # Build procedure text
        procedure_list = operation_data.get('procedure', [])
        procedure_text = ''
        for proc in procedure_list:
            step_num = proc.get('step', '')
            instruction = proc.get('instruction', '')
            procedure_text += f"{step_num}. {instruction}<br/>"
        
        # Handle equipment with image
        equipment_list = operation_data.get('equipment', [])
        equipment_cell_content = []
        
        if equipment_list:
            equipment = equipment_list[0]
            equipment_name = equipment.get('name', '')
            equipment_image_url = equipment.get('image', '')
            
            if equipment_name:
                equipment_cell_content.append(Paragraph(equipment_name, cell_style))
            
            if equipment_image_url:
                # Download and add image
                img_path = download_image(equipment_image_url, max_size=(80, 80))
                if img_path:
                    temp_image_files.append(img_path)
                    try:
                        img = Image(img_path, width=80, height=80)
                        equipment_cell_content.append(Spacer(1, 0.05*inch))
                        equipment_cell_content.append(img)
                    except Exception as e:
                        logger.error(f"Error adding image to PDF: {e}")
        
        # Create row
        row = [
            Paragraph(step_text, cell_style),
            Paragraph(ingredients_text, cell_style),
            Paragraph(procedure_text, cell_style),
            equipment_cell_content if equipment_cell_content else Paragraph('', cell_style)
        ]
        table_data.append(row)
    
    # Create operations table
    col_widths = [1.2*inch, 2.2*inch, 2.8*inch, 1.3*inch]
    operations_table = Table(table_data, colWidths=col_widths, repeatRows=1)
    
    # Style the operations table
    operations_table_style = TableStyle([
        # Header styling
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#1E3A8A')),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.white),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, 0), 10),
        ('ALIGN', (0, 0), (-1, 0), 'CENTER'),
        ('VALIGN', (0, 0), (-1, 0), 'MIDDLE'),
        
        # Body styling
        ('BACKGROUND', (0, 1), (-1, -1), colors.white),
        ('TEXTCOLOR', (0, 1), (-1, -1), colors.black),
        ('FONTNAME', (0, 1), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 1), (-1, -1), 9),
        ('ALIGN', (0, 1), (-1, -1), 'LEFT'),
        ('VALIGN', (0, 1), (-1, -1), 'TOP'),
        
        # Grid
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
        ('LINEBELOW', (0, 0), (-1, 0), 2, colors.black),
        
        # Padding
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LEFTPADDING', (0, 0), (-1, -1), 6),
        ('RIGHTPADDING', (0, 0), (-1, -1), 6),
    ])
    
    operations_table.setStyle(operations_table_style)
    elements.append(operations_table)
    
    # Build PDF
    doc.build(elements)
    
    # Clean up temporary image files
    for img_file in temp_image_files:
        try:
            os.unlink(img_file)
        except Exception:
            pass
    
    return pdf_filename


def main():
    """Main application function"""
    # Custom header with logo and title
    st.markdown("""
    <style>
    .mo-recipes-header {
        display: flex;
        align-items: center;
        justify-content: center;
        gap: 15px;
        padding: 20px 0;
        margin-bottom: 10px;
    }
    .mo-recipes-logo {
        font-size: 52px;
        line-height: 1;
        filter: drop-shadow(0 3px 6px rgba(0,0,0,0.15));
        animation: pulse 2s ease-in-out infinite;
    }
    @keyframes pulse {
        0%, 100% { transform: scale(1); }
        50% { transform: scale(1.05); }
    }
    .mo-recipes-title {
        font-size: 44px;
        font-weight: 700;
        background: linear-gradient(135deg, #1E3A8A 0%, #3B82F6 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        background-clip: text;
        margin: 0;
        letter-spacing: -0.5px;
        text-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    .mo-recipes-subtitle {
        text-align: center;
        color: #4B5563;
        font-size: 16px;
        margin-top: -5px;
        margin-bottom: 20px;
        font-weight: 400;
    }
    </style>
    <div class="mo-recipes-header">
        <div class="mo-recipes-logo">🏭📋</div>
        <h1 class="mo-recipes-title">MO and Recipes</h1>
    </div>
    """, unsafe_allow_html=True)
    
    st.markdown('<p class="mo-recipes-subtitle">Create MOs and print recipes</p>', unsafe_allow_html=True)

    # Initialize session state
    initialize_session_state()
    
    # Sync legacy states with new state machine
    sync_legacy_states()

    # Initialize API Manager with error handling
    try:
        api = APIManager()
    except (ValueError, KeyError, TypeError) as e:
        st.error(f"❌ Error initializing API Manager: {str(e)}")
        st.info("""
        **Please check your configuration:**
        1. Verify that `MRPEASY_API_KEY` and `MRPEASY_API_SECRET` are set in `.streamlit/secrets.toml`
        2. Make sure the secrets file exists and is properly formatted
        3. Restart the Streamlit app after updating secrets
        """)
        st.stop()
        return

    # Get API credentials for cache key
    api_key = secrets.get('MRPEASY_API_KEY', '')
    api_secret = secrets.get('MRPEASY_API_SECRET', '')

    # Load cached data (will use existing cache if valid, otherwise fetch new)
    with st.spinner("Loading data..."):
        all_items = fetch_items_cache(api_key, api_secret)
        all_units = fetch_units_cache(api_key, api_secret)
        
        # Update cache metadata on first load in this session
        cache_info = get_cache_info()
        if not cache_info['items_loaded'] or not cache_info['units_loaded']:
            cache_info['items_loaded'] = True
            cache_info['units_loaded'] = True
            cache_info['last_updated'] = datetime.now()

    # Display cache status in sidebar
    display_cache_status(all_items, all_units)
    
    # Filter items where is_raw = false
    filtered_items = [item for item in all_items if item.get('is_raw') == False]
    
    # Allowed item codes (from production schedule)
    ALLOWED_ITEM_CODES = {
        # JORGE TEAM
        'A1233', 'A1635', 'A1631', 'A1619', 'A1861', 'A1639', 'A1574', 'A1490', 
        'A1315', 'A1600', 'A1646', 'A1011', 'A1691', 'A1176', 'A1696', 'A1903', 
        'A1640', 'A1615', 'A1650', 'A1634', 'A1693', 'A1942', 'A1641',
        # ALEJANDRO TEAM
        'A1564', 'A1575', 'A1616', 'A1565', 'A1871', 'A1563', 'A1550', 'A1545', 
        'A1280', 'A1544', 'A1549', 'A1612', 'A1649',
        # ASSEMBLY TEAM
        'A1689', 'A1737', 'A1629', 'A1684', 'A1688', 'A1685', 'A1026', 'A1686', 
        'A1385',
        # SAMIA TEAM
        'A1567', 'A1652', 'A1633', 'A1017', 'A1015', 'A1568', 'A1606', 'A1602', 
        'A1603', 'A1604',
        # RAWAD TEAM
        'A1876', 'A1935', 'A1925', 'A1628', 'A1553', 'A1907',
        # THEODORA TEAM
        'A1607', 'A1613', 'A1632',
        # BUTCHER TEAM
        'A1499', 'A1547', 'A1543', 'A1614', 'A1647',
        # GRILL TEAM
        'A1697', 'A1653', 'A1694', 'A1551', 'A1049', 'A1452', 'A1698', 'A1643', 
        'A1690', 'A1720', 'A1692',
        # BREAD TEAM
        'A1558', 'A1561'
    }
    
    # Filter to only show allowed item codes
    filtered_items = [item for item in filtered_items if item.get('code') in ALLOWED_ITEM_CODES]
    
    # Add validation info in sidebar if a team is selected
    if st.session_state.selected_team:
        team_items = [item for item in filtered_items if item.get('custom_44680') == st.session_state.selected_team]
        validation = validate_items_for_team(st.session_state.selected_team, team_items)
        
        if validation['has_validation']:
            st.sidebar.divider()
            st.sidebar.header("📊 Item Validation")
            st.sidebar.metric("Items Found", f"{validation['total_found']}/{validation['total_expected']}")
            st.sidebar.metric("Coverage", f"{validation['coverage']:.1f}%")
            
            if validation['missing']:
                with st.sidebar.expander("⚠️ Missing Items"):
                    for code in validation['missing']:
                        st.sidebar.text(f"• {code}")
            
            if validation['extra']:
                with st.sidebar.expander("ℹ️ Extra Items"):
                    for code in validation['extra'][:10]:  # Show first 10
                        st.sidebar.text(f"• {code}")
                    if len(validation['extra']) > 10:
                        st.sidebar.text(f"... and {len(validation['extra']) - 10} more")

    # Extract unique teams (custom_44680)
    teams = sorted(list(set([item.get('custom_44680') for item in filtered_items if item.get('custom_44680')])))
    
    # Sort teams by display name for better organization
    teams = sorted(teams, key=lambda t: get_display_team_name(t))

    # ============================================
    # ACTION SELECTION - Initial Decision Point
    # ============================================
    # Show action selection if not already selected
    if st.session_state.action_selected is None:
        st.markdown('<div style="margin: 30px 0;"></div>', unsafe_allow_html=True)
        st.header("🎯 Select Action")
        st.markdown("Choose what you want to do:")
        
        # Create two columns for action buttons
        col1, col2 = st.columns(2)
        
        with col1:
            if st.button(
                "📋 Print Recipe",
                key="action_print_recipe",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.action_selected = 'recipe'
                st.rerun()
        
        with col2:
            if st.button(
                "🏭 Generate MO",
                key="action_generate_mo",
                use_container_width=True,
                type="primary"
            ):
                st.session_state.action_selected = 'mo'
                st.rerun()
        
        st.markdown('<div style="margin: 40px 0;"></div>', unsafe_allow_html=True)
        st.info("💡 **Print Recipe**: View and download recipe PDFs from Google Docs\n\n🏭 **Generate MO**: Create a Manufacturing Order and generate routing PDF")
        
        # Stop here if no action selected
        return
    
    # ============================================
    # MAIN FLOW - Continue only if action is selected
    # ============================================
    
    # Show selected action info
    action_display = "📋 Print Recipe" if st.session_state.action_selected == 'recipe' else "🏭 Generate MO"
    st.info(f"**Selected Action:** {action_display}")
    
    # Back button to change action
    if st.button("← Change Action", key="back_to_action_selection"):
        st.session_state.action_selected = None
        reset_state_machine()
        st.rerun()
    
    st.divider()

    # ============================================
    # STEP 2: SELECT CATEGORY (from ERP Quick MO Creator)
    # ============================================
    st.header("Step 2: Select Category")
    
    # Add refresh button next to header
    col1, col2 = st.columns([3, 1])
    with col1:
        pass  # Header is already shown above
    with col2:
        if st.button("🔄 Refresh Data", help="Clear cache and reload items from API"):
            clear_all_caches()
            st.success("Cache cleared! Reloading...")
            st.rerun()
    
    # Extract unique professional categories from all filtered items
    # Assign professional category to each item
    categories = []
    if filtered_items:
        for item in filtered_items:
            item['professional_category'] = get_professional_category(item)
        
        # Get unique professional categories, sorted alphabetically
        categories = sorted(list(set([item.get('professional_category', 'Other Products') for item in filtered_items])))
    
    # Debug info (can be removed later)
    if not categories:
        st.warning("⚠️ No categories found. This might indicate:")
        st.info("""
        - Items are still loading (check sidebar for cache status)
        - Items don't match the allowed item codes filter
        - All items are filtered out (is_raw = True)
        """)
        
        # Show debug info
        with st.expander("🔍 Debug Information"):
            st.write(f"**Total items loaded:** {len(all_items)}")
            st.write(f"**Filtered items (is_raw=False):** {len([item for item in all_items if item.get('is_raw') == False])}")
            st.write(f"**Filtered items (allowed codes):** {len(filtered_items)}")
            
            # Show sample items
            if all_items:
                sample_item = all_items[0]
                st.write(f"**Sample item keys:** {list(sample_item.keys())[:10]}...")
                st.write(f"**Sample item code:** {sample_item.get('code', 'N/A')}")
                st.write(f"**Sample item is_raw:** {sample_item.get('is_raw', 'N/A')}")
                st.write(f"**Sample item in allowed codes:** {sample_item.get('code') in ALLOWED_ITEM_CODES if sample_item.get('code') else False}")
            
            if filtered_items:
                sample_filtered = filtered_items[0]
                st.write(f"**Sample filtered item code:** {sample_filtered.get('code', 'N/A')}")
                st.write(f"**Sample filtered item title:** {sample_filtered.get('title', 'N/A')}")
                st.write(f"**Sample filtered professional_category:** {sample_filtered.get('professional_category', 'N/A')}")
            
            # Show category distribution
            if filtered_items:
                category_counts = {}
                for item in filtered_items:
                    cat = item.get('professional_category', 'Other Products')
                    category_counts[cat] = category_counts.get(cat, 0) + 1
                st.write(f"**Category distribution:** {category_counts}")
    
    # Create columns for category buttons (3 per row for better touchscreen UX)
    cols_per_row = 3
    category_cols = st.columns(cols_per_row)
    
    if categories:
        for idx, category in enumerate(categories):
            col_idx = idx % cols_per_row
            with category_cols[col_idx]:
                # Get icon for category, default to 📋 if not found
                icon = CATEGORY_ICONS.get(category, '📋')
                # Create button label with icon
                button_label = f"{icon} {category}"
                
                if st.button(
                    button_label,
                    key=f"category_{category}",
                    use_container_width=True,
                    type="primary" if st.session_state.category_selected == category else "secondary"
                ):
                    st.session_state.category_selected = category
                    st.session_state.selected_category = category  # Legacy sync
                    st.session_state.item_selected = None
                    st.session_state.selected_item = None  # Legacy sync
                    st.session_state.step = 3
                    st.rerun()
    else:
        st.info("💡 Waiting for items to load... If this persists:")
        st.write("1. Check the sidebar for cache status")
        st.write("2. Click '🔄 Refresh Data' button above to reload from API")
        st.write("3. Check the debug information below for details")
        st.write("4. Verify API credentials in secrets.toml")

    # ============================================
    # STEP 3: SELECT ITEM (from ERP Quick MO Creator)
    # ============================================
    if st.session_state.category_selected:
        st.divider()
        st.header("Step 3: Select Item")
        # Get icon for selected category
        selected_icon = CATEGORY_ICONS.get(st.session_state.category_selected, '📋')
        st.info(f"**Category:** {selected_icon} {st.session_state.category_selected}")
        
        # Filter items by selected professional category
        category_items = [
            item for item in filtered_items 
            if item.get('professional_category') == st.session_state.category_selected
        ]
        
        # Sort by title alphabetically
        category_items = sorted(category_items, key=lambda x: x.get('title', ''))
        
        # Create columns for item buttons
        item_cols = st.columns(cols_per_row)
        
        for idx, item in enumerate(category_items):
            col_idx = idx % cols_per_row
            item_title = item.get('title', 'Unknown')
            item_code = item.get('code', '')
            
            with item_cols[col_idx]:
                if st.button(
                    f"{item_title}\n({item_code})",
                    key=f"item_{item_code}",
                    use_container_width=True,
                    type="primary" if (st.session_state.item_selected == item or st.session_state.selected_item == item) else "secondary"
                ):
                    st.session_state.item_selected = item
                    st.session_state.selected_item = item  # Legacy sync
                    # Clear recipe state when selecting a new item (for Recipe Viewer)
                    st.session_state.current_recipe = None
                    st.session_state.recipe_item_code = None
                    st.session_state.step = 4
                    st.rerun()

    # ============================================
    # STEP 4: RECIPE VIEWER OR CREATE MO
    # ============================================
    # Use item_selected if available, otherwise fall back to selected_item for compatibility
    current_item = st.session_state.item_selected or st.session_state.selected_item
    
    if current_item:
        selected_item = current_item  # Use the current item (from item_selected or selected_item)
        
        # ============================================
        # FLOW: RECIPE VIEWER (action_selected == "recipe")
        # ============================================
        if st.session_state.action_selected == 'recipe':
            st.divider()
            st.header("📋 Recipe Viewer")
            st.success(f"**Selected Item:** {selected_item.get('title')} ({selected_item.get('code')})")
            
            # Get Google Docs configuration
            # Try st.secrets first (Streamlit native), then fallback to config.py secrets
            try:
                if hasattr(st, 'secrets') and hasattr(st.secrets, 'get'):
                    recipes_doc_url = st.secrets.get('RECIPES_DOCS_URL', '') or secrets.get('RECIPES_DOCS_URL', '')
                    use_google_docs_recipes = st.secrets.get('USE_GOOGLE_DOCS_RECIPES', False) or secrets.get('USE_GOOGLE_DOCS_RECIPES', False)
                else:
                    recipes_doc_url = secrets.get('RECIPES_DOCS_URL', '')
                    use_google_docs_recipes = secrets.get('USE_GOOGLE_DOCS_RECIPES', False)
            except (AttributeError, KeyError, TypeError):
                # Fallback to config.py secrets
                recipes_doc_url = secrets.get('RECIPES_DOCS_URL', '')
                use_google_docs_recipes = secrets.get('USE_GOOGLE_DOCS_RECIPES', False)
            
            # Try to load recipe from ZIP first, then Google Docs as fallback
            if not st.session_state.get('current_recipe') or st.session_state.get('recipe_item_code') != selected_item.get('code'):
                recipe = None
                recipe_source = None
                
                # First, try to find recipe in ZIP file
                with st.spinner("Searching for recipe in PDF files..."):
                    recipe_pdf = find_recipe_pdf_from_zip(
                        selected_item.get('code'),
                        selected_item.get('title')
                    )
                    if recipe_pdf:
                        recipe = recipe_pdf
                        recipe_source = 'zip'
                
                # If not found in ZIP, try Google Docs
                if not recipe and use_google_docs_recipes and recipes_doc_url:
                    with st.spinner("Loading recipe from Google Docs..."):
                        recipe_gdocs = find_recipe_by_item_code(
                            selected_item.get('code'),
                            selected_item.get('title'),
                            recipes_doc_url
                        )
                        if recipe_gdocs:
                            recipe = recipe_gdocs
                            recipe_source = 'gdocs'
                
                # Store recipe in session state
                if recipe:
                    st.session_state.current_recipe = recipe
                    st.session_state.recipe_item_code = selected_item.get('code')
                    st.session_state.recipe_source = recipe_source
                    st.rerun()
                else:
                    # No recipe found in either source
                    if not use_google_docs_recipes or not recipes_doc_url:
                        st.warning("⚠️ Recipe sources not configured.")
                        st.info("""
                        **Available sources:**
                        - PDF ZIP file (recipes_split/recipespdf.zip) - ✅ Checked
                        - Google Docs - ❌ Not configured
                        
                        **To enable Google Docs:**
                        Configure `RECIPES_DOCS_URL` and `USE_GOOGLE_DOCS_RECIPES` in your secrets file.
                        """)
                    else:
                        st.warning(f"Recipe not found for item: {selected_item.get('code')} ({selected_item.get('title')})")
                        st.info("💡 Recipe not found in PDF ZIP or Google Docs. Make sure the recipe exists in either source.")
                    
                    # Debug information
                    with st.expander("🔍 Debug - Search Information"):
                        st.write(f"**Searching for:**")
                        st.write(f"- Item Code: `{selected_item.get('code')}`")
                        st.write(f"- Item Title: `{selected_item.get('title')}`")
                        st.write("")
                        st.write("**Sources checked:**")
                        st.write("1. ✅ PDF ZIP file (recipes_split/recipespdf.zip)")
                        if use_google_docs_recipes and recipes_doc_url:
                            st.write(f"2. ✅ Google Docs: {recipes_doc_url}")
                        else:
                            st.write("2. ❌ Google Docs (not configured)")
                        
                        # Check ZIP file and search details
                        project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
                        zip_path = os.path.join(project_root, 'recipes_split', 'recipespdf.zip')
                        if os.path.exists(zip_path):
                            st.write(f"")
                            st.write(f"**ZIP file found:** ✅ `{zip_path}`")
                            try:
                                import zipfile
                                from PyPDF2 import PdfReader
                                from io import BytesIO
                                
                                with zipfile.ZipFile(zip_path, 'r') as z:
                                    pdf_files = [f for f in z.namelist() if f.lower().endswith('.pdf')]
                                    st.write(f"**PDFs in ZIP:** {len(pdf_files)}")
                                    
                                    # Show search variations
                                    item_code = selected_item.get('code', '')
                                    item_title = selected_item.get('title', '')
                                    item_title_lower = item_title.lower().strip()
                                    
                                    title_variations = [
                                        item_title_lower,
                                        item_title_lower.replace(' - ', ' '),
                                        item_title_lower.replace('-', ' '),
                                        item_title_lower.split(' - ')[0],
                                        item_title_lower.split('(')[0].strip(),
                                        item_title_lower.replace('tray', '').strip(),
                                        item_title_lower.replace('bag', '').strip(),
                                    ]
                                    title_variations = list(set([v for v in title_variations if v and len(v) > 2]))
                                    
                                    st.write("")
                                    st.write("**Search variations being used:**")
                                    st.write(f"- Code: `{item_code}` (case-insensitive)")
                                    st.write(f"- Title variations: {', '.join([f'`{v}`' for v in title_variations[:5]])}")
                                    
                                    # Try to find matches
                                    st.write("")
                                    st.write("**Scanning PDFs for matches...**")
                                    matches_found = []
                                    for pdf_name in pdf_files[:10]:  # Check first 10 PDFs
                                        try:
                                            pdf_data = z.read(pdf_name)
                                            pdf_reader = PdfReader(BytesIO(pdf_data))
                                            full_text = ""
                                            for page in pdf_reader.pages:
                                                full_text += page.extract_text() + "\n"
                                            
                                            full_text_lower = full_text.lower()
                                            
                                            # Check for code match
                                            code_match = item_code.lower() in full_text_lower or item_code.upper() in full_text
                                            
                                            # Check for title matches
                                            title_matches = []
                                            for var in title_variations:
                                                if var in full_text_lower:
                                                    title_matches.append(var)
                                            
                                            if code_match or title_matches:
                                                pdf_item_name, pdf_item_code = extract_item_info_from_pdf_text(full_text)
                                                matches_found.append({
                                                    'name': pdf_name,
                                                    'code_match': code_match,
                                                    'title_matches': title_matches,
                                                    'extracted_code': pdf_item_code,
                                                    'extracted_name': pdf_item_name
                                                })
                                        except Exception as e:
                                            continue
                                    
                                    if matches_found:
                                        st.write(f"**Found {len(matches_found)} potential match(es):**")
                                        for match in matches_found:
                                            st.write(f"- `{match['name']}`")
                                            if match['code_match']:
                                                st.write(f"  ✅ Code match: {match['extracted_code']}")
                                            if match['title_matches']:
                                                st.write(f"  ✅ Title match: {', '.join(match['title_matches'][:2])}")
                                            if match['extracted_code']:
                                                st.write(f"  📋 Extracted code: {match['extracted_code']}")
                                            if match['extracted_name']:
                                                st.write(f"  📋 Extracted name: {match['extracted_name']}")
                                    else:
                                        st.write("❌ No matches found in scanned PDFs")
                                        
                            except Exception as e:
                                st.write(f"⚠️ Error reading ZIP: {str(e)}")
                        else:
                            st.write(f"")
                            st.write(f"**ZIP file not found:** ❌ `{zip_path}`")
                        
                        st.write("")
                        st.write("**Tips:**")
                        st.write("1. Make sure the recipe PDF contains the item code (e.g., 'A1551')")
                        st.write("2. Or the recipe PDF should contain part of the item name (e.g., 'Terbyelli')")
                        st.write("3. For Google Docs, the recipe title should match the item code or name")
            
            # Display recipe if available
            if st.session_state.get('current_recipe'):
                recipe = st.session_state.current_recipe
                recipe_source = st.session_state.get('recipe_source', 'unknown')
                
                # Display source indicator
                if recipe_source == 'zip':
                    st.info("📦 Recipe loaded from PDF ZIP file")
                elif recipe_source == 'gdocs':
                    st.info("📄 Recipe loaded from Google Docs")
                
                # Handle PDF recipe
                if recipe.get('type') == 'pdf':
                    # Use item name from PDF if available, otherwise use selected item title
                    pdf_item_name = recipe.get('item_name')
                    pdf_item_code = recipe.get('item_code')
                    
                    # Determine display name and code
                    display_name = pdf_item_name if pdf_item_name else selected_item.get('title', 'Recipe')
                    display_code = pdf_item_code if pdf_item_code else selected_item.get('code')
                    
                    # Show warning if names don't match
                    if pdf_item_name and pdf_item_name.lower() != selected_item.get('title', '').lower():
                        st.warning(f"⚠️ **Note:** The recipe PDF contains item name '{pdf_item_name}', which differs from the selected item '{selected_item.get('title')}'. Displaying the name from the PDF.")
                    
                    # Show warning if codes don't match
                    if pdf_item_code and pdf_item_code.upper() != selected_item.get('code', '').upper():
                        st.error(f"❌ **Error:** The recipe PDF contains item code '{pdf_item_code}', which does not match the selected item code '{selected_item.get('code')}'. This recipe may not be correct for this item.")
                    
                    st.markdown(f"### {display_name} ({display_code})")
                    
                    # Display PDF download button only
                    pdf_data = recipe.get('pdf_data')
                    if pdf_data:
                        # Ensure pdf_data is bytes
                        if isinstance(pdf_data, str):
                            pdf_data = pdf_data.encode('utf-8')
                        elif not isinstance(pdf_data, bytes):
                            pdf_data = bytes(pdf_data)
                        
                        # Use PDF item name for filename if available
                        filename_name = pdf_item_name if pdf_item_name else selected_item.get('title', 'recipe')
                        filename_code = pdf_item_code if pdf_item_code else selected_item.get('code')
                        
                        # Download button
                        st.download_button(
                            label="📥 Download Recipe PDF",
                            data=pdf_data,
                            file_name=f"recipe_{filename_code}_{filename_name.replace(' ', '_')}.pdf",
                            mime="application/pdf",
                            use_container_width=True,
                            type="primary"
                        )
                else:
                    # Handle Google Docs recipe (existing code)
                    recipe_data = st.session_state.current_recipe
                    
                    # Recipe title
                    st.markdown(f"### {recipe_data.get('name', selected_item.get('title', 'Recipe'))}")
                    
                    # Ingredients section
                    if recipe_data.get('ingredients'):
                        st.subheader("📝 Ingredients")
                        for ingredient in recipe_data['ingredients']:
                            st.write(f"• {ingredient}")
                    
                    # Instructions section
                    if recipe_data.get('instructions'):
                        st.subheader("📋 Instructions")
                        for i, instruction in enumerate(recipe_data['instructions'], 1):
                            st.write(f"{i}. {instruction}")
                    
                    # Full text fallback (if no structured data)
                    if recipe_data.get('full_text') and not recipe_data.get('ingredients') and not recipe_data.get('instructions'):
                        st.subheader("📄 Recipe")
                        for line in recipe_data['full_text']:
                            st.write(line)
                    
                    st.divider()
                    
                    # Print Recipe Button
                    col1, col2, col3 = st.columns([1, 2, 1])
                    with col2:
                        if st.button("🖨️ Print Recipe PDF", type="primary", use_container_width=True, key="print_recipe_viewer"):
                            with st.spinner("Generating recipe PDF..."):
                                try:
                                    pdf_file = generate_recipe_pdf_from_gdocs(
                                        recipe,
                                        selected_item.get('code'),
                                        selected_item.get('title')
                                    )
                                    
                                    with open(pdf_file, 'rb') as f:
                                        pdf_bytes = f.read()
                                        st.download_button(
                                            label="📥 Download Recipe PDF",
                                            data=pdf_bytes,
                                            file_name=f"{selected_item.get('code')}_recipe.pdf",
                                            mime="application/pdf",
                                            type="primary",
                                            use_container_width=True,
                                            key="download_recipe_pdf"
                                        )
                                    
                                    # Clean up temp file
                                    try:
                                        os.unlink(pdf_file)
                                    except:
                                        pass
                                except Exception as e:
                                    st.error(f"Error generating PDF: {str(e)}")
                                    logger.error(f"Error generating recipe PDF: {e}")
        
        # ============================================
        # FLOW: CREATE MO (action_selected == "mo")
        # ============================================
        elif st.session_state.action_selected == 'mo':
            st.divider()
            st.header("Step 4: Create Manufacturing Order")
            st.success(f"**Selected Item:** {selected_item.get('title')} ({selected_item.get('code')})")
            
            # Create tabs for Single and Batch creation
            tab1, tab2 = st.tabs(["📝 Single Creation", "⚡ Batch Creation"])
            
            # ============================================
            # TAB 1: SINGLE CREATION (existing flow)
            # ============================================
            with tab1:
                # Get unit for the item
                unit_id = selected_item.get('unit_id')
                unit_name = get_unit_by_id(unit_id, all_units)
                
                # Expected Output (Estimate) input
                st.info("💡 **Expected Output** is an **estimate** used for planning (ingredients, routing). Actual produced quantity will be captured later from the Lot App.")
                col1, col2 = st.columns([3, 1])
                with col1:
                    quantity = st.number_input(
                        f"Expected Output (Estimate) ({unit_name})",
                        min_value=0.0,
                        step=1.0,
                        format="%.2f",
                        value=1.0,
                        help="Enter the estimated quantity for planning purposes. This will be used to calculate ingredients and generate routing. Actual produced quantity will be captured from the Lot App.",
                        key="quantity_input"
                    )
                with col2:
                    st.metric("Unit", unit_name)
                
                # Submit button
                if st.button("🚀 Create Manufacturing Order", type="primary", use_container_width=True, key="create_mo_single"):
                    if quantity <= 0:
                        st.error("Please enter a quantity greater than 0")
                    else:
                        with st.spinner("Creating Manufacturing Order..."):
                            try:
                                # Get current date as Unix timestamp
                                current_date = int(datetime.now().timestamp())
                                
                                # Create the manufacturing order
                                response = api.create_manufacturing_order(
                                    item_code=selected_item.get('code'),
                                    quantity=float(quantity),
                                    assigned_id=1,
                                    start_date=current_date
                                )
                                
                                if response.ok:
                                    # Handle response - could be int or dict
                                    response_data = response.json()
                                    logger.info(f"MO Creation Response: {response_data}")
                                    logger.info(f"Response type: {type(response_data)}")
                                    print(f"MO Creation Response: {response_data}")
                                    print(f"Response type: {type(response_data)}")
                                    
                                    if isinstance(response_data, int):
                                        mo_id = response_data
                                    elif isinstance(response_data, dict):
                                        mo_id = response_data.get('man_ord_id') or response_data.get('id')
                                    else:
                                        st.error(f"Unexpected response format: {response_data}")
                                        return
                                    
                                    st.session_state.created_mo_id = mo_id
                                    st.session_state.mo_number = mo_id  # Sync with state machine
                                    
                                    st.success(f"✅ Manufacturing Order created successfully! (ID: {mo_id})")
                                    
                                    # Now generate the PDF
                                    with st.spinner("Generating routing PDF..."):
                                        # Fetch the MO data (contains both basic and detailed info)
                                        mo_data = api.get_manufacturing_order_details(mo_id)
                                        
                                        if mo_data:
                                            mo_code = mo_data.get('code', 'MO')
                                            
                                            # Generate PDF (mo_data contains all needed info)
                                            pdf_file = generate_mo_recipe_pdf(
                                                mo_data, 
                                                mo_data, 
                                                all_items,
                                                all_units
                                            )
                                            
                                            st.session_state.show_routing = True  # Set routing state
                                            st.success("🎉 Routing PDF Generated Successfully!")
                                            
                                            # Provide download button
                                            with open(pdf_file, 'rb') as f:
                                                pdf_bytes = f.read()
                                                st.download_button(
                                                    label="📥 Download Routing PDF",
                                                    data=pdf_bytes,
                                                    file_name=f"{selected_item.get('code')}_{mo_code}_routing.pdf",
                                                    mime="application/pdf",
                                                    type="primary",
                                                    use_container_width=True
                                                )
                                            
                                            # Clean up temp file
                                            try:
                                                os.unlink(pdf_file)
                                            except:
                                                pass
                                        else:
                                            st.warning("MO created but could not fetch details for PDF generation")
                                else:
                                    st.error(f"❌ Failed to create Manufacturing Order: {response.text}")
                            
                            except Exception as e:
                                logger.error(f"Error creating MO: {str(e)}")
                                st.error(f"❌ Error: {str(e)}")
            
            # ============================================
            # TAB 2: BATCH CREATION (automatic MO creation)
            # ============================================
            with tab2:
                st.subheader("⚡ Batch Order Creation")
                st.info("Create Manufacturing Orders automatically with item code, expected output (estimate), and start date.")
                
                # Form for batch creation
                with st.form("batch_order_form", clear_on_submit=False):
                    col1, col2 = st.columns(2)
                    
                    with col1:
                        # Item code input (auto-filled if item is selected)
                        default_item_code = selected_item.get('code', '') if selected_item else ''
                        item_code_input = st.text_input(
                            "Item Code *",
                            value=default_item_code,
                            placeholder="e.g., A1234",
                            help="Enter the item code for the Manufacturing Order"
                        )
                    
                    with col2:
                        # Expected Output (Estimate) input
                        quantity_input = st.number_input(
                            "Expected Output (Estimate) *",
                            min_value=0.0,
                            step=1.0,
                            format="%.2f",
                            value=1.0,
                            help="Enter the estimated quantity for planning purposes. This will be used to calculate ingredients and generate routing. Actual produced quantity will be captured from the Lot App."
                        )
                    
                    # Start date input
                    today = datetime.now()
                    default_date = today.strftime("%m/%d/%Y")
                    start_date_input = st.text_input(
                        "Start Date (MM/DD/YYYY) *",
                        value=default_date,
                        placeholder="MM/DD/YYYY",
                        help="Enter the start date in MM/DD/YYYY format"
                    )
                    
                    # Submit button
                    submitted = st.form_submit_button("🚀 Create Manufacturing Order", type="primary", use_container_width=True)
                    
                    if submitted:
                        # Validate and create MO
                        success, mo_id, message = create_mo_batch(
                            api,
                            item_code_input,
                            quantity_input,
                            start_date_input
                        )
                        
                        if success:
                            # Save MO number to session state
                            st.session_state.mo_number = mo_id
                            st.session_state.created_mo_id = mo_id  # Legacy sync
                            
                            st.success(f"✅ {message}")
                            
                            # Display MO number prominently
                            st.metric("Manufacturing Order ID", mo_id)
                        else:
                            st.error(f"❌ {message}")
        
        # ============================================
        # ROUTING PDF GENERATOR (only if mo_number exists)
        # ============================================
        if st.session_state.mo_number:
            st.divider()
            st.header("📄 Routing PDF Generator")
            
            mo_id = st.session_state.mo_number
            
            # Initialize MO data cache in session state if not exists
            if 'routing_mo_data' not in st.session_state or st.session_state.get('routing_mo_id') != mo_id:
                with st.spinner("Loading Manufacturing Order details..."):
                    # Fetch full MO details using the MO ID
                    mo_full_data = api.get_manufacturing_order_details(mo_id)
                    
                    if mo_full_data:
                        # get_manufacturing_order_details returns all data in one object
                        st.session_state.routing_mo_data = mo_full_data
                        st.session_state.routing_mo_id = mo_id
                        st.session_state.routing_mo_full_data = mo_full_data
                    else:
                        st.error(f"❌ Could not fetch Manufacturing Order details for ID: {mo_id}")
                        st.session_state.routing_mo_data = None
                        st.session_state.routing_mo_full_data = None
            
            # Display MO summary and PDF generation if data is available
            if st.session_state.get('routing_mo_data'):
                # Use the same data object for both mo_data and mo_full_data
                # since get_manufacturing_order_details returns complete data
                mo_data = st.session_state.routing_mo_data
                mo_full_data = st.session_state.routing_mo_full_data
                
                # Display MO Summary
                st.subheader("Manufacturing Order Summary")
                col1, col2, col3 = st.columns(3)
                
                with col1:
                    st.metric("MO ID", mo_id)
                    st.metric("MO Code", mo_data.get('code', 'N/A'))
                    st.metric("Item", mo_data.get('item_title', 'N/A'))
                
                with col2:
                    st.metric("Quantity", f"{mo_data.get('quantity', 0)} {mo_data.get('unit', '')}")
                    st.metric("Status", mo_data.get('status', 'N/A'))
                    st.metric("Parts Count", len(mo_full_data.get('parts', [])))
                
                with col3:
                    st.metric("Operations Count", len(mo_full_data.get('operations', [])))
                
                st.info(f"""
                **PDF will be generated with:**
                - Item: {mo_data.get('item_title', 'N/A')}
                - MO Code: {mo_data.get('code', 'N/A')}
                - Quantity: {mo_data.get('quantity', 0)} {mo_data.get('unit', '')}
                - Parts/Ingredients: {len(mo_full_data.get('parts', []))}
                - Operations: {len(mo_full_data.get('operations', []))}
                """)
                
                # Generate PDF button
                col1, col2, col3 = st.columns([1, 2, 1])
                with col2:
                    if st.button("🖨️ Generate Routing PDF", type="primary", use_container_width=True, key="generate_routing_pdf"):
                        with st.spinner("Generating Routing PDF..."):
                            try:
                                # Generate PDF using cached items and units
                                pdf_file = generate_mo_recipe_pdf(
                                    mo_data,
                                    mo_full_data,
                                    all_items,
                                    all_units
                                )
                                
                                # Store PDF file path in session state
                                st.session_state.routing_pdf_file = pdf_file
                                st.session_state.show_routing = True
                                
                                st.success("🎉 **Routing PDF Generated Successfully!**")
                                
                                # Read PDF bytes for download and preview
                                with open(pdf_file, 'rb') as f:
                                    pdf_bytes = f.read()
                                    st.session_state.routing_pdf_bytes = pdf_bytes
                                
                                st.rerun()
                            
                            except Exception as e:
                                st.error(f"❌ An error occurred while generating the PDF: {str(e)}")
                                logger.error(f"Error generating routing PDF: {e}")
                                st.exception(e)
                
                # Display PDF download and preview if generated
                if st.session_state.get('routing_pdf_file') and st.session_state.get('show_routing'):
                    st.divider()
                    st.subheader("📥 Download & Print Routing PDF")
                    
                    pdf_bytes = st.session_state.get('routing_pdf_bytes')
                    if pdf_bytes:
                        # Download button
                        col1, col2, col3 = st.columns([1, 2, 1])
                        with col2:
                            st.download_button(
                                label="📥 Download Routing PDF",
                                data=pdf_bytes,
                                file_name=f"{mo_data.get('item_code', 'recipe')}_{mo_data.get('code', 'MO')}_routing.pdf",
                                mime="application/pdf",
                                type="primary",
                                use_container_width=True,
                                key="download_routing_pdf"
                            )
                            
                            # Preview PDF using base64 embedding
                            st.markdown("### 📄 PDF Preview")
                            import base64
                            pdf_base64 = base64.b64encode(pdf_bytes).decode('utf-8')
                            pdf_display = f'<iframe src="data:application/pdf;base64,{pdf_base64}" width="100%" height="600px" type="application/pdf"></iframe>'
                            st.markdown(pdf_display, unsafe_allow_html=True)
                            
                            # Print button (opens print dialog)
                            st.markdown(f"""
                            <script>
                            function printPDF() {{
                                const pdfWindow = window.open('');
                                pdfWindow.document.write('<iframe width="100%" height="100%" src="data:application/pdf;base64,{pdf_base64}"></iframe>');
                                pdfWindow.document.close();
                                pdfWindow.focus();
                                pdfWindow.print();
                            }}
                            </script>
                            <button onclick="printPDF()" style="
                                background-color: #1E3A8A;
                                color: white;
                                padding: 0.75rem 1.5rem;
                                border-radius: 0.5rem;
                                border: none;
                                cursor: pointer;
                                font-size: 1rem;
                                width: 100%;
                                margin-top: 1rem;
                            ">🖨️ Print PDF</button>
                            """, unsafe_allow_html=True)
        
        # Reset button
        st.divider()
        if st.button("🔄 Start Over", use_container_width=True):
            reset_state_machine()
            st.rerun()


if __name__ == "__main__":
    main()

