# Revisar Recetas Nuevas en Google Docs

## 🎯 Objetivo
Revisar las nuevas recetas añadidas al documento de Google Docs y verificar que estén correctamente formateadas y accesibles.

---

## 📋 Paso 1: Habilitar Google Docs API

La API de Google Docs debe estar habilitada en tu proyecto de Google Cloud.

### Enlace directo:
```
https://console.developers.google.com/apis/api/docs.googleapis.com/overview?project=594969981919
```

### Instrucciones:
1. Abre el enlace en tu navegador
2. Haz clic en el botón **"ENABLE"** (Habilitar)
3. Espera 2-5 minutos para que los cambios se propaguen

---

## 📧 Paso 2: Compartir el Documento con la Cuenta de Servicio

El documento debe estar compartido con la cuenta de servicio de Google:

**Email de la cuenta de servicio:**
```
starship-erp@starship-431114.iam.gserviceaccount.com
```

### Instrucciones:
1. Abre tu documento de recetas en Google Docs:
   ```
   https://docs.google.com/document/d/1M0FvH5Q6dhqQKysHyplCrm8w665SM3RbeZcJOhhcGqs/edit
   ```

2. Haz clic en el botón **"Compartir"** (arriba a la derecha)

3. En el campo "Agregar personas o grupos", ingresa:
   ```
   starship-erp@starship-431114.iam.gserviceaccount.com
   ```

4. Asigna el rol: **"Lector"** (Viewer)

5. **Desmarca** la casilla "Notificar a las personas" (no es necesario)

6. Haz clic en **"Compartir"**

---

## ✅ Paso 3: Verificar las Recetas

Una vez habilitada la API y compartido el documento, puedes verificar las recetas de dos maneras:

### Opción A: Script de Línea de Comandos

Ejecuta el script para revisar todas las recetas:

```bash
python check_recipes.py
```

Este script mostrará:
- Total de recetas encontradas
- Lista de todas las recetas con sus códigos
- Recetas sin código (que necesitan corrección)
- Ingredientes e instrucciones de cada receta

### Opción B: Aplicación Streamlit

Ejecuta la aplicación de revisión interactiva:

```bash
streamlit run review_recipes.py
```

Esta aplicación permite:
- Ver todas las recetas en una interfaz visual
- Buscar recetas por código o nombre
- Ver detalles completos de cada receta
- Exportar la lista de recetas

### Opción C: Usar la App Principal

1. Ejecuta la aplicación principal:
   ```bash
   streamlit run home.py
   ```

2. Ve a la página **"MO and Recipes"**

3. Selecciona un item que tenga receta nueva

4. Haz clic en **"📋 Print Recipe"**

5. Verifica que la receta se cargue correctamente

---

## 📝 Formato Esperado de las Recetas

Cada receta debe seguir este formato:

### Formato 1: Con Código Explícito
```
A1567: Cheese Borek - tray

Ingredients:
- 500g cheese
- 2 cups flour
- 1/2 cup water

Instructions:
1. Mix ingredients
2. Roll dough
3. Bake at 350°F
```

### Formato 2: Título con Código
```
Cheese Borek (A1567):

Ingredients:
- 500g cheese
...

Instructions:
1. Mix ingredients
...
```

### Formato 3: Sin Secciones Explícitas
```
A1567: Cheese Borek

500g cheese
2 cups flour
1/2 cup water

1. Mix ingredients
2. Roll dough
3. Bake at 350°F
```

---

## 🔍 Verificación de Recetas Nuevas

Para verificar que las nuevas recetas están correctamente ingresadas:

1. **Busca recetas por código**: El sistema debe encontrar recetas por su código (ej: A1567)

2. **Busca recetas por nombre**: El sistema debe encontrar recetas por su nombre (ej: Cheese Borek)

3. **Verifica ingredientes**: Cada receta debe tener ingredientes listados

4. **Verifica instrucciones**: Cada receta debe tener instrucciones (pasos)

5. **Verifica separación**: Las recetas deben estar separadas correctamente (una línea en blanco entre recetas)

---

## ❌ Problemas Comunes

### Error: "API has not been used in project"
**Solución**: Habilitar la API de Google Docs (ver Paso 1)

### Error: "Permission denied" o "403"
**Solución**: Compartir el documento con la cuenta de servicio (ver Paso 2)

### Error: "Recipe not found"
**Solución**: 
- Verificar que el código del item coincida exactamente
- Verificar que el nombre del item coincida exactamente
- Asegurarse de que el título de la receta termine en `:` o sea claramente un título

### Recetas sin código
**Solución**: Asegurarse de que cada receta tenga su código de item (ej: A1567) en el título

---

## 📊 Checklist de Verificación

- [ ] API de Google Docs habilitada
- [ ] Documento compartido con cuenta de servicio
- [ ] Todas las recetas nuevas tienen código (A####)
- [ ] Todas las recetas tienen ingredientes
- [ ] Todas las recetas tienen instrucciones
- [ ] Las recetas están separadas correctamente
- [ ] Los códigos coinciden con los items en MRPeasy
- [ ] El script `check_recipes.py` funciona correctamente

---

## 🆘 Si Necesitas Ayuda

Si después de seguir estos pasos aún tienes problemas:

1. Revisa los logs de error en la consola
2. Verifica que las credenciales JSON estén en el lugar correcto
3. Asegúrate de que la URL del documento en `secrets.toml` sea correcta
4. Verifica que el formato del documento sea el esperado

---

## 📌 Notas Importantes

- Las recetas se cargan **en tiempo real** desde Google Docs
- No necesitas reiniciar la aplicación después de agregar recetas
- Los cambios en Google Docs se reflejan inmediatamente
- El sistema busca recetas por código primero, luego por nombre
- Si una receta no se encuentra, verifica que el código/nombre coincida exactamente

