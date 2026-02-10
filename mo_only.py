"""
Punto de entrada para mostrar SOLO MO and Recipes, sin menú de navegación.
Al usar st.navigation, Streamlit ignora la carpeta pages/ y no muestra el menú lateral.
"""
import sys
import os

# Asegurar que la raíz del proyecto esté en sys.path para que las páginas puedan importar config, shared, etc.
_project_root = os.path.dirname(os.path.abspath(__file__))
if _project_root not in sys.path:
    sys.path.insert(0, _project_root)

import streamlit as st
import importlib.util

# Cargar main de mo_and_recipes - al usar callable en lugar de archivo,
# Streamlit llama a main() directamente (el archivo usa if __name__ == "__main__"
# y no ejecuta main() cuando se carga como página)
_spec = importlib.util.spec_from_file_location(
    "mo_and_recipes",
    os.path.join(_project_root, "pages", "mo_and_recipes.py")
)
_mo_module = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mo_module)
mo_and_recipes_main = _mo_module.main

st.set_page_config(
    page_title="MO and Recipes",
    page_icon="🏭",
    layout="wide",
    initial_sidebar_state="expanded",
)

# Una sola página: no se muestra menú de navegación.
# Usamos la función main() para que el contenido se renderice correctamente.
pg = st.navigation([
    st.Page(mo_and_recipes_main, title="MO and Recipes"),
], position="hidden")

pg.run()
