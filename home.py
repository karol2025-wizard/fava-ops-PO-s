import streamlit as st
import pandas as pd
from PIL import Image
import base64

# Page configuration
st.set_page_config(
    page_title="Company Resources Hub - Ivan OPS App",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded"
)


# Custom CSS
def add_custom_css():
    st.markdown("""
    <style>
    .main {
        background-color: #f5f7f9;
    }
    .card {
        border-radius: 10px;
        padding: 20px;
        margin-bottom: 20px;
        background-color: white;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease, box-shadow 0.3s ease;
    }
    .card:hover {
        transform: translateY(-5px);
        box-shadow: 0 10px 20px rgba(0, 0, 0, 0.1);
    }
    .card-title {
        font-size: 20px;
        font-weight: 600;
        margin-bottom: 10px;
        color: #1E3A8A;
    }
    .card-description {
        color: #4B5563;
        margin-bottom: 15px;
    }
    .btn-primary {
        background-color: #1E3A8A;
        color: white;
        padding: 10px 20px;
        border-radius: 5px;
        text-decoration: none;
        font-weight: 500;
        display: inline-block;
        text-align: center;
        margin-top: 10px;
        transition: background-color 0.3s ease;
    }
    .btn-primary:hover {
        background-color: #1E40AF;
    }
    .header {
        padding: 20px 0;
        text-align: center;
        margin-bottom: 30px;
    }
    .header h1 {
        color: #1E3A8A;
        font-size: 36px;
        font-weight: 700;
    }
    .header p {
        color: #4B5563;
        font-size: 18px;
    }
    .footer {
        text-align: center;
        margin-top: 50px;
        padding: 20px 0;
        color: #6B7280;
        font-size: 14px;
    }
    </style>
    """, unsafe_allow_html=True)


add_custom_css()

# Resources data
sheets = [
    {
        "title": "Item Central",
        "description": "Central inventory management and item tracking database.",
        "icon": "📦",
        "url": "https://docs.google.com/spreadsheets/d/1PKEY_ofj9dUxuvV1v9yaR81AcOS-2ghragW_pw6_EgI",
    },
    {
        "title": "Purchaser",
        "description": "Purchasing records and vendor management system.",
        "icon": "🛒",
        "url": "https://docs.google.com/spreadsheets/d/1CIESigXtLj2Fc4fRsrtmGkud2nGblSP5CqO7zWadH7o",
    },
    {
        "title": "Folfol Order Form",
        "description": "",
        "icon": "📝",
        "url": "https://docs.google.com/spreadsheets/d/1ySLLzGPy5qypHY15fP6GxnBJyEnoLMz6oKqQa673SQM",
    },
    {
        "title": "Damas Order Form",
        "description": "",
        "icon": "📝",
        "url": "https://docs.google.com/spreadsheets/d/1md588Ah8uVzxeUDcN7WXqKF1VwVjrLz_G-6qRp8JJe4",
    }
]

# Header
st.markdown('<div class="header">', unsafe_allow_html=True)
st.markdown('<h1>Fava Cuisine - Central Hub</h1>', unsafe_allow_html=True)
st.markdown('</div>', unsafe_allow_html=True)

# Main content
col1, col2 = st.columns([1, 3])

with col1:
    st.markdown("### Quick Navigation")
    for i, sheet in enumerate(sheets):
        if st.button(f"{sheet['icon']} {sheet['title']}", key=f"nav_{i}"):
            st.session_state.active_tab = i

    st.markdown("---")



with col2:
    # Resource cards in a grid
    for i in range(0, len(sheets), 2):
        cols = st.columns(2)
        for j in range(2):
            if i + j < len(sheets):
                sheet = sheets[i + j]
                with cols[j]:
                    st.markdown(f"""
                    <div class="card">
                        <div style="font-size: 40px; margin-bottom: 15px;">{sheet['icon']}</div>
                        <div class="card-title">{sheet['title']}</div>
                        <div class="card-description">{sheet['description']}</div>
                        <a href="{sheet['url']}" target="_blank" class="btn-primary">Open Sheet</a>
                    </div>
                    """, unsafe_allow_html=True)

# Display the image
image_path = "media/sad-face-pictures.jpg"  # Replace with your actual file path
st.image(image_path, caption="A Sad Face", use_container_width=True)


