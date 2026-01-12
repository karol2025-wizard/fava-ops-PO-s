"""
Script para revisar todas las recetas en el documento de Google Docs
y verificar que las nuevas recetas estén correctamente formateadas.
"""
import streamlit as st
from shared.gdocs_manager import GDocsManager
from config import secrets
import re

def main():
    st.set_page_config(
        page_title="Revisar Recetas",
        page_icon="📋",
        layout="wide"
    )
    
    st.title("📋 Revisión de Recetas en Google Docs")
    
    # Get recipes document URL from config
    try:
        recipes_doc_url = secrets.get('RECIPES_DOCS_URL', '')
        if not recipes_doc_url:
            st.error("❌ No se encontró RECIPES_DOCS_URL en la configuración.")
            return
        
        # Get credentials path
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH', 'credentials/starship-431114-129e01fe3c06.json')
        
        st.info(f"📄 Documento: {recipes_doc_url}")
        
        # Authenticate and get document
        with st.spinner("Conectando a Google Docs..."):
            gdocs_manager = GDocsManager(credentials_path=creds_path)
            gdocs_manager.authenticate()
            
            # Get document content
            text_content, document = gdocs_manager.get_document_content(recipes_doc_url)
            
        st.success("✅ Conexión exitosa")
        
        # Parse all recipes
        with st.spinner("Parseando recetas..."):
            all_recipes = gdocs_manager.parse_recipes_from_text(text_content)
        
        st.success(f"✅ Se encontraron {len(all_recipes)} recetas")
        
        # Display summary
        st.header("📊 Resumen")
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total de Recetas", len(all_recipes))
        with col2:
            recipes_with_code = sum(1 for r in all_recipes if re.search(r'[A-Z]\d{4}', r['name']))
            st.metric("Con Código (A####)", recipes_with_code)
        with col3:
            recipes_with_ingredients = sum(1 for r in all_recipes if r.get('ingredients'))
            st.metric("Con Ingredientes", recipes_with_ingredients)
        
        # Search functionality
        st.header("🔍 Buscar Receta")
        search_term = st.text_input("Buscar por nombre o código:", placeholder="Ej: A1567 o Cheese Borek")
        
        # Filter recipes
        if search_term:
            search_lower = search_term.lower()
            filtered_recipes = [
                r for r in all_recipes
                if search_lower in r['name'].lower() or search_lower in str(r)
            ]
            st.info(f"Se encontraron {len(filtered_recipes)} recetas que coinciden con '{search_term}'")
        else:
            filtered_recipes = all_recipes
        
        # Display recipes
        st.header("📝 Lista de Recetas")
        
        if not filtered_recipes:
            st.warning("No se encontraron recetas.")
            return
        
        # Group by first letter or code
        recipes_by_letter = {}
        for recipe in filtered_recipes:
            name = recipe['name']
            # Extract code if exists
            code_match = re.search(r'([A-Z]\d{4})', name.upper())
            if code_match:
                key = code_match.group(1)
            else:
                key = name[0].upper() if name else 'Other'
            
            if key not in recipes_by_letter:
                recipes_by_letter[key] = []
            recipes_by_letter[key].append(recipe)
        
        # Sort keys
        sorted_keys = sorted(recipes_by_letter.keys(), key=lambda x: (not x.startswith('A'), x))
        
        for key in sorted_keys:
            with st.expander(f"🔹 {key} ({len(recipes_by_letter[key])} recetas)", expanded=False):
                for idx, recipe in enumerate(recipes_by_letter[key], 1):
                    st.subheader(f"{idx}. {recipe['name']}")
                    
                    # Extract and display code
                    code_match = re.search(r'([A-Z]\d{4})', recipe['name'].upper())
                    if code_match:
                        st.code(f"Código: {code_match.group(1)}")
                    
                    # Display ingredients
                    if recipe.get('ingredients'):
                        st.write("**Ingredientes:**")
                        for ingredient in recipe['ingredients'][:10]:  # Show first 10
                            st.write(f"- {ingredient}")
                        if len(recipe['ingredients']) > 10:
                            st.caption(f"... y {len(recipe['ingredients']) - 10} ingredientes más")
                    
                    # Display instructions
                    if recipe.get('instructions'):
                        st.write("**Instrucciones:**")
                        for instruction in recipe['instructions'][:5]:  # Show first 5
                            st.write(f"- {instruction}")
                        if len(recipe['instructions']) > 5:
                            st.caption(f"... y {len(recipe['instructions']) - 5} instrucciones más")
                    
                    # If no ingredients or instructions, show full text
                    if not recipe.get('ingredients') and not recipe.get('instructions'):
                        if recipe.get('full_text'):
                            st.write("**Contenido:**")
                            for line in recipe['full_text'][:10]:
                                st.write(f"- {line}")
                            if len(recipe['full_text']) > 10:
                                st.caption(f"... y {len(recipe['full_text']) - 10} líneas más")
                    
                    st.divider()
        
        # Export option
        st.header("💾 Exportar")
        if st.button("Exportar Lista de Recetas"):
            import json
            recipes_json = json.dumps([{
                'name': r['name'],
                'code': re.search(r'([A-Z]\d{4})', r['name'].upper()).group(1) if re.search(r'([A-Z]\d{4})', r['name'].upper()) else None,
                'ingredients_count': len(r.get('ingredients', [])),
                'instructions_count': len(r.get('instructions', []))
            } for r in all_recipes], indent=2, ensure_ascii=False)
            
            st.download_button(
                label="Descargar JSON",
                data=recipes_json,
                file_name="recetas_lista.json",
                mime="application/json"
            )

if __name__ == "__main__":
    main()

