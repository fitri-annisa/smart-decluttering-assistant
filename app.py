import streamlit as st
import asyncio
import os
import tempfile
from orchestrator import run_decluttering_flow
from inventory_db import init_db, save_item, get_inventory, delete_inventory_item

# Set up Streamlit Page configuration
st.set_page_config(
    page_title="Smart Decluttering Assistant",
    page_icon="🧹",
    layout="wide"
)

# Initialize the SQLite database tables
init_db()

# ----------------- TRANSLATION DICTIONARY -----------------
TRANSLATIONS = {
    "Bahasa Indonesia": {
        "title": "🧹 Smart Decluttering Assistant",
        "subtitle": "Ubah tumpukan barang tak terpakai menjadi keputusan cerdas dan actionable secara instan.",
        "history_title": "Riwayat Inventori",
        "empty_history": "Belum ada barang di inventori.",
        "total_items": "Total barang: {count}",
        "input_header": "🔍 Input Detail Barang",
        "desc_label": "Deskripsikan barang Anda:",
        "desc_placeholder": "Contoh: Kemeja flanel merah merek Erigo ukuran XL, kondisi mulus tanpa sobek, kancing lengkap semua.",
        "img_label": "Upload foto barang (opsional):",
        "intent_label": "Apa tujuan Anda?",
        "intent_options": [
            "Tidak tahu / Bantu putuskan (default)",
            "Ingin menjual",
            "Ingin donasikan",
            "Ingin perbaiki",
            "Ingin daur ulang"
        ],
        "btn_analyze": "Analisa Barang",
        "loading_msg": "Sedang menganalisis...",
        "save_msg": "Hasil analisis otomatis disimpan ke inventori!",
        "results_header": "📊 Hasil Analisis Agen AI",
        "prompt_info": "Silakan masukkan input di kolom kiri dan tekan tombol 'Analisa Barang'.",
        "brand": "Merek",
        "age": "Umur Perkiraan",
        "years": "Tahun",
        "condition": "Kondisi Hasil Analisis",
        "best_decision": "Keputusan Terbaik",
        "scores_header": "Skor Tiap Opsi Kelayakan",
        "reco_header": "Rekomendasi Utama",
        "steps_header": "Langkah Selanjutnya:",
        "locations_header": "Lokasi & Tautan Referensi Relevan",
        "no_locations": "Tidak ada lokasi referensi khusus ditemukan.",
        "visit_ref": "Kunjungi Tautan Referensi ↗",
        "delete_btn": "Hapus",
        "success_delete": "Barang dihapus!"
    },
    "English": {
        "title": "🧹 Smart Decluttering Assistant",
        "subtitle": "Turn clutter into smart, actionable decluttering decisions instantly.",
        "history_title": "Inventory History",
        "empty_history": "No items in inventory yet.",
        "total_items": "Total items: {count}",
        "input_header": "🔍 Input Item Details",
        "desc_label": "Describe your item:",
        "desc_placeholder": "Example: Red flannel shirt by Erigo, size XL, excellent condition with no tears, all buttons intact.",
        "img_label": "Upload item photo (optional):",
        "intent_label": "What is your goal?",
        "intent_options": [
            "Don't know / Help me decide (default)",
            "Want to sell",
            "Want to donate",
            "Want to repair",
            "Want to recycle"
        ],
        "btn_analyze": "Analyze Item",
        "loading_msg": "Analyzing...",
        "save_msg": "Analysis results automatically saved to inventory!",
        "results_header": "📊 AI Agent Analysis Results",
        "prompt_info": "Please enter the input on the left panel and click 'Analyze Item'.",
        "brand": "Brand",
        "age": "Estimated Age",
        "years": "Years",
        "condition": "Analysis Condition Result",
        "best_decision": "Best Decision",
        "scores_header": "Option Feasibility Scores",
        "reco_header": "Main Recommendation",
        "steps_header": "Next Steps:",
        "locations_header": "Relevant Locations & Reference Links",
        "no_locations": "No specific reference locations found.",
        "visit_ref": "Visit Reference Link ↗",
        "delete_btn": "Delete",
        "success_delete": "Item deleted!"
    }
}

# ----------------- SIDEBAR CONTROLS -----------------
# Initialize session state for language selection if not present
if "language_choice" not in st.session_state:
    st.session_state["language_choice"] = "Bahasa Indonesia"

# 1. Language Selector Pills (Horizontal Radio control)
st.sidebar.markdown("<div style='font-size: 0.8rem; font-weight: 600; margin-bottom: 0.3rem; opacity: 0.7; font-family: \"Inter\", sans-serif;'>LANGUAGE / BAHASA</div>", unsafe_allow_html=True)
lang_choice = st.sidebar.radio(
    "Language Selection",
    ["🇮🇩 ID", "🇬🇧 EN"],
    index=0 if st.session_state["language_choice"] == "Bahasa Indonesia" else 1,
    horizontal=True,
    label_visibility="collapsed"
)

if lang_choice == "🇮🇩 ID":
    st.session_state["language_choice"] = "Bahasa Indonesia"
else:
    st.session_state["language_choice"] = "English"

lang = st.session_state["language_choice"]
t = TRANSLATIONS[lang]

# 2. Dark/Light Theme Toggle (Subtle toggle control)
light_theme = st.sidebar.toggle("☀️ Light Mode", value=False)

# Theme Style Calculations
if light_theme:
    bg_color = "#FAFAFA"
    card_bg = "#FFFFFF"
    text_color = "#1A1A1A"
    border_color = "#E0E0E0"
    sec_text_color = "#666666"
    sidebar_bg = "#FFFFFF"
    sidebar_text = "#1A1A1A"
    hero_bg = "linear-gradient(180deg, #F3F3F3 0%, #FAFAFA 100%)"
    code_bg = "#EAEAEA"
    code_text = "#4CAF82"
else:
    bg_color = "#111111"
    card_bg = "#1E1E1E"
    text_color = "#F0F0F0"
    border_color = "#2A2A2A"
    sec_text_color = "#888888"
    sidebar_bg = "#1A1A1A"
    sidebar_text = "#F0F0F0"
    hero_bg = "linear-gradient(180deg, #1E1E1E 0%, #111111 100%)"
    code_bg = "#2A2A2A"
    code_text = "#4CAF82"

# Injected CSS Typography and Aesthetics
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&family=Plus+Jakarta+Sans:wght@400;500;600;700;800&display=swap');
    
    /* Global Background and Fonts */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Inter', sans-serif !important;
    }}
    
    h1, h2, h3, h4, h5, h6 {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        color: {text_color} !important;
        font-weight: 700 !important;
    }}
    
    .hero-banner {{
        background: {hero_bg};
        border-radius: 16px;
        padding: 2.5rem 1.5rem;
        margin-bottom: 2rem;
        border: 1px solid {border_color};
        text-align: center;
    }}
    
    .hero-title {{
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        font-size: 2.8rem;
        font-weight: 800;
        letter-spacing: -1px;
        color: {text_color} !important;
        margin-bottom: 0.5rem;
        line-height: 1.1;
    }}
    
    .hero-subtitle {{
        font-family: 'Inter', sans-serif !important;
        font-size: 1.15rem;
        color: {sec_text_color};
        font-weight: 400;
        margin: 0 auto;
        max-width: 600px;
    }}
    
    .input-card {{
        background-color: {card_bg};
        border-radius: 16px;
        padding: 1.8rem;
        border: 1px solid {border_color};
        margin-bottom: 2rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.01);
    }}
    
    .result-card {{
        background-color: {card_bg};
        border-radius: 16px;
        padding: 1.8rem;
        border: 1px solid {border_color};
        margin-bottom: 1.5rem;
        box-shadow: 0 4px 12px rgba(0,0,0,0.01);
    }}
    
    .card {{
        background-color: {card_bg};
        border-radius: 12px;
        padding: 1.2rem;
        border: 1px solid {border_color};
        margin-bottom: 1.2rem;
        color: {text_color};
    }}
    
    /* Notion/Linear clean style for st.container(border=True) */
    div[data-testid="stVerticalBlockBorderWrapper"] {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 16px !important;
        padding: 1.5rem !important;
        box-shadow: 0 4px 12px rgba(0,0,0,0.01) !important;
        margin-bottom: 1.5rem !important;
    }}
    
    .highlight-card {{
        background-color: {card_bg};
        border: 1px solid {border_color};
        border-left: 5px solid #E8A87C;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        color: {text_color};
    }}
    
    .best-decision-badge {{
        display: inline-block;
        background-color: #E8A87C;
        color: #1A1A1A !important;
        padding: 0.4rem 1.2rem;
        border-radius: 30px;
        font-weight: 700;
        font-size: 1.1rem;
        margin-top: 0.5rem;
        margin-bottom: 1rem;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}
    
    .location-card {{
        background-color: {card_bg};
        border-radius: 10px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #4CAF82;
        border-right: 1px solid {border_color};
        border-top: 1px solid {border_color};
        border-bottom: 1px solid {border_color};
    }}
    
    .location-title {{
        font-weight: 700;
        color: {text_color} !important;
        font-size: 1.05rem;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
    }}
    
    .location-link {{
        font-size: 0.9rem;
        color: #4CAF82;
        text-decoration: none;
        font-weight: 600;
    }}
    
    .location-link:hover {{
        text-decoration: underline;
    }}
    
    .section-header {{
        font-size: 1.5rem;
        font-weight: 800;
        color: {text_color};
        margin-bottom: 1.2rem;
        font-family: 'Plus Jakarta Sans', sans-serif !important;
        letter-spacing: -0.3px;
    }}

    /* Sidebar Theme override */
    [data-testid="stSidebar"] {{
        background-color: {sidebar_bg} !important;
        color: {sidebar_text} !important;
        border-right: 1px solid {border_color} !important;
    }}
    
    [data-testid="stSidebar"] * {{
        color: {sidebar_text} !important;
    }}

    /* Force high contrast text colors on standard labels and markdown paragraphs */
    label,
    .stWidgetLabel,
    [data-testid="stWidgetLabel"] p,
    [data-testid="stMarkdownContainer"] p,
    [data-testid="stMarkdownContainer"] li,
    [data-testid="stMarkdownContainer"] span,
    [data-testid="stMarkdownContainer"] strong {{
        color: {text_color} !important;
        font-family: 'Inter', sans-serif !important;
    }}

    /* Selectbox dropdown container and values overrides */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] * {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    div[data-baseweb="popover"] ul {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
    }}
    div[data-baseweb="popover"] li {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
    }}
    div[data-baseweb="popover"] li:hover {{
        background-color: #4CAF82 !important;
        color: #FFFFFF !important;
    }}

    /* Text Area Input overrides */
    [data-testid="stTextArea"] textarea {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
        border-radius: 8px !important;
        min-height: 120px !important;
    }}
    textarea::placeholder {{
        color: {sec_text_color} !important;
        opacity: 0.7 !important;
    }}

    /* File Uploader overrides */
    [data-testid="stFileUploader"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px dashed {border_color} !important;
        border-radius: 8px !important;
        padding: 0.5rem !important;
    }}
    [data-testid="stFileUploader"] * {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}

    /* Primary Action Buttons styling: flat design */
    .stButton > button[kind="primary"] {{
        width: 100% !important;
        height: 52px !important;
        background-color: #2D2D2D !important;
        color: #FFFFFF !important;
        border: 1px solid #2D2D2D !important;
        border-radius: 12px !important;
        font-size: 1rem !important;
        font-weight: 600 !important;
        font-family: 'Inter', sans-serif !important;
        transition: all 0.2s ease !important;
        cursor: pointer !important;
        box-shadow: none !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        background-color: #4CAF82 !important;
        border-color: #4CAF82 !important;
        color: #FFFFFF !important;
        transform: none !important;
        box-shadow: none !important;
    }}
    .stButton > button[kind="primary"]:active {{
        background-color: #3e9c71 !important;
        border-color: #3e9c71 !important;
    }}

    /* Compact Delete Button styling inside sidebar */
    [data-testid="stSidebar"] button {{
        width: auto !important;
        height: 28px !important;
        padding: 0.1rem 0.4rem !important;
        font-size: 0.75rem !important;
        background-color: transparent !important;
        color: {sidebar_text} !important;
        border: 1px solid {border_color} !important;
        border-radius: 6px !important;
        font-weight: 400 !important;
    }}
    [data-testid="stSidebar"] button:hover {{
        background-color: rgba(220, 53, 69, 0.1) !important;
        border-color: #DC3545 !important;
        color: #DC3545 !important;
    }}
</style>
""", unsafe_allow_html=True)

# Helper function to draw custom styled progress bars
def draw_custom_progress(label, value):
    bar_bg = "#2A2A2A" if not light_theme else "#E0E0E0"
    st.markdown(f"""
    <div style="margin-bottom: 0.8rem; display: flex; align-items: center; justify-content: space-between;">
        <div style="width: 100px; font-size: 0.9rem; font-weight: 600; color: {text_color}; font-family: 'Inter', sans-serif;">{label}</div>
        <div style="flex-grow: 1; background-color: {bar_bg}; border-radius: 6px; height: 12px; margin: 0 1rem; overflow: hidden; position: relative;">
            <div style="background-color: #4CAF82; height: 100%; width: {value}%; border-radius: 6px;"></div>
        </div>
        <div style="width: 45px; text-align: right; font-size: 0.9rem; font-weight: 700; color: {text_color}; font-family: 'Inter', sans-serif;">{value}%</div>
    </div>
    """, unsafe_allow_html=True)

# ----------------- SIDEBAR INVENTORY LIST -----------------
st.sidebar.markdown(f"### 📦 {t['history_title']}")
inventory = get_inventory()

if not inventory:
    st.sidebar.info(t["empty_history"])
else:
    st.sidebar.caption(t["total_items"].replace("{count}", str(len(inventory))))
    st.sidebar.markdown("<div style='margin-bottom: 0.6rem;'></div>", unsafe_allow_html=True)
    
    # Render compact sidebar cards
    for item in inventory:
        dec = item['decision']
        # Determine colored border-left based on decision
        if dec == "Keep":
            border_color_left = "#4CAF82" # Hijau
        elif dec == "Repair":
            border_color_left = "#007BFF" # Biru
        elif dec == "Sell":
            border_color_left = "#E8A87C" # Kuning/Orange
        else: # Donate, Recycle
            border_color_left = "#FF6584" # Merah/Pink
            
        col_side_text, col_side_del = st.sidebar.columns([4.8, 1.2])
        with col_side_text:
            value_info = f"<br/><span style='font-size: 0.75rem; opacity: 0.75;'>Value: Rp {item['value_rp']:,}</span>" if item['value_rp'] > 0 else ""
            st.markdown(f"""
            <div style='background-color: {card_bg}; border-radius: 6px; padding: 0.5rem; border-left: 4px solid {border_color_left}; border-right: 1px solid {border_color}; border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color}; line-height: 1.25;'>
                <div style='font-size: 0.8rem; font-weight: 600; color: {sidebar_text}; overflow: hidden; text-overflow: ellipsis; white-space: nowrap;'>{item['name']}</div>
                <div style='font-size: 0.7rem; color: {sec_text_color}; margin-top: 0.1rem;'>{item['condition']} &rarr; <b>{dec}</b>{value_info}</div>
            </div>
            """, unsafe_allow_html=True)
        with col_side_del:
            # Render a tiny, compact delete button
            if st.button("🗑️", key=f"del_{item['id']}"):
                delete_inventory_item(item['id'])
                st.sidebar.success(t["success_delete"])
                st.rerun()

# ----------------- MAIN PAGE HEADER -----------------
st.markdown(f"""
<div class='hero-banner'>
    <div class='hero-title'>{t['title']}</div>
    <div class='hero-subtitle'>{t['subtitle']}</div>
</div>
""", unsafe_allow_html=True)

# ----------------- GRID LAYOUT (SINGLE COLUMN) -----------------
with st.container(border=True):
    st.markdown(f"<div class='section-header' style='border-bottom: none; margin-bottom: 0.5rem; padding-bottom: 0;'>⚙️ {t['input_header']}</div>", unsafe_allow_html=True)
    
    col_left, col_right = st.columns([3, 2])
    with col_left:
        item_description = st.text_area(
            t["desc_label"],
            placeholder=t["desc_placeholder"],
            height=140
        )
    with col_right:
        uploaded_image = st.file_uploader(
            t["img_label"],
            type=["jpg", "png", "jpeg"]
        )
        selected_intent_str = st.selectbox(
            t["intent_label"],
            t["intent_options"]
        )
        
    intent_mapping = {
        0: "Tidak tahu",
        1: "Ingin menjual",
        2: "Ingin donasikan",
        3: "Ingin perbaiki",
        4: "Ingin daur ulang"
    }
    selected_index = t["intent_options"].index(selected_intent_str)
    user_intent = intent_mapping.get(selected_index, "Tidak tahu")
    
    analyze_btn = st.button(t["btn_analyze"], type="primary", use_container_width=True)

# ----------------- PROCESS ANALYSIS -----------------
if analyze_btn:
    if not item_description.strip():
        st.warning("Please describe your item first." if lang == "English" else "Silakan deskripsikan barang Anda terlebih dahulu.")
    else:
        with st.spinner(t["loading_msg"]):
            image_path = None
            if uploaded_image:
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, uploaded_image.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_image.getbuffer())
                image_path = temp_path
            
            results = asyncio.run(run_decluttering_flow(item_description, image_path, user_intent))
            
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            
            st.session_state["pipeline_results"] = results
            
            details = results.get("item_details", {})
            decision = results.get("decision", {})
            reco = results.get("recommendations", {})
            val = results.get("valuation", {})
            
            name = details.get("nama_barang", "Barang Tak Dikenal")
            category = "General"
            cond = details.get("kondisi", "Bagus")
            dec = decision.get("keputusan_terbaik", "Keep")
            price = val.get("harga_pasaran_rp", 0)
            rec_text = reco.get("rekomendasi", "")
            
            save_success = save_item(name, category, cond, dec, price, rec_text)
            if save_success:
                st.rerun()

# ----------------- PRESENT RESULTS -----------------
if "pipeline_results" in st.session_state:
    results = st.session_state["pipeline_results"]
    
    details = results.get("item_details", {})
    repair_info = results.get("repair_info", {})
    valuation = results.get("valuation", {})
    sustainability = results.get("sustainability", {})
    decision = results.get("decision", {})
    recommendations = results.get("recommendations", {})
    action_taken = results.get("action_taken", {})
    
    st.markdown(f"<div class='section-header' style='margin-top: 2rem;'>📊 {t['results_header']}</div>", unsafe_allow_html=True)
    
    # 1. Brief Item Overview & Decision Card combined in a full width Notion-style container
    with st.container(border=True):
        st.markdown(f"""
        <div style="font-size: 2.2rem; font-weight: 800; font-family: 'Plus Jakarta Sans', sans-serif; letter-spacing: -0.5px; margin-bottom: 0.2rem; color: {text_color};">
            📦 {details.get('nama_barang', 'Item')}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="font-size: 0.95rem; opacity: 0.8; margin-bottom: 1rem; color: {text_color}; font-family: 'Inter', sans-serif;">
            <b>{t['brand']}:</b> {details.get('merek', 'Tidak Diketahui')} | 
            <b>{t['age']}:</b> {details.get('umur_perkiraan_tahun', 0)} {t['years']} | 
            <b>{t['condition']}:</b> {details.get('kondisi', 'Tidak Diketahui')}
        </div>
        """, unsafe_allow_html=True)
        
        st.markdown(f"""
        <div style="margin-top: 1rem; padding-top: 1rem; border-top: 1px solid {border_color};">
            <div style="font-size: 0.8rem; text-transform: uppercase; letter-spacing: 1px; opacity: 0.6; font-weight: 600; margin-bottom: 0.4rem; color: {text_color};">{t['best_decision']}</div>
            <div class="best-decision-badge">{decision.get('keputusan_terbaik', 'Keep')}</div>
            <div style="font-size: 1rem; line-height: 1.5; color: {text_color}; font-family: 'Inter', sans-serif; opacity: 0.95;">
                {decision.get('alasan', '')}
            </div>
        </div>
        """, unsafe_allow_html=True)

    # 2. Option Scores & Actionable recommendations side-by-side inside cards (Notion column grid look)
    col_scores, col_reco = st.columns([1, 1])
    
    with col_scores:
        with st.container(border=True):
            st.markdown(f"<div style='font-size: 1.15rem; font-weight: 700; margin-bottom: 1rem; font-family: \"Plus Jakarta Sans\"; color: {text_color};'>📈 {t['scores_header']}</div>", unsafe_allow_html=True)
            scores = decision.get("skor_tiap_opsi", {})
            default_options = ["Keep", "Repair", "Sell", "Donate", "Recycle"]
            for opt in default_options:
                score_val = scores.get(opt, 0)
                draw_custom_progress(opt, min(max(int(score_val), 0), 100))
                
    with col_reco:
        with st.container(border=True):
            st.markdown(f"<div style='font-size: 1.15rem; font-weight: 700; margin-bottom: 1rem; font-family: \"Plus Jakarta Sans\"; color: {text_color};'>💬 {t['reco_header']}</div>", unsafe_allow_html=True)
            st.markdown(f"<div style='font-size: 0.95rem; line-height: 1.5; color: {text_color}; font-family: \"Inter\", sans-serif; margin-bottom: 1rem;'>{recommendations.get('rekomendasi', '')}</div>", unsafe_allow_html=True)
            
            st.markdown(f"<div style='font-size: 0.9rem; font-weight: 600; margin-bottom: 0.5rem; color: {text_color};'>📋 {t['steps_header']}</div>", unsafe_allow_html=True)
            steps = recommendations.get("langkah_selanjutnya", [])
            for step in steps:
                st.markdown(f"<div style='font-size: 0.9rem; margin-bottom: 0.3rem; font-family: \"Inter\", sans-serif; color: {text_color};'>• {step}</div>", unsafe_allow_html=True)

    # 3. Locations and Search Guide Card in a single full-width container at bottom
    with st.container(border=True):
        section_title = action_taken.get("judul_section")
        if not section_title:
            section_title = t['locations_header']
            
        st.markdown(f"<div style='font-size: 1.2rem; font-weight: 700; margin-bottom: 1rem; font-family: \"Plus Jakarta Sans\"; color: {text_color};'>📍 {section_title}</div>", unsafe_allow_html=True)
        
        rekomendasi_lokasi = action_taken.get("rekomendasi_lokasi", [])
        locations = action_taken.get("lokasi", [])
        urls = action_taken.get("tautan", [])
        
        if rekomendasi_lokasi:
            for item in rekomendasi_lokasi:
                nama = item.get("nama", "Tidak Diketahui")
                alamat = item.get("alamat", "")
                url = item.get("tautan", "#")
                alamat_html = f"<div style='font-size:0.85rem; opacity:0.8; margin-top:0.2rem; margin-bottom:0.4rem; color: {text_color};'>📍 {alamat}</div>" if alamat else ""
                st.markdown(f"""
                <div class='location-card'>
                    <div class='location-title'>🏢 {nama}</div>
                    {alamat_html}
                    <a class='location-link' href='{url}' target='_blank'>{t['visit_ref']}</a>
                </div>
                """, unsafe_allow_html=True)
        elif locations:
            for loc, url in zip(locations, urls):
                st.markdown(f"""
                <div class='location-card'>
                    <div class='location-title'>📍 {loc}</div>
                    <a class='location-link' href='{url}' target='_blank'>{t['visit_ref']}</a>
                </div>
                """, unsafe_allow_html=True)
        else:
            st.info(t["no_locations"])
            
        panduan = action_taken.get("panduan_pencarian")
        if panduan:
            st.markdown(f"""
            <div style='background-color: {card_bg}; border-radius: 8px; padding: 0.8rem; margin-top: 1rem; border-left: 4px solid #FF6584; border-right: 1px solid {border_color}; border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color};'>
                <div style='font-weight: 600; font-size: 0.9rem; margin-bottom: 0.2rem; color: {text_color}; font-family: \"Plus Jakarta Sans\";'>ℹ️ Panduan Pencarian / Search Guide</div>
                <div style='font-size: 0.85rem; opacity: 0.85; color: {text_color}; font-family: \"Inter\";'>{panduan}</div>
            </div>
            """, unsafe_allow_html=True)
else:
    st.info(t["prompt_info"])
