# Antes de hacer commit

Checklist para mantener el código limpio y escalable:

## 1. Quitar código que no se usa

- Borrar archivos obsoletos o stubs que ya no hacen falta (ej. scripts que solo redirigen).
- Quitar imports sin usar y funciones/variables muertas.
- No commitear `dist/`, `build/`, backups temporales ni archivos generados.

## 2. Revisar la complejidad

- ¿Hace falta toda esta lógica o se puede simplificar?
- ¿Un solo script puede hacer el trabajo de dos muy parecidos?
- Evitar duplicar: si dos .bat hacen lo mismo, que uno llame al otro.

## 3. Pensar en rendimiento a escala

- APIs/DB: evitar llamadas en bucle cuando se pueda hacer una sola (batch).
- Usar caché donde aplique (`@st.cache_data`, TTL adecuado).
- En listas grandes: paginar o limitar resultados si tiene sentido.

---

*Resumen: menos código, menos duplicación, menos llamadas por elemento.*
