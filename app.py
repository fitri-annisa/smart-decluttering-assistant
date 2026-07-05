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
        "subtitle": "Analisis cerdas barang tak terpakai Anda dengan tim multi-agent AI.",
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
        "subtitle": "Intelligent analysis of your unused items with a multi-agent AI team.",
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
# 1. Language Selector
lang = st.sidebar.selectbox("Language / Bahasa", ["Bahasa Indonesia", "English"])
t = TRANSLATIONS[lang]

# 2. Dark/Light Theme Toggle
light_theme = st.sidebar.toggle("Light Mode ☀️", value=False)

# Theme Style Calculations
if light_theme:
    bg_color = "#F8F9FF"
    card_bg = "#FFFFFF"
    text_color = "#1A1A2E"
    border_color = "#E0E0E0"
    sec_text_color = "#666666"
    sub_title_gradient = "linear-gradient(135deg, #6C63FF, #FF6584)"
    sidebar_bg = "#FFFFFF"
    sidebar_text = "#1A1A2E"
    code_bg = "#EAEAEA"
    code_text = "#FF6584"
else:
    bg_color = "#1A1A2E"
    card_bg = "#16213E"
    text_color = "#FFFFFF"
    border_color = "#2E3B5E"
    sec_text_color = "#888888"
    sub_title_gradient = "linear-gradient(135deg, #6C63FF, #FF6584)"
    sidebar_bg = "#16213E"
    sidebar_text = "#FFFFFF"
    code_bg = "#2E3B5E"
    code_text = "#FF6584"

# Injected CSS Typography and Aesthetics
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Playfair+Display:ital,wght@0,400..900;1,400..900&family=Roboto:ital,wght@0,100..900;1,100..900&display=swap');
    
    /* Global Background and Fonts */
    .stApp {{
        background-color: {bg_color} !important;
        color: {text_color} !important;
        font-family: 'Roboto', sans-serif !important;
    }}
    
    h1, h2, h3, h4, h5, h6, .main-title, .section-header {{
        font-family: 'Playfair Display', serif !important;
        color: {text_color} !important;
    }}
    
    .main-title {{
        font-size: 2.8rem;
        font-weight: 800;
        background: {sub_title_gradient};
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        margin-bottom: 0.2rem;
    }}
    
    .sub-title {{
        font-size: 1.1rem;
        color: {sec_text_color};
        margin-bottom: 2rem;
    }}
    
    .card {{
        background-color: {card_bg};
        border-radius: 12px;
        padding: 1.5rem;
        border: 1px solid {border_color};
        margin-bottom: 1.5rem;
        color: {text_color};
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
    }}
    
    .highlight-card {{
        background-color: {card_bg};
        border: 2px solid #6C63FF;
        border-radius: 12px;
        padding: 1.5rem;
        margin-bottom: 1.5rem;
        color: {text_color};
    }}
    
    .best-decision {{
        font-size: 2.2rem;
        font-weight: 700;
        color: #FF6584;
        margin-top: 0.5rem;
        margin-bottom: 0.5rem;
        font-family: 'Playfair Display', serif !important;
    }}
    
    .location-card {{
        background-color: {card_bg};
        border-radius: 8px;
        padding: 1rem;
        margin-bottom: 0.8rem;
        border-left: 4px solid #6C63FF;
        border-right: 1px solid {border_color};
        border-top: 1px solid {border_color};
        border-bottom: 1px solid {border_color};
    }}
    
    .location-title {{
        font-weight: 600;
        color: {text_color};
        font-size: 1rem;
    }}
    
    .location-link {{
        font-size: 0.9rem;
        color: #FF6584;
        text-decoration: none;
    }}
    
    .location-link:hover {{
        text-decoration: underline;
    }}
    
    .section-header {{
        font-size: 1.4rem;
        font-weight: 700;
        color: {text_color};
        margin-bottom: 1rem;
        border-bottom: 1px solid {border_color};
        padding-bottom: 0.3rem;
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
    }}

    /* Selectbox dropdown container and values overrides */
    [data-testid="stSelectbox"] [data-baseweb="select"] > div,
    [data-testid="stSelectbox"] [data-baseweb="select"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    [data-testid="stSelectbox"] [data-baseweb="select"] * {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    div[data-baseweb="popover"] ul {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
    }}
    div[data-baseweb="popover"] li {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
    }}
    div[data-baseweb="popover"] li:hover {{
        background-color: #6C63FF !important;
        color: #FFFFFF !important;
    }}

    /* Text Area Input overrides */
    [data-testid="stTextArea"] textarea {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px solid {border_color} !important;
    }}
    textarea::placeholder {{
        color: {sec_text_color} !important;
        opacity: 0.7 !important;
    }}

    /* Code tag formatting (for inline badges) */
    code {{
        background-color: {code_bg} !important;
        color: {code_text} !important;
        border: 1px solid {border_color} !important;
        font-weight: 600 !important;
    }}

    /* Spinner, Alerts, & Notification Contrast overrides */
    div[data-testid="stNotification"],
    div[class*="stAlert"],
    div[class*="stNotificationContent"] {{
        background-color: {card_bg} !important;
        border: 1px solid {border_color} !important;
        color: {text_color} !important;
    }}
    div[data-testid="stNotification"] *,
    div[class*="stAlert"] *,
    div[class*="stNotificationContent"] * {{
        color: {text_color} !important;
    }}

    /* File Uploader overrides */
    [data-testid="stFileUploader"] {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
        border: 1px dashed {border_color} !important;
    }}
    [data-testid="stFileUploader"] * {{
        background-color: transparent !important;
        color: {text_color} !important;
    }}
    [data-testid="stFileUploader"] div[data-testid="stFileUploaderFileList"] div,
    [data-testid="stFileUploader"] div[data-testid="stFileUploaderFileList"] span,
    [data-testid="stFileUploader"] div[data-testid="stFileUploaderFileList"] button {{
        background-color: {card_bg} !important;
        color: {text_color} !important;
    }}

    /* Primary Action Buttons styling with premium micro-interaction */
    .stButton > button[kind="primary"] {{
        background: linear-gradient(135deg, #6C63FF, #FF6584) !important;
        border: none !important;
        color: #FFFFFF !important;
        font-weight: 600 !important;
        transition: transform 0.1s ease, box-shadow 0.1s ease !important;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1) !important;
    }}
    .stButton > button[kind="primary"]:hover {{
        transform: translateY(-1px) !important;
        box-shadow: 0 6px 12px rgba(108, 99, 255, 0.3) !important;
    }}
    .stButton > button[kind="primary"]:active {{
        transform: translateY(0px) !important;
    }}

    /* Compact Delete Button styling inside sidebar */
    [data-testid="stSidebar"] button {{
        padding: 0.15rem 0.4rem !important;
        font-size: 0.8rem !important;
        line-height: 1.2 !important;
        border-radius: 4px !important;
        border: 1px solid {border_color} !important;
        background-color: {card_bg} !important;
        color: {sidebar_text} !important;
    }}
    [data-testid="stSidebar"] button:hover {{
        border-color: #FF6584 !important;
        color: #FF6584 !important;
    }}
</style>
""", unsafe_allow_html=True)

# Helper function to draw custom styled progress bars
def draw_custom_progress(label, value):
    bar_bg = "#2E3B5E" if not light_theme else "#E0E0E0"
    st.markdown(f"""
    <div style="margin-bottom: 0.8rem;">
        <div style="display: flex; justify-content: space-between; font-size: 0.9rem; font-weight: 600; margin-bottom: 0.2rem;">
            <span>{label}</span>
            <span>{value}/100</span>
        </div>
        <div style="background-color: {bar_bg}; border-radius: 6px; height: 10px; width: 100%; overflow: hidden;">
            <div style="background-color: #6C63FF; height: 100%; width: {value}%; border-radius: 6px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ----------------- SIDEBAR INVENTORY LIST -----------------
st.sidebar.markdown(f"### 📦 {t['history_title']}")
inventory = get_inventory()

if not inventory:
    st.sidebar.info(t["empty_history"])
else:
    st.sidebar.caption(t["total_items"].replace("{count}", str(len(inventory))))
    st.sidebar.markdown("<hr style='margin: 0.3rem 0;' />", unsafe_allow_html=True)
    
    # Render compact sidebar cards
    for item in inventory:
        col_side_text, col_side_del = st.sidebar.columns([4, 1])
        with col_side_text:
            st.markdown(
                f"<div style='font-size: 0.9rem; color: {sidebar_text}; line-height: 1.3;'>"
                f"<strong>{item['name']}</strong> | <span style='color: #FF6584; font-weight: 600;'>{item['condition']}</span> &rarr; <strong>{item['decision']}</strong>"
                f"</div>",
                unsafe_allow_html=True
            )
            if item['value_rp'] > 0:
                st.markdown(
                    f"<div style='font-size: 0.75rem; color: {sec_text_color}; margin-top: 0.1rem;'>"
                    f"Value: Rp {item['value_rp']:,}"
                    f"</div>",
                    unsafe_allow_html=True
                )
        with col_side_del:
            if st.button("🗑️", key=f"del_{item['id']}"):
                delete_inventory_item(item['id'])
                st.sidebar.success(t["success_delete"])
                st.rerun()
        st.sidebar.markdown("<hr style='margin: 0.2rem 0;' />", unsafe_allow_html=True)

# ----------------- MAIN PAGE HEADER -----------------
st.markdown(f"<div class='main-title'>{t['title']}</div>", unsafe_allow_html=True)
st.markdown(f"<div class='sub-title'>{t['subtitle']}</div>", unsafe_allow_html=True)

# ----------------- GRID LAYOUT -----------------
col_input, col_result = st.columns([2, 3])

with col_input:
    st.markdown(f"<div class='section-header'>{t['input_header']}</div>", unsafe_allow_html=True)
    
    # Description input box
    item_description = st.text_area(
        t["desc_label"],
        placeholder=t["desc_placeholder"],
        height=150
    )
    
    # Image uploader
    uploaded_image = st.file_uploader(
        t["img_label"],
        type=["jpg", "png", "jpeg"]
    )
    
    # User Intent selector
    selected_intent_str = st.selectbox(
        t["intent_label"],
        t["intent_options"]
    )
    # Map selection back to normalized Indonesian keys for pipeline logic
    intent_mapping = {
        0: "Tidak tahu",
        1: "Ingin menjual",
        2: "Ingin donasikan",
        3: "Ingin perbaiki",
        4: "Ingin daur ulang"
    }
    selected_index = t["intent_options"].index(selected_intent_str)
    user_intent = intent_mapping.get(selected_index, "Tidak tahu")
    
    # Action button
    analyze_btn = st.button(t["btn_analyze"], type="primary", use_container_width=True)

# ----------------- PROCESS ANALYSIS -----------------
if analyze_btn:
    if not item_description.strip():
        st.warning("Please describe your item first." if lang == "English" else "Silakan deskripsikan barang Anda terlebih dahulu.")
    else:
        with st.spinner(t["loading_msg"]):
            image_path = None
            # Store uploaded image temporarily if present
            if uploaded_image:
                temp_dir = tempfile.gettempdir()
                temp_path = os.path.join(temp_dir, uploaded_image.name)
                with open(temp_path, "wb") as f:
                    f.write(uploaded_image.getbuffer())
                image_path = temp_path
            
            # Execute orchestrator flow
            results = asyncio.run(run_decluttering_flow(item_description, image_path, user_intent))
            
            # Remove temp image file
            if image_path and os.path.exists(image_path):
                os.remove(image_path)
            
            # Store results in Session State
            st.session_state["pipeline_results"] = results
            
            # Extract attributes to save to SQLite database
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
            
            # Database insertion
            save_success = save_item(name, category, cond, dec, price, rec_text)
            if save_success:
                st.rerun()

# ----------------- PRESENT RESULTS -----------------
with col_result:
    st.markdown(f"<div class='section-header'>{t['results_header']}</div>", unsafe_allow_html=True)
    
    if "pipeline_results" not in st.session_state:
        st.info(t["prompt_info"])
    else:
        results = st.session_state["pipeline_results"]
        
        details = results.get("item_details", {})
        repair_info = results.get("repair_info", {})
        valuation = results.get("valuation", {})
        sustainability = results.get("sustainability", {})
        decision = results.get("decision", {})
        recommendations = results.get("recommendations", {})
        action_taken = results.get("action_taken", {})
        
        # 1. Brief Item Overview
        st.markdown(f"""
        <div class='card'>
            <h3 style="margin-top:0;">📦 {details.get('nama_barang', 'Item')}</h3>
            <p style="margin-bottom:0;"><b>{t['brand']}:</b> {details.get('merek', 'Tidak Diketahui')} | <b>{t['age']}:</b> {details.get('umur_perkiraan_tahun', 0)} {t['years']}</p>
            <p style="margin-bottom:0; margin-top:0.4rem;"><b>{t['condition']}:</b> {details.get('kondisi', 'Tidak Diketahui')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 2. Decision Card
        st.markdown(f"""
        <div class='highlight-card'>
            <div style="font-size: 0.9rem; text-transform: uppercase; letter-spacing: 1px; color: #888888;">{t['best_decision']}</div>
            <div class='best-decision'>{decision.get('keputusan_terbaik', 'Keep')}</div>
            <p style="margin: 0; color: {text_color}; opacity: 0.9;">{decision.get('alasan', '')}</p>
        </div>
        """, unsafe_allow_html=True)
        
        # 3. Option Scores (Custom Progress Bars)
        st.markdown(f"<h3>📈 {t['scores_header']}</h3>", unsafe_allow_html=True)
        scores = decision.get("skor_tiap_opsi", {})
        default_options = ["Keep", "Repair", "Sell", "Donate", "Recycle"]
        for opt in default_options:
            score_val = scores.get(opt, 0)
            draw_custom_progress(opt, min(max(int(score_val), 0), 100))
        
        # 4. Actionable recommendations
        st.markdown(f"<h3>💬 {t['reco_header']}</h3>", unsafe_allow_html=True)
        st.write(recommendations.get("rekomendasi", ""))
        
        st.markdown(f"<h4>{t['steps_header']}</h4>", unsafe_allow_html=True)
        steps = recommendations.get("langkah_selanjutnya", [])
        for step in steps:
            st.markdown(f"- {step}")
            
        # 5. Local maps/URLs resources
        section_title = action_taken.get("judul_section")
        if not section_title:
            section_title = t['locations_header']
        st.markdown(f"<h3>📍 {section_title}</h3>", unsafe_allow_html=True)
        
        rekomendasi_lokasi = action_taken.get("rekomendasi_lokasi", [])
        locations = action_taken.get("lokasi", [])
        urls = action_taken.get("tautan", [])
        
        if rekomendasi_lokasi:
            for item in rekomendasi_lokasi:
                nama = item.get("nama", "Tidak Diketahui")
                alamat = item.get("alamat", "")
                url = item.get("tautan", "#")
                alamat_html = f"<div style='font-size:0.9rem; opacity:0.8; margin-top:0.3rem; margin-bottom:0.5rem;'>📍 {alamat}</div>" if alamat else ""
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
            <div style='background-color: {card_bg}; border-radius: 8px; padding: 1rem; margin-top: 0.8rem; border-left: 4px solid #FF6584; border-right: 1px solid {border_color}; border-top: 1px solid {border_color}; border-bottom: 1px solid {border_color};'>
                <div style='font-weight: 600; font-size: 0.95rem; margin-bottom: 0.3rem; color: {text_color};'>ℹ️ Panduan Pencarian / Search Guide</div>
                <div style='font-size: 0.9rem; opacity: 0.9; color: {text_color};'>{panduan}</div>
            </div>
            """, unsafe_allow_html=True)
