# Instrucciones para Conectar Google Docs con Recetas

## 📋 Resumen

La página "MO and recipes" ahora puede conectarse a un documento de Google Docs que contenga las recetas paso a paso para cada item. Cuando un usuario selecciona un item, puede ver e imprimir la receta directamente desde Google Docs.

---

## ✅ Condiciones que debe cumplir el documento de Google Docs

### 1. **Estructura del Documento**

El documento debe tener una estructura clara donde cada receta esté identificada por el **código del item** o el **nombre del item**.

### 2. **Formato de Títulos de Recetas**

Cada receta debe comenzar con un título que contenga:
- El **código del item** (ej: `ITEM-001`) O
- El **nombre completo del item** (ej: `Hummus Classic`)

**Ejemplos de títulos válidos:**
```
ITEM-001:
ITEM-001 - Hummus Classic
Hummus Classic:
HUMMUS CLASSIC
```

### 3. **Estructura de Contenido**

Cada receta debe seguir esta estructura:

```
ITEM-001: Hummus Classic

Ingredients:
- 2 cups chickpeas
- 1/4 cup tahini
- 2 tbsp lemon juice
- 1 clove garlic
- Salt to taste

Instructions:
1. Drain and rinse chickpeas
2. Combine all ingredients in food processor
3. Blend until smooth
4. Season with salt
```

**O formato alternativo (sin secciones explícitas):**

```
ITEM-001: Hummus Classic

2 cups chickpeas
1/4 cup tahini
2 tbsp lemon juice
1 clove garlic
Salt to taste

1. Drain and rinse chickpeas
2. Combine all ingredients in food processor
3. Blend until smooth
4. Season with salt
```

### 4. **Separación entre Recetas**

- Cada receta debe estar separada por al menos **una línea en blanco**
- O usar un formato claro con títulos que terminen en `:`

### 5. **Requisitos de Permisos**

El documento de Google Docs debe:
- ✅ Estar compartido con la cuenta de servicio de Google (la que tiene las credenciales JSON)
- ✅ Tener permisos de **lectura** (al menos "Viewer")
- ✅ El email de la cuenta de servicio debe tener acceso

---

## 🔧 Configuración en secrets.toml

Agrega estas líneas a tu archivo `.streamlit/secrets.toml`:

```toml
# Google Docs Recipes Configuration
USE_GOOGLE_DOCS_RECIPES = true
RECIPES_DOCS_URL = "https://docs.google.com/document/d/TU_DOCUMENT_ID/edit"

# Google Credentials (ya deberías tener esto)
GOOGLE_CREDENTIALS_PATH = "credentials/starship-431114-129e01fe3c06.json"
```

### Obtener el Document ID:

1. Abre tu documento de Google Docs
2. Copia la URL completa
3. El Document ID es la parte entre `/d/` y `/edit`
   - Ejemplo: `https://docs.google.com/document/d/1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs/edit`
   - Document ID: `1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs`

---

## 📝 Ejemplo Completo de Documento

```
ITEM-001: Hummus Classic

Ingredients:
- 2 cups cooked chickpeas
- 1/4 cup tahini
- 2 tbsp lemon juice
- 1 clove garlic, minced
- 2 tbsp olive oil
- Salt to taste

Instructions:
1. Drain and rinse chickpeas thoroughly
2. Combine chickpeas, tahini, lemon juice, and garlic in food processor
3. Blend on high speed until smooth
4. While blending, slowly add olive oil
5. Season with salt to taste
6. Transfer to serving bowl and drizzle with olive oil


ITEM-002: Baba Ganoush

Ingredients:
- 2 large eggplants
- 1/4 cup tahini
- 2 tbsp lemon juice
- 2 cloves garlic
- 2 tbsp olive oil
- Salt and pepper

Instructions:
1. Roast eggplants at 400°F for 45 minutes
2. Let cool, then peel and remove seeds
3. Mash eggplant flesh
4. Mix with tahini, lemon juice, and garlic
5. Season with salt and pepper
6. Drizzle with olive oil before serving


ITEM-003: Tabbouleh

Ingredients:
- 1 cup bulgur wheat
- 2 cups boiling water
- 2 bunches fresh parsley, chopped
- 1/2 cup fresh mint, chopped
- 2 tomatoes, diced
- 1/2 cup olive oil
- 1/4 cup lemon juice
- Salt to taste

Instructions:
1. Soak bulgur in boiling water for 30 minutes
2. Drain and let cool
3. Mix bulgur with parsley, mint, and tomatoes
4. Whisk together olive oil and lemon juice
5. Pour dressing over salad
6. Season with salt and mix well
```

---

## 🎯 Cómo Funciona la Búsqueda

El sistema busca recetas de la siguiente manera:

1. **Primero busca por código del item** (ej: `ITEM-001`)
2. **Si no encuentra, busca por nombre del item** (ej: `Hummus Classic`)
3. **Busca en los títulos** que terminen en `:` o que sean títulos reconocibles
4. **Extrae el contenido** hasta encontrar la siguiente receta o el final del documento

---

## 🖨️ Funcionalidades Disponibles

### 1. **Ver Receta**
- Botón: "📄 View Recipe from Google Docs"
- Muestra la receta directamente en la página
- Incluye ingredientes e instrucciones organizados

### 2. **Imprimir Receta PDF**
- Botón: "🖨️ Print Recipe PDF"
- Genera un PDF profesional con la receta
- Incluye título, código del item, ingredientes e instrucciones
- Descarga directa del PDF

---

## ⚠️ Solución de Problemas

### "Recipe not found"
- Verifica que el título de la receta contenga el código del item o el nombre exacto
- Asegúrate de que el título termine en `:` o sea un título reconocible
- Revisa que no haya espacios extra o caracteres especiales

### "Error authenticating with Google Docs"
- Verifica que `GOOGLE_CREDENTIALS_PATH` esté correcto en `secrets.toml`
- Asegúrate de que el archivo JSON de credenciales exista
- Verifica que las APIs de Google Docs y Google Drive estén habilitadas

### "Error accessing document"
- Verifica que el documento esté compartido con la cuenta de servicio
- Asegúrate de que la URL del documento sea correcta
- Verifica que el Document ID sea válido

---

## 📌 Mejores Prácticas

1. **Usa códigos de item consistentes**: Si usas `ITEM-001` en MRPeasy, úsalo también en Google Docs
2. **Mantén formato consistente**: Usa la misma estructura para todas las recetas
3. **Títulos claros**: Los títulos deben ser fáciles de identificar
4. **Actualiza el documento**: Cuando cambies recetas, el sistema las cargará automáticamente
5. **Prueba la búsqueda**: Verifica que los códigos/nombres coincidan exactamente

---

## 🔄 Actualización de Recetas

Las recetas se cargan **en tiempo real** desde Google Docs. No necesitas reiniciar la aplicación:
- Cada vez que se busca una receta, se consulta el documento actualizado
- Los cambios en Google Docs se reflejan inmediatamente
- No hay caché de recetas (solo caché de autenticación)

---

## 📞 Soporte

Si tienes problemas:
1. Verifica la configuración en `secrets.toml`
2. Revisa los logs en la consola de Streamlit
3. Asegúrate de que el formato del documento sea correcto
4. Verifica los permisos del documento de Google Docs

