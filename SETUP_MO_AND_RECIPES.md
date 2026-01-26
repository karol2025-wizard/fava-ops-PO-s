# 🏭 Setup y Testing - MO and Recipes

Guía rápida para configurar y testear `mo_and_recipes.py` en otros computadores.

## ✅ Optimizaciones Implementadas

### 🚀 Performance Improvements
- **API Calls Optimizados**: Reducción de 1 llamada API por producto a 0 (usa caché)
- **Caché Inteligente**: Items y units se cachean por 6 horas
- **Logging de Performance**: Tracking de optimizaciones aplicadas

### 🧹 Code Quality
- Código limpio y documentado
- Manejo robusto de errores
- Paths relativos (funciona en cualquier sistema)

## 📋 Requisitos Previos

1. **Python 3.8+**
2. **Dependencias instaladas**:
   ```bash
   pip install -r requirements.txt
   ```

3. **Configuración de Secrets** (`.streamlit/secrets.toml`):
   ```toml
   # MRPeasy API (REQUERIDO)
   MRPEASY_API_KEY = "m40512u5e7b84632c"
   MRPEASY_API_SECRET = "vB)s,#geXwp1Gz9Lvqm"?kZ2b{j0"
   
   # Google Credentials (OPCIONAL - solo para ver recetas)
   GOOGLE_CREDENTIALS_PATH = "credentials/tu-archivo.json"
   ```

## 🚀 Inicio Rápido

### 1. Verificar Instalación
```bash
# Verificar que Streamlit está instalado
streamlit --version

# Verificar que todas las dependencias están instaladas
pip list | grep -E "streamlit|reportlab|PyPDF2|google"
```

### 2. Ejecutar la Aplicación
```bash
# Desde la raíz del proyecto
streamlit run pages/mo_and_recipes.py
```

O usar el script incluido:
```bash
# Windows
run_streamlit.bat

# Linux/Mac
./run_streamlit.ps1
```

### 3. Verificar Funcionalidad

#### Test 1: Caché de Items
1. Abre la aplicación
2. Verifica en el sidebar que muestra "Items cache initialized"
3. Debería mostrar el número de items cargados

#### Test 2: Crear MO (Single)
1. Selecciona "🏭 Generate MO"
2. Selecciona una categoría
3. Selecciona un item
4. Ingresa cantidad y crea el MO
5. **Verifica en logs**: Debe mostrar "Using cached article_id" (no API call)

#### Test 3: Crear MO (Batch)
1. Selecciona "🏭 Generate MO"
2. Selecciona una categoría
3. Selecciona un item
4. Ve a tab "⚡ Batch Creation"
5. Ingresa item code, cantidad y fecha
6. **Verifica en logs**: Debe mostrar "Performance: Using cached article_id" (0 API calls)

#### Test 4: Ver Recetas
1. Selecciona "📋 Print Recipe"
2. Selecciona una categoría
3. Selecciona un item
4. Debe mostrar la receta desde Google Docs o ZIP

## 🔍 Verificación de Optimizaciones

### Logs de Performance
Busca en la consola estos mensajes:

✅ **Optimización aplicada**:
```
Performance: Using cached article_id for A1234 (saved 1 API call)
```

⚠️ **Fallback a API** (si item no está en caché):
```
Item A1234 not found in cache, falling back to API lookup (1 API call required)
```

### Métricas Esperadas

| Operación | API Calls Antes | API Calls Después |
|-----------|----------------|-------------------|
| Single MO Creation | 1 | 0 (usa caché) |
| Batch MO Creation | 1 por producto | 0 (usa caché) |
| View Recipe | 0 | 0 (usa Google Docs/ZIP) |

## 🐛 Troubleshooting

### Error: "MRPEASY_API_KEY not found"
**Solución**: Verifica que `.streamlit/secrets.toml` existe y tiene las credenciales correctas.

### Error: "Item not found in cache"
**Solución**: 
1. Click en "🔄 Refresh Data" en la página
2. Verifica que el item code existe en MRPeasy
3. Verifica que el item está en `ALLOWED_ITEM_CODES`

### Error: "Credentials file not found"
**Solución**: 
- Si solo quieres crear MOs, esto es opcional
- Si quieres ver recetas, verifica que `GOOGLE_CREDENTIALS_PATH` apunta al archivo correcto

### Performance: "Cache needs refresh"
**Solución**: 
- El caché expira después de 6 horas
- Click en "🔄 Refresh Data" para forzar actualización

## 📊 Estructura de Archivos Necesarios

```
fava-ops-PO's/
├── pages/
│   └── mo_and_recipes.py          # ✅ Archivo optimizado
├── shared/
│   ├── api_manager.py              # ✅ Gestión de API
│   └── gdocs_manager.py            # ✅ Gestión de Google Docs
├── credentials/                    # Opcional
│   └── tu-archivo.json
├── recipes_split/                  # Opcional (para recetas ZIP)
│   └── recipespdf.zip
├── .streamlit/
│   └── secrets.toml               # ⚠️ REQUERIDO
└── requirements.txt                # ✅ Dependencias
```

## ✅ Checklist Pre-Deployment

- [ ] `requirements.txt` está actualizado
- [ ] `.streamlit/secrets.toml` configurado con credenciales válidas
- [ ] Código sin errores de linting (`read_lints` pasa)
- [ ] Paths relativos funcionan (no paths absolutos hardcodeados)
- [ ] Caché funciona correctamente (ver logs)
- [ ] Creación de MO funciona (single y batch)
- [ ] Visualización de recetas funciona (si Google Docs configurado)

## 📝 Notas Importantes

1. **Caché**: Los items se cachean por 6 horas. Si agregas nuevos items en MRPeasy, necesitas refrescar el caché.

2. **API Rate Limits**: Con las optimizaciones, reduces significativamente las llamadas a la API, evitando rate limits.

3. **Legacy States**: El código mantiene compatibilidad con estados legacy. Pueden removerse en el futuro si la migración está completa.

4. **Performance**: Para 100 productos, ahora haces 0-1 API calls en lugar de 100.

## 🎯 Próximos Pasos

1. Testear en diferentes computadores
2. Monitorear logs de performance
3. Verificar que no hay regresiones
4. Considerar remover legacy states si no se usan

---

**Última actualización**: Optimizaciones de performance completadas ✅
**Versión**: Optimizada para producción
