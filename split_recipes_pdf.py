from PyPDF2 import PdfReader, PdfWriter
import os
import re
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

# Palabras clave que identifican inicio de receta
RECIPE_KEYWORDS = [
    "Dip", "Sauce", "Base", "Dessert", "Appetizer",
    "Hummus", "Mutabbal", "Falafel", "Kibbeh",
    "Kataifi", "Kunafa", "Yalanji", "Shish", "Marinade"
]

def is_new_recipe(text):
    text = text.strip()
    for word in RECIPE_KEYWORDS:
        if text.startswith(word):
            return True
    return False

reader = PdfReader(INPUT_PDF)

current_writer = None
current_title = None
file_index = 1

for i, page in enumerate(reader.pages):
    text = page.extract_text() or ""

    # Detect start of new recipe
    if is_new_recipe(text):
        if current_writer:
            filename = f"{file_index:03d}_{current_title}.pdf"
            current_writer.write(open(os.path.join(OUTPUT_DIR, filename), "wb"))
            file_index += 1

        # sanitize title
        first_line = text.split("\n")[0][:60]
        safe_title = re.sub(r"[^a-zA-Z0-9_ ]", "", first_line).replace(" ", "_")
        current_title = safe_title

        current_writer = PdfWriter()

    if current_writer:
        current_writer.add_page(page)

# Save last file
if current_writer:
    filename = f"{file_index:03d}_{current_title}.pdf"
    current_writer.write(open(os.path.join(OUTPUT_DIR, filename), "wb"))

print("✅ PDF split completed.")

