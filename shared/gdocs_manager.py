from google.oauth2 import service_account
from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
import re
from typing import List, Dict, Any


class GDocsManager:
    def __init__(self, credentials_path=None):
        """Initialize the GDocs Manager with the provided credentials path"""
        self.credentials_path = credentials_path
        self.service = None
        self.drive_service = None

    def authenticate(self, credentials_path=None):
        """Authenticate with Google Docs API"""
        if credentials_path:
            self.credentials_path = credentials_path

        if not self.credentials_path:
            raise ValueError("Credentials path not provided")

        scopes = [
            'https://www.googleapis.com/auth/documents.readonly',
            'https://www.googleapis.com/auth/drive.readonly'
        ]

        try:
            credentials = service_account.Credentials.from_service_account_file(
                self.credentials_path,
                scopes=scopes
            )
            self.service = build('docs', 'v1', credentials=credentials)
            self.drive_service = build('drive', 'v3', credentials=credentials)
            return self.service
        except Exception as e:
            raise Exception(f"Failed to authenticate with Google Docs: {e}")

    def get_document_id_from_url(self, doc_url):
        """Extract document ID from Google Docs URL"""
        # Pattern: https://docs.google.com/document/d/DOCUMENT_ID/edit
        match = re.search(r'/document/d/([a-zA-Z0-9-_]+)', doc_url)
        if match:
            return match.group(1)
        raise ValueError(f"Invalid Google Docs URL: {doc_url}")

    def get_document_content(self, doc_url):
        """Get the full text content of a Google Doc"""
        if not self.service:
            raise ValueError("Not authenticated. Call authenticate() first.")

        try:
            doc_id = self.get_document_id_from_url(doc_url)
            document = self.service.documents().get(documentId=doc_id).execute()
            
            # Extract text from document
            content = document.get('body', {}).get('content', [])
            text_content = self._extract_text_from_elements(content)
            
            return text_content, document
        except HttpError as e:
            raise Exception(f"Error accessing document: {e}")
        except Exception as e:
            raise Exception(f"Failed to get document content: {e}")

    def _extract_text_from_elements(self, elements):
        """Recursively extract text from document elements"""
        text_parts = []
        
        for element in elements:
            if 'paragraph' in element:
                paragraph = element['paragraph']
                para_text = self._extract_text_from_paragraph(paragraph)
                if para_text:
                    text_parts.append(para_text)
            elif 'table' in element:
                # Handle tables if needed
                pass
            elif 'sectionBreak' in element:
                text_parts.append('\n\n')
        
        return '\n'.join(text_parts)

    def _extract_text_from_paragraph(self, paragraph):
        """Extract text from a paragraph element"""
        text_parts = []
        elements = paragraph.get('elements', [])
        
        for elem in elements:
            if 'textRun' in elem:
                text_run = elem['textRun']
                text = text_run.get('content', '')
                text_parts.append(text)
        
        return ''.join(text_parts)

    def parse_recipes_from_text(self, text_content):
        """Parse recipes from document text - improved version"""
        recipes = []
        
        # Split by common recipe separators
        lines = text_content.split('\n')
        
        current_recipe = None
        in_ingredients = False
        in_instructions = False
        
        for line in lines:
            line = line.strip()
            
            # Skip empty lines but use them as separators
            if not line:
                if current_recipe:
                    in_ingredients = False
                    in_instructions = False
                continue
            
            # Check for section headers
            line_lower = line.lower()
            if 'ingredient' in line_lower and ('list' in line_lower or ':' in line):
                in_ingredients = True
                in_instructions = False
                continue
            elif 'instruction' in line_lower or 'direction' in line_lower or 'step' in line_lower:
                in_ingredients = False
                in_instructions = True
                continue
            
            # Check if it's a recipe title
            if self._is_recipe_title(line):
                # Save previous recipe if exists
                if current_recipe:
                    recipes.append(current_recipe)
                
                # Start new recipe
                current_recipe = {
                    'name': line.replace(':', '').strip(),
                    'ingredients': [],
                    'instructions': [],
                    'section': None
                }
                in_ingredients = False
                in_instructions = False
            elif current_recipe:
                # Add to current recipe
                if in_ingredients:
                    current_recipe['ingredients'].append(line)
                elif in_instructions:
                    current_recipe['instructions'].append(line)
                else:
                    # Auto-detect based on content
                    if self._is_ingredient_line(line):
                        current_recipe['ingredients'].append(line)
                    elif self._is_instruction_line(line):
                        current_recipe['instructions'].append(line)
                    else:
                        # Default: treat as instruction if it looks like a sentence
                        if line.endswith('.') or len(line) > 50:
                            current_recipe['instructions'].append(line)
                        else:
                            current_recipe['ingredients'].append(line)
        
        # Add last recipe
        if current_recipe:
            recipes.append(current_recipe)
        
        # If no recipes found with titles, try to extract by patterns
        if not recipes:
            recipes = self._parse_recipes_by_pattern(text_content)
        
        return recipes
    
    def _parse_recipes_by_pattern(self, text_content):
        """Alternative parsing method using common patterns"""
        recipes = []
        
        # Try to find recipes separated by double newlines or specific markers
        # This is a fallback if title detection doesn't work
        sections = re.split(r'\n\n+', text_content)
        
        for section in sections:
            lines = [l.strip() for l in section.split('\n') if l.strip()]
            if len(lines) < 2:
                continue
            
            # First line might be the recipe name
            recipe_name = lines[0]
            if len(recipe_name) > 100:
                continue
            
            recipe = {
                'name': recipe_name,
                'ingredients': [],
                'instructions': [],
                'section': None
            }
            
            # Process remaining lines
            for line in lines[1:]:
                if self._is_ingredient_line(line):
                    recipe['ingredients'].append(line)
                else:
                    recipe['instructions'].append(line)
            
            if recipe['ingredients'] or recipe['instructions']:
                recipes.append(recipe)
        
        return recipes

    def _is_recipe_title(self, line):
        """Check if a line is likely a recipe title - more flexible version"""
        if not line or len(line) > 150:  # Too long to be a title
            return False
        
        line_stripped = line.strip()
        
        # Ends with colon - very likely a title
        if line_stripped.rstrip().endswith(':'):
            return True
        
        # All uppercase and reasonably short - likely a title
        if line_stripped.isupper() and len(line_stripped) < 60:
            return True
        
        # Title case pattern (First Word Capitalized)
        if re.match(r'^[A-Z][a-zA-Z0-9\s\-\(\):]+$', line_stripped) and len(line_stripped) < 80:
            # Check if it's not all caps (which we already handled)
            if not line_stripped.isupper():
                return True
        
        # Contains item code pattern (A####) and is reasonably short
        if re.search(r'[A-Z]\d{4}', line_stripped) and len(line_stripped) < 100:
            return True
        
        # Short lines that look like titles (no sentence-ending punctuation)
        if len(line_stripped) < 60 and not line_stripped.endswith('.') and not line_stripped.endswith('!') and not line_stripped.endswith('?'):
            # Check if it contains common title words or patterns
            if any(word in line_stripped.lower() for word in ['recipe', 'ingredient', 'instruction', 'method', 'preparation']):
                return False  # These are section headers, not recipe titles
            # If it's short and doesn't look like a sentence, might be a title
            if len(line_stripped.split()) < 10:  # Less than 10 words
                return True
        
        return False

    def _is_ingredient_line(self, line):
        """Check if a line is likely an ingredient"""
        ingredient_keywords = ['cup', 'tbsp', 'tsp', 'oz', 'lb', 'gram', 'kg', 'ml', 'l', 'piece', 'pieces']
        return any(keyword in line.lower() for keyword in ingredient_keywords)

    def _is_instruction_line(self, line):
        """Check if a line is likely an instruction"""
        instruction_keywords = ['step', 'mix', 'heat', 'cook', 'bake', 'fry', 'add', 'stir', 'pour']
        return any(keyword in line.lower() for keyword in instruction_keywords)

