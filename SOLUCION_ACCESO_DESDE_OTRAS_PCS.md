# Solución: Acceso a MO and Recipes desde Otras PCs

## Problema
Cuando otras PCs intentan abrir `http://localhost:8504/`, no funciona porque `localhost` solo se refiere a la máquina local donde se ejecuta el servidor.

## Solución

### Opción 1: Usar la IP de la Máquina Servidor (Recomendado)

1. **En la PC que ejecuta el servidor:**
   - Ejecuta el script `obtener_url_acceso.bat` para obtener tu IP local
   - O ejecuta `ipconfig` en la terminal y busca tu "Dirección IPv4"

2. **Usa la IP en lugar de localhost:**
   - En lugar de: `http://localhost:8504/mo_and_recipes`
   - Usa: `http://TU_IP:8504/mo_and_recipes`
   - Ejemplo: `http://192.168.1.100:8504/mo_and_recipes`

3. **Comparte esta URL con las otras PCs:**
   - La URL será algo como: `http://192.168.1.100:8504/mo_and_recipes`
   - Cada PC en la red puede usar esta misma URL

### Opción 2: Configuración Automática

Los scripts `run_streamlit.bat` y `run_streamlit.ps1` ahora están configurados para:
- Escuchar en todas las interfaces de red (0.0.0.0)
- Mostrar automáticamente la IP local cuando se inicia el servidor
- Permitir acceso desde otras PCs en la misma red

## Pasos para Configurar

### 1. Ejecutar el Servidor

**Opción A: Script original (puede necesitar ajustes manuales)**
```batch
run_streamlit.bat
```

**Opción B: Script mejorado (recomendado)**
```batch
run_streamlit_red.bat
```

O si prefieres PowerShell:
```powershell
.\run_streamlit.ps1
```

El script mostrará automáticamente:
- La URL local: `http://localhost:8504/`
- La URL de red: `http://TU_IP:8504/`

### 2. Obtener la URL Correcta
Ejecuta:
```batch
obtener_url_acceso.bat
```

Este script:
- Obtiene tu IP local automáticamente
- Muestra las URLs correctas
- Copia la URL al portapapeles para compartir fácilmente

### 3. Configurar el Firewall (Si es necesario)

Si otras PCs no pueden conectarse, es posible que el firewall de Windows esté bloqueando el puerto 8504.

**Para permitir el acceso:**
1. Abre "Firewall de Windows Defender" en el Panel de Control
2. Haz clic en "Configuración avanzada"
3. Haz clic en "Reglas de entrada" → "Nueva regla"
4. Selecciona "Puerto" → Siguiente
5. Selecciona "TCP" y escribe `8504` en "Puertos locales específicos"
6. Selecciona "Permitir la conexión"
7. Aplica a todos los perfiles
8. Dale un nombre como "Streamlit MO and Recipes"

**Opción rápida:** Ejecuta el script `configurar_firewall.bat` como Administrador:
```batch
configurar_firewall.bat
```

O ejecuta este comando manualmente como Administrador:
```batch
netsh advfirewall firewall add rule name="Streamlit MO and Recipes" dir=in action=allow protocol=TCP localport=8504
```

## Verificación

### Desde la PC Servidor:
- Abre: `http://localhost:8504/mo_and_recipes`
- Debe funcionar correctamente

### Desde Otra PC en la Red:
1. Asegúrate de que ambas PCs estén en la misma red local
2. Abre el navegador en la otra PC
3. Ve a: `http://IP_DEL_SERVIDOR:8504/mo_and_recipes`
   - Reemplaza `IP_DEL_SERVIDOR` con la IP que obtuviste del script

## Troubleshooting

### Problema: "No se puede acceder a este sitio"
**Solución:**
- Verifica que el servidor Streamlit esté corriendo
- Verifica que estés usando la IP correcta (no localhost)
- Verifica que el firewall permita conexiones en el puerto 8504
- Verifica que ambas PCs estén en la misma red

### Problema: La IP cambia cada vez
**Solución:**
- Configura una IP estática en la PC servidor
- O usa el script `obtener_url_acceso.bat` cada vez que necesites la URL

### Problema: El puerto 8504 está ocupado
**Solución:**
- Cierra otras aplicaciones que usen el puerto 8504
- O cambia el puerto en los scripts usando `--server.port=OTRO_PUERTO`

## Notas Importantes

1. **Seguridad:** Esta configuración permite acceso desde cualquier PC en tu red local. No expongas esto a Internet sin protección adicional.

2. **IP Dinámica:** Si tu PC obtiene su IP automáticamente (DHCP), la IP puede cambiar. Considera configurar una IP estática si necesitas una URL permanente.

3. **Misma Red:** Las otras PCs deben estar en la misma red local (mismo router/switch) para poder acceder.
