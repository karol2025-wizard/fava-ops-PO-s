"""
Script simple para revisar las recetas en Google Docs desde la línea de comandos.
"""
from shared.gdocs_manager import GDocsManager
from config import secrets
import re
from typing import List, Dict

def extract_code_from_name(name: str) -> str:
    """Extrae el código del nombre de la receta (ej: A1567)"""
    match = re.search(r'([A-Z]\d{4})', name.upper())
    return match.group(1) if match else None

def main():
    print("=" * 60)
    print("REVISIÓN DE RECETAS EN GOOGLE DOCS")
    print("=" * 60)
    print()
    
    # Get configuration
    try:
        recipes_doc_url = secrets.get('RECIPES_DOCS_URL', '')
        if not recipes_doc_url:
            print("❌ ERROR: No se encontró RECIPES_DOCS_URL en la configuración.")
            return
        
        creds_path = secrets.get('GOOGLE_CREDENTIALS_PATH', 'credentials/starship-431114-129e01fe3c06.json')
        service_account_email = "starship-erp@starship-431114.iam.gserviceaccount.com"
        
        print(f"📄 Documento: {recipes_doc_url}")
        print(f"🔑 Credenciales: {creds_path}")
        print(f"📧 Cuenta de servicio: {service_account_email}")
        print()
        
        # Authenticate and get document
        print("Conectando a Google Docs...", end=" ")
        gdocs_manager = GDocsManager(credentials_path=creds_path)
        gdocs_manager.authenticate()
        
        # Get document content
        text_content, document = gdocs_manager.get_document_content(recipes_doc_url)
        print("✅")
        
        # Parse all recipes
        print("Parseando recetas...", end=" ")
        all_recipes = gdocs_manager.parse_recipes_from_text(text_content)
        print(f"✅ ({len(all_recipes)} recetas encontradas)")
        print()
        
        # Summary
        print("-" * 60)
        print("RESUMEN")
        print("-" * 60)
        print(f"Total de recetas: {len(all_recipes)}")
        
        recipes_with_code = [r for r in all_recipes if extract_code_from_name(r['name'])]
        print(f"Recetas con código (A####): {len(recipes_with_code)}")
        
        recipes_with_ingredients = [r for r in all_recipes if r.get('ingredients')]
        print(f"Recetas con ingredientes: {len(recipes_with_ingredients)}")
        
        recipes_with_instructions = [r for r in all_recipes if r.get('instructions')]
        print(f"Recetas con instrucciones: {len(recipes_with_instructions)}")
        print()
        
        # List all recipes with codes
        print("-" * 60)
        print("LISTA DE RECETAS (ordenadas por código)")
        print("-" * 60)
        
        # Sort recipes by code if available
        recipes_with_code_sorted = sorted(
            recipes_with_code,
            key=lambda r: extract_code_from_name(r['name']) or 'ZZZZ'
        )
        
        recipes_without_code = [r for r in all_recipes if not extract_code_from_name(r['name'])]
        
        # Display recipes with codes
        for recipe in recipes_with_code_sorted:
            code = extract_code_from_name(recipe['name'])
            name = recipe['name']
            ingredients_count = len(recipe.get('ingredients', []))
            instructions_count = len(recipe.get('instructions', []))
            
            print(f"\n[{code}] {name}")
            print(f"   Ingredientes: {ingredients_count}, Instrucciones: {instructions_count}")
            
            # Show first few ingredients if available
            if recipe.get('ingredients'):
                print("   Primeros ingredientes:")
                for ing in recipe['ingredients'][:3]:
                    print(f"     - {ing}")
                if len(recipe['ingredients']) > 3:
                    print(f"     ... y {len(recipe['ingredients']) - 3} más")
        
        # Display recipes without codes
        if recipes_without_code:
            print("\n" + "-" * 60)
            print(f"RECETAS SIN CÓDIGO ({len(recipes_without_code)})")
            print("-" * 60)
            for recipe in recipes_without_code:
                name = recipe['name']
                ingredients_count = len(recipe.get('ingredients', []))
                instructions_count = len(recipe.get('instructions', []))
                
                print(f"\n❓ {name}")
                print(f"   Ingredientes: {ingredients_count}, Instrucciones: {instructions_count}")
        
        print("\n" + "=" * 60)
        print("✅ Revisión completada")
        print("=" * 60)
        
    except Exception as e:
        error_msg = str(e)
        print(f"\n❌ ERROR: {error_msg}")
        
        # Check for specific errors
        if "SERVICE_DISABLED" in error_msg or "API has not been used" in error_msg:
            print("\n" + "=" * 60)
            print("⚠️  API DE GOOGLE DOCS NO HABILITADA")
            print("=" * 60)
            print("\nPara habilitar la API de Google Docs:")
            print("\n1. Abre este enlace en tu navegador:")
            print("   https://console.developers.google.com/apis/api/docs.googleapis.com/overview?project=594969981919")
            print("\n2. Haz clic en 'ENABLE' (Habilitar)")
            print("\n3. Espera unos minutos y vuelve a ejecutar este script")
            print("\n" + "-" * 60)
        
        if "Permission denied" in error_msg or "403" in error_msg:
            service_account_email = "starship-erp@starship-431114.iam.gserviceaccount.com"
            print("\n" + "=" * 60)
            print("⚠️  PERMISOS INSUFICIENTES")
            print("=" * 60)
            print("\nEl documento debe estar compartido con la cuenta de servicio:")
            print(f"\n   📧 {service_account_email}")
            print("\nPara compartir el documento:")
            print("\n1. Abre el documento de recetas en Google Docs")
            print("2. Haz clic en 'Compartir' (botón azul arriba a la derecha)")
            print(f"3. Agrega este email: {service_account_email}")
            print("4. Dale permisos de 'Lector' (Viewer)")
            print("5. Desmarca 'Notificar a las personas'")
            print("6. Haz clic en 'Compartir'")
            print("\n" + "-" * 60)
        
        import traceback
        print("\nDetalles técnicos:")
        traceback.print_exc()

if __name__ == "__main__":
    main()

