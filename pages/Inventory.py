"""
Página Inventory - Gestión de inventario.
"""
import streamlit as st


def main():
    st.title("📦 Inventory")
    st.markdown("---")

    st.info("Página de Inventory. Aquí puedes añadir consultas de stock, lotes, productos y toda la lógica de inventario que necesites.")

    # Placeholder para contenido futuro
    with st.expander("Resumen rápido", expanded=True):
        st.write("Contenido de la página Inventory en desarrollo.")
        st.write("Puedes conectar datos de **API**, **base de datos** o **Google Sheets** según el resto de la app.")


if __name__ == "__main__":
    main()
