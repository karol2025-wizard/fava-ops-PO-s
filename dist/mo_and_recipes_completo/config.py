import toml
import os

def load_secrets():
    secrets_path = os.getenv("SECRETS_PATH", ".streamlit/secrets.toml")
    try:
        with open(secrets_path, "r") as f:
            secrets = toml.load(f)
    except FileNotFoundError:
        secrets = {}
    return secrets

secrets = load_secrets()
