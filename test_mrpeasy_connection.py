"""
Test MRPeasy API Connection

Este script prueba la conexión con MRPeasy API y verifica que las credenciales funcionen correctamente.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from shared.api_manager import APIManager
from config import secrets

def test_connection():
    """Test MRPeasy API connection"""
    print("=" * 60)
    print("Testing MRPeasy API Connection")
    print("=" * 60)
    
    # Check credentials
    print("\n1. Checking credentials...")
    api_key = secrets.get('MRPEASY_API_KEY', '')
    api_secret = secrets.get('MRPEASY_API_SECRET', '')
    
    if not api_key:
        print("❌ ERROR: MRPEASY_API_KEY not found in secrets")
        return False
    
    if not api_secret:
        print("❌ ERROR: MRPEASY_API_SECRET not found in secrets")
        return False
    
    print(f"✅ API Key found: {api_key[:10]}...{api_key[-5:] if len(api_key) > 15 else '***'}")
    print(f"✅ API Secret found: {'*' * len(api_secret)}")
    
    # Try to initialize APIManager
    print("\n2. Initializing APIManager...")
    try:
        api = APIManager()
        print("✅ APIManager initialized successfully")
    except Exception as e:
        print(f"❌ ERROR: Failed to initialize APIManager: {str(e)}")
        return False
    
    # Test a simple API call (fetch a few manufacturing orders)
    print("\n3. Testing API call (fetching first 10 manufacturing orders)...")
    try:
        # Try to fetch with a limit
        mos = api.fetch_manufacturing_orders()
        
        if mos is None:
            print("❌ ERROR: API returned None")
            print("   This usually means:")
            print("   - Invalid credentials")
            print("   - Network connection issue")
            print("   - MRPeasy service unavailable")
            return False
        
        if isinstance(mos, list):
            print(f"✅ SUCCESS: Retrieved {len(mos)} manufacturing orders")
            if len(mos) > 0:
                print(f"   First MO: {mos[0].get('code', 'N/A')}")
            return True
        else:
            print(f"❌ ERROR: Unexpected response type: {type(mos)}")
            return False
            
    except ValueError as ve:
        print(f"❌ ERROR: {str(ve)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error: {str(e)}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    success = test_connection()
    print("\n" + "=" * 60)
    if success:
        print("✅ Connection test PASSED")
    else:
        print("❌ Connection test FAILED")
        print("\nTroubleshooting steps:")
        print("1. Verify MRPEASY_API_KEY and MRPEASY_API_SECRET in .streamlit/secrets.toml")
        print("2. Check your internet connection")
        print("3. Verify credentials are correct in MRPeasy account")
        print("4. Check that API has permissions to read Manufacturing Orders")
    print("=" * 60)
    sys.exit(0 if success else 1)

