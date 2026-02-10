import toml
import os

def load_secrets():
    # Resolver la ruta relativa a la raíz del proyecto (donde está config.py)
    _root = os.path.dirname(os.path.abspath(__file__))
    secrets_path = os.getenv("SECRETS_PATH", os.path.join(_root, ".streamlit", "secrets.toml"))
    try:
        with open(secrets_path, "r", encoding="utf-8") as f:
            return toml.load(f)
    except FileNotFoundError:
        return {}

secrets = load_secrets()
