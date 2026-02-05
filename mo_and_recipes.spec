# -*- mode: python ; coding: utf-8 -*-
"""
Archivo de especificación de PyInstaller para mo_and_recipes.py
"""

import os
from pathlib import Path

# Obtener la ruta del proyecto
project_root = Path(SPECPATH)

# Lista de archivos de datos a incluir
datas = []

# Verificar y agregar archivos si existen
files_to_check = [
    ('pages/mo_and_recipes.py', 'pages'),
    ('shared', 'shared'),
    ('config.py', '.'),
    ('credentials', 'credentials'),
    ('.streamlit', '.streamlit'),
    ('media', 'media'),
]

for src, dst in files_to_check:
    src_path = project_root / src
    if src_path.exists():
        datas.append((str(src_path), dst))
        print(f"Incluyendo: {src} -> {dst}")

a = Analysis(
    ['build_exe_wrapper.py'],
    pathex=[str(project_root)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        'streamlit',
        'streamlit.web.cli',
        'streamlit.runtime.scriptrunner',
        'pandas',
        'numpy',
        'PIL',
        'PIL.Image',
        'reportlab',
        'reportlab.lib',
        'reportlab.lib.colors',
        'reportlab.lib.pagesizes',
        'reportlab.lib.styles',
        'reportlab.lib.units',
        'reportlab.platypus',
        'reportlab.lib.enums',
        'reportlab.graphics',
        'reportlab.graphics.barcode',
        'reportlab.graphics.barcode.code128',
        'googleapiclient',
        'googleapiclient.discovery',
        'googleapiclient.errors',
        'google.auth',
        'google.oauth2',
        'google.oauth2.service_account',
        'gspread',
        'gspread_dataframe',
        'requests',
        'toml',
        'config',
        'shared',
        'shared.api_manager',
        'shared.gdocs_manager',
        'shared.gsheets_manager',
        'shared.database_manager',
        'shared.database_operations',
        'shared.production_workflow',
        'oauth2client',
        'oauth2client.service_account',
    ],
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=['matplotlib', 'scipy', 'IPython', 'jupyter'],
    noarchive=False,
    optimize=0,
)

pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name='mo_and_recipes',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,  # Mostrar consola para ver errores
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
