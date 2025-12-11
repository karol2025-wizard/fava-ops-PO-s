# Fava Operations PO's

Sistema de gestión de Purchase Orders (PO) para operaciones de Fava.

## 🚀 Configuración Inicial

### Requisitos Previos

- Python 3.8 o superior
- Streamlit
- Credenciales de Google Service Account
- Acceso a Google Sheets y Google Docs

### Instalación

1. Clona el repositorio:
```bash
git clone https://github.com/karol2025-wizard/fava-ops-PO-s.git
cd fava-ops-PO-s
```

2. Instala las dependencias:
```bash
pip install -r requirements.txt
```

3. Configura las credenciales (ver sección de Configuración)

### ⚙️ Configuración

#### 1. Credenciales de Google

1. Coloca tus archivos de credenciales JSON en la carpeta `credentials/`
2. Configura la ruta en `.streamlit/secrets.toml`:
```toml
GOOGLE_CREDENTIALS_PATH = "credentials/tu-archivo-credenciales.json"
```

#### 2. Configuración de Secrets

Crea o edita el archivo `.streamlit/secrets.toml` con tus configuraciones:

```toml
# Google Credentials
GOOGLE_CREDENTIALS_PATH = "credentials/tu-archivo.json"

# PO Sheet Configuration (for generar_csv_gfs.py)
PO_SHEET_URL = "https://docs.google.com/spreadsheets/d/TU_SHEET_ID"
PO_WORKSHEET_NAME = "PO"
PO_COLUMN_NAME = "PO_Number"
GFS_TEMPLATE_CSV_PATH = "media/csv_template_french-v3.csv"

# Otras configuraciones según necesites...
```

**⚠️ IMPORTANTE:** 
- El archivo `secrets.toml` NO debe ser commiteado a Git
- Las credenciales JSON deben estar en `.gitignore`
- Nunca compartas tus API keys o credenciales

#### 3. Compartir Google Sheets

Para que la aplicación funcione, debes compartir tus Google Sheets con la cuenta de servicio:

1. Abre tu Google Sheet
2. Haz clic en "Compartir"
3. Agrega el email de la cuenta de servicio (encontrado en tu archivo JSON de credenciales)
4. Dale permisos de "Editor" o "Lector"

### 🏃 Ejecutar la Aplicación

```bash
streamlit run home.py
```

La aplicación estará disponible en `http://localhost:8501`

## 📁 Estructura del Proyecto

```
fava-ops-PO-s/
├── credentials/          # Credenciales (NO commiteadas)
├── .streamlit/          # Configuración de Streamlit
│   └── secrets.toml     # Secrets (NO commiteado)
├── pages/               # Páginas de la aplicación
├── shared/              # Módulos compartidos
├── media/               # Archivos multimedia y templates
├── clover_sales_analysis/
├── silverware_sales_analysis/
└── requirements.txt     # Dependencias
```

## 🔒 Seguridad

- **NUNCA** commitees archivos con credenciales
- **NUNCA** commitees `secrets.toml`
- **NUNCA** commitees archivos JSON de credenciales
- Usa variables de entorno o `secrets.toml` para configuraciones sensibles

## 📝 Páginas Disponibles

- **Generate CSV for GFS**: Genera archivos CSV para importar a GFS desde números de PO
- **Barcode PO**: Gestión de códigos de barras para PO
- **ERP Operations**: Operaciones relacionadas con el ERP
- Y más...

## 🤝 Contribuir

1. Fork el proyecto
2. Crea una rama para tu feature (`git checkout -b feature/AmazingFeature`)
3. Commit tus cambios (`git commit -m 'Add some AmazingFeature'`)
4. Push a la rama (`git push origin feature/AmazingFeature`)
5. Abre un Pull Request

## 📄 Licencia

Este proyecto es privado y confidencial.

## ⚠️ Notas Importantes

- Asegúrate de tener las credenciales configuradas antes de ejecutar la aplicación
- Verifica que los Google Sheets estén compartidos con la cuenta de servicio
- Revisa la configuración en `.streamlit/secrets.toml` antes de iniciar


