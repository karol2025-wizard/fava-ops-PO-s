import toml
import os

def _load_dotenv():
    """Load .env file if python-dotenv is available. No-op otherwise."""
    try:
        from dotenv import load_dotenv
        _root = os.path.dirname(os.path.abspath(__file__))
        env_path = os.path.join(_root, ".env")
        load_dotenv(env_path)
    except ImportError:
        pass  # python-dotenv optional

def load_secrets():
    # 1. Load .env first (variables from .env override secrets.toml)
    _load_dotenv()
    _root = os.path.dirname(os.path.abspath(__file__))
    result = {}
    # 2. Load secrets.toml as base
    secrets_path = os.getenv("SECRETS_PATH", os.path.join(_root, ".streamlit", "secrets.toml"))
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            result = toml.load(f)
    except FileNotFoundError:
        pass
    # 3. Override with env vars (converts to string; toml values preserved if not in env)
    env_map = {
        "MRPEASY_API_KEY": "MRPEASY_API_KEY",
        "MRPEASY_API_SECRET": "MRPEASY_API_SECRET",
        "clover_api_key": "clover_api_key",
        "clover_merchant_id": "clover_merchant_id",
        "BOXHERO_API_TOKEN": "BOXHERO_API_TOKEN",
        "GOOGLE_CREDENTIALS_PATH": "GOOGLE_CREDENTIALS_PATH",
        "mysql_host": "mysql_host",
        "mysql_port": "mysql_port",
        "mysql_user": "mysql_user",
        "mysql_password": "mysql_password",
        "mysql_database": "mysql_database",
        "starship_db_host": "starship_db_host",
        "starship_db_port": "starship_db_port",
        "starship_db_user": "starship_db_user",
        "starship_db_password": "starship_db_password",
        "starship_db_database": "starship_db_database",
    }
    for env_key, secrets_key in env_map.items():
        val = os.getenv(env_key)
        if val is not None:
            result[secrets_key] = val
    return result

secrets = load_secrets()
