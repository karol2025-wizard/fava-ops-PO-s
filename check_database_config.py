"""
Check Database Configuration

This script verifies that the database configuration is correct.
Run this to diagnose connection issues.
"""

import sys
import os

# Add project root to path
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from config import secrets

def check_config():
    """Check if all required database configuration is present"""
    print("=" * 60)
    print("Checking Database Configuration")
    print("=" * 60)
    print()
    
    required_keys = [
        'starship_db_host',
        'starship_db_port',
        'starship_db_user',
        'starship_db_password',
        'starship_db_database'
    ]
    
    missing_keys = []
    present_keys = []
    
    for key in required_keys:
        if key not in secrets or not secrets.get(key):
            missing_keys.append(key)
            print(f"❌ {key}: MISSING")
        else:
            present_keys.append(key)
            # Don't print password, just confirm it exists
            if 'password' in key.lower():
                print(f"✅ {key}: CONFIGURED (hidden)")
            else:
                print(f"✅ {key}: {secrets[key]}")
    
    print()
    print("=" * 60)
    
    if missing_keys:
        print("❌ CONFIGURATION INCOMPLETE")
        print()
        print("Missing keys:")
        for key in missing_keys:
            print(f"  - {key}")
        print()
        print("To fix:")
        print("1. Create .streamlit/secrets.toml")
        print("2. Copy secrets.toml.example as a template")
        print("3. Fill in your database credentials")
        print("4. See SETUP_DATABASE.md for detailed instructions")
        return False
    else:
        print("✅ All required configuration present!")
        print()
        print("Testing database connection...")
        try:
            from shared.database_manager import DatabaseManager
            db = DatabaseManager()
            print("✅ Database connection successful!")
            
            # Test query
            try:
                result = db.fetch_all("SELECT 1 as test")
                if result:
                    print("✅ Database query test successful!")
                else:
                    print("⚠️ Database query returned no results")
            except Exception as e:
                print(f"⚠️ Database query test failed: {e}")
            
            # Check if table exists
            try:
                result = db.fetch_all("SHOW TABLES LIKE 'erp_mo_to_import'")
                if result:
                    print("✅ Table 'erp_mo_to_import' exists!")
                    
                    # Check pending entries
                    pending = db.fetch_all(
                        "SELECT COUNT(*) as count FROM erp_mo_to_import WHERE processed_at IS NULL"
                    )
                    if pending:
                        count = pending[0].get('count', 0)
                        print(f"ℹ️  Found {count} pending entries")
                else:
                    print("⚠️ Table 'erp_mo_to_import' does not exist")
                    print("   See SETUP_DATABASE.md for table creation script")
            except Exception as e:
                print(f"⚠️ Could not check table: {e}")
            
            return True
        except Exception as e:
            print(f"❌ Database connection failed: {e}")
            print()
            print("Possible issues:")
            print("  - Incorrect host/port")
            print("  - Incorrect username/password")
            print("  - Database server not running")
            print("  - Network/firewall issues")
            return False

if __name__ == "__main__":
    success = check_config()
    sys.exit(0 if success else 1)

