import streamlit as st
import pandas as pd
from pathlib import Path

st.set_page_config(
    page_title="Inventory by Location",
    page_icon="📦",
    layout="wide",
)


@st.cache_data
def load_inventory_from_csv(file) -> pd.DataFrame:
    df = pd.read_csv(file)
    expected_cols = [
        "Part No.",
        "Part description",
        "UoM",
        "Default storage location",
    ]
    missing = [c for c in expected_cols if c not in df.columns]
    if missing:
        raise ValueError(f"Las siguientes columnas no se encontraron en el CSV: {missing}")
    df = df[expected_cols].copy()
    df.rename(
        columns={
            "Part No.": "Part No",
            "Part description": "Description",
            "UoM": "UoM",
            "Default storage location": "Location",
        },
        inplace=True,
    )
    df["Location"] = df["Location"].fillna("Sin ubicación").astype(str)
    df["Part No"] = df["Part No"].astype(str)
    df["Description"] = df["Description"].astype(str)
    df["UoM"] = df["UoM"].astype(str)
    return df


st.title("Inventory organizado por Location")

st.markdown(
    """
Selecciona el archivo CSV exportado de MRPeasy (lista de Items).

Solo se usarán las columnas:
- **Part No**
- **Part description**
- **UoM**
- **Default storage location**
"""
)

uploaded_file = st.file_uploader("Sube el CSV de artículos", type=["csv"])

default_path = Path.home() / "Desktop" / "articles_20260227.csv"
use_default = False

if not uploaded_file and default_path.exists():
    use_default = st.checkbox(
        f"Usar archivo por defecto: {default_path.name}",
        value=True,
        help="Lee automáticamente el último export que tienes en el Desktop.",
    )

df_inventory: pd.DataFrame | None = None

try:
    if uploaded_file is not None:
        df_inventory = load_inventory_from_csv(uploaded_file)
    elif use_default:
        df_inventory = load_inventory_from_csv(default_path)
except ValueError as e:
    st.error(str(e))
except Exception as e:
    st.error(f"Error leyendo el CSV: {e}")

if df_inventory is None:
    st.info("Sube un CSV o activa el archivo por defecto para ver el inventario.")
    st.stop()

st.subheader("Filtros")

# Overrides manuales de ubicación para ciertos productos
LOCATION_OVERRIDES = {
    "A1704": "Packaging",
    "A1705": "Packaging",
    "A1706": "Packaging",
    "A1707": "Packaging",
    "A1708": "Packaging",
    "A1709": "Packaging",
    "A1710": "Packaging",
    "A1711": "Packaging",
    "A1712": "Packaging",
    "A1713": "Packaging",
    "A1714": "Packaging",
    "A1715": "Packaging",
    "A1721": "Packaging",
    "A1724": "Sanitation",
    "A1725": "Sanitation",
    "A1728": "Dry",
    "A1733": "Dry",
    "A1734": "Dry",
    "A1739": "Dry",
    "A1741": "Dry",
    "A1743": "Dry",
    "A1744": "Dry",
    "A1745": "Dry",
    "A1811": "Sanitation",
    "A1835": "Dry",
    "A1846": "Packaging",
    "A1857": "Packaging",
    "A1879": "Fridge-5",
    "A1885": "Dry",
    "A1910": "Dry",
    "A1911": "Dry",
    "A1921": "Dry",
    "A1931": "Dry",
    "A1933": "Dry",
    "A1934": "Dry",
    "A1937": "Dry",
    "A1938": "Dry",
    "A1939": "Packaging",
    "A1940": "Packaging",
    "A1953": "Dry",
    "A1996": "Dry",
    "A1997": "Dry",
    "A2001": "Dry",
    "A2015": "Packaging",
}

if not df_inventory.empty:
    df_inventory = df_inventory.copy()
    df_inventory["Location"] = (
        df_inventory["Part No"]
        .map(LOCATION_OVERRIDES)
        .fillna(df_inventory["Location"])
    )

col1, col2 = st.columns([2, 1])

with col1:
    search_text = st.text_input(
        "Buscar por Part No o descripción",
        value="",
        placeholder="Ej. A00536, Duck, Rice, etc.",
    ).strip()

with col2:
    locations = sorted(df_inventory["Location"].unique())
    selected_locations = st.multiselect(
        "Filtrar por Location",
        options=locations,
        default=locations,
    )

df_filtered = df_inventory[df_inventory["Location"].isin(selected_locations)].copy()

if search_text:
    s = search_text.lower()
    df_filtered = df_filtered[
        df_filtered["Part No"].str.lower().str.contains(s)
        | df_filtered["Description"].str.lower().str.contains(s)
    ]

st.markdown("---")

st.subheader("Inventario agrupado por Location")

if df_filtered.empty:
    st.warning("No hay registros que coincidan con los filtros actuales.")
    st.stop()

df_filtered = df_filtered.copy()
df_filtered["Real stock"] = 0.0
df_filtered = df_filtered[["Part No", "Description", "UoM", "Location", "Real stock"]]

# Lista curada de ítems visibles en la sección Dry
DRY_PARTS_WHITELIST = [
    "A00554", "A00555", "A00564", "A00565", "A00566", "A00586",
    "A00605", "A00606", "A00620", "A1013", "A1014", "A1030", "A1102",
    "A1104", "A1108", "A1109", "A1110", "A1114", "A1116", "A1117",
    "A1119", "A1123", "A1124", "A1125", "A1127", "A1130", "A1131",
    "A1132", "A1133", "A1135", "A1136", "A1139", "A1141", "A1143",
    "A1144", "A1146", "A1147", "A1148", "A1150", "A1151", "A1178",
    "A1179", "A1180", "A1181", "A1182", "A1183", "A1184", "A1185",
    "A1186", "A1187", "A1188", "A1189", "A1190", "A1192", "A1193",
    "A1195", "A1196", "A1197", "A1198", "A1200", "A1201", "A1203",
    "A1204", "A1205", "A1206", "A1207", "A1211", "A1213", "A1215",
    "A1218", "A1219", "A1237", "A1283", "A1284", "A1313", "A1320",
    "A1328", "A1329", "A1375", "A1385", "A1403", "A1407", "A1408",
    "A1410", "A1411", "A1417", "A1418", "A1419", "A1420", "A1421",
    "A1422", "A1425", "A1428", "A1429", "A1431", "A1434", "A1435",
    "A1437", "A1440", "A1458", "A1486", "A1488", "A1492", "A1505",
    "A1519", "A1526", "A1576", "A1578", "A1579", "A1582", "A1583",
    "A1585", "A1636", "A1637", "A1643", "A1656", "A1657", "A1659",
    "A1661", "A1662", "A1700", "A1701", "A1704", "A1705", "A1706",
    "A1707", "A1708", "A1709", "A1710", "A1711", "A1712", "A1713",
    "A1714", "A1715", "A1721", "A1724", "A1725", "A1728", "A1730",
    "A1731", "A1733", "A1734", "A1735", "A1739", "A1741", "A1743",
    "A1744", "A1745", "A1811", "A1835", "A1846", "A1857", "A1879",
    "A1885", "A1910", "A1911", "A1921", "A1931", "A1933", "A1934",
    "A1937", "A1938", "A1939", "A1940", "A1945",
    "A1953", "A1996", "A1997", "A2001", "A2015",
]

# Dejar en la sección Dry solo los ítems de la lista anterior
is_dry = df_filtered["Location"] == "Dry"
mask_keep_dry = is_dry & df_filtered["Part No"].isin(DRY_PARTS_WHITELIST)
non_dry_rows = ~is_dry
df_filtered = pd.concat(
    [df_filtered[non_dry_rows], df_filtered[mask_keep_dry]],
    ignore_index=True,
)

# Lista curada de ítems visibles en la sección Fridge-1
FRIDGE1_PARTS_WHITELIST = [
    "A1349",
    "A1484",
    "A1499",
    "A1518",
    "A1543",
    "A1547",
    "A1554",
    "A1575",
    "A1612",
    "A1619",
    "A1631",
    "A1639",
    "A1647",
    "A1653",
    "A1876",
    "A1903",
    "A1952",
    "A1990",
]

# Dejar en la sección Fridge-1 solo los ítems de la lista anterior
is_fridge1 = df_filtered["Location"] == "Fridge-1"
mask_keep_fridge1 = is_fridge1 & df_filtered["Part No"].isin(FRIDGE1_PARTS_WHITELIST)
non_fridge1_rows = ~is_fridge1
df_filtered = pd.concat(
    [df_filtered[non_fridge1_rows], df_filtered[mask_keep_fridge1]],
    ignore_index=True,
)

grouped = df_filtered.groupby("Location")

edited_groups = []

for location, df_loc in grouped:
    with st.expander(f"{location}  —  {len(df_loc)} items", expanded=False):
        edited_loc = st.data_editor(
            df_loc[["Part No", "Description", "UoM", "Real stock"]]
            .sort_values("Part No")
            .reset_index(drop=True),
            use_container_width=True,
            num_rows="fixed",
            hide_index=True,
            column_config={
                "Real stock": st.column_config.NumberColumn(
                    "Real stock",
                    help="Cantidad real que tienes en inventario para esta ubicación.",
                    min_value=0.0,
                    step=0.1,
                )
            },
            key=f"editor_{location}",
        )
        edited_loc["Location"] = location
        edited_groups.append(edited_loc)

if edited_groups:
    edited_df = pd.concat(edited_groups, ignore_index=True)
    download_df = edited_df.sort_values(["Location", "Part No"])
else:
    edited_df = df_filtered
    download_df = df_filtered.sort_values(["Location", "Part No"])

csv_buffer = download_df.to_csv(index=False).encode("utf-8-sig")

st.download_button(
    label="⬇️ Descargar CSV filtrado (incluye Real stock)",
    data=csv_buffer,
    file_name="inventory_by_location_with_real_stock.csv",
    mime="text/csv",
)
