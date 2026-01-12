from PyPDF2 import PdfReader, PdfWriter
import os
import sys

INPUT_PDF = "recipes_master.pdf"
OUTPUT_DIR = "recipes_split"

# Check if input file exists
if not os.path.exists(INPUT_PDF):
    print(f"❌ Error: File '{INPUT_PDF}' not found.")
    print(f"Please make sure the PDF file exists in the current directory.")
    print(f"Current directory: {os.getcwd()}")
    sys.exit(1)

os.makedirs(OUTPUT_DIR, exist_ok=True)

reader = PdfReader(INPUT_PDF)
total_pages = len(reader.pages)

print(f"📄 Total pages in PDF: {total_pages}")

# ⚠️ AJUSTA ESTOS NÚMEROS
# Cada número es la página donde comienza una receta nueva (0-indexed)
recipe_start_pages = [
    3,   # Dip Eggplant Mutabbal
    5,   # Beet Mutabbal
    13,  # Hummus
    9,   # Mouhammara
    17,  # Garlic Mayo
    20,  # Garlic Sauce
    22,  # Garlic Yogourt
    24,  # Tarator
    26,  # Marinade Chicken
    31,  # Marinade lamb
    34,  # Falafel base
    39,  # Falafel Not Cooked
    40,  # Dough Cheese Borek
    42,  # Dough Shish Borek
    44,  # Cheese Borek
    49,  # Shish Borek
    54,  # Kataifi Nests
    57,  # Kunafa 
    63,  # Ice Cream Pistachio
    67,  # Yalanji Base
    71,  # Yalanji Frozen Not Cooked
    76,  # Shrimp Kataifi 
    80,  # Tomato Sauce
    83,  # Dukka
    85,  # Eggplant Grilled
    89,  # Terbyelli

    # Agrega más números de página aquí...
]

# Validate page numbers
for page_num in recipe_start_pages:
    if page_num < 0 or page_num >= total_pages:
        print(f"⚠️ Warning: Page {page_num} is out of range (0-{total_pages-1})")

print(f"📋 Found {len(recipe_start_pages)} recipes to extract")

for i, start in enumerate(recipe_start_pages):
    # Determine end page (next recipe start or end of document)
    end = recipe_start_pages[i + 1] if i + 1 < len(recipe_start_pages) else total_pages
    
    if start >= end:
        print(f"⚠️ Skipping recipe {i+1}: start page {start} >= end page {end}")
        continue
    
    writer = PdfWriter()
    
    print(f"📝 Extracting recipe {i+1}: pages {start} to {end-1} ({end-start} pages)")
    
    for p in range(start, end):
        if p < total_pages:
            writer.add_page(reader.pages[p])
        else:
            print(f"⚠️ Warning: Page {p} is out of range")
    
    output_path = os.path.join(OUTPUT_DIR, f"recipe_{i+1:03d}.pdf")
    
    try:
        with open(output_path, "wb") as f:
            writer.write(f)
        print(f"✅ Saved: {output_path}")
    except Exception as e:
        print(f"❌ Error saving {output_path}: {e}")

print(f"\n✅ PDFs generados correctamente en '{OUTPUT_DIR}/'")
print(f"📊 Total recipes extracted: {len(recipe_start_pages)}")


