# 🧹 Smart Decluttering Assistant

[English](#english) | [Bahasa Indonesia](#bahasa-indonesia)

---

## English

Smart Decluttering Assistant is an intelligent multi-agent AI system designed to help users declutter unused items. Powered by the **Google Agent Development Kit (ADK)** and `gemini-2.5-flash`, the system analyzes item descriptions and images, performs marketplace price comparisons and repairability evaluations, and recommends the best course of action (Keep, Repair, Sell, Donate, or Recycle).

### 🚀 Features

*   **7 Specialized AI Agents**:
    1.  **Understanding Agent**: Classifies items and assesses physical condition using text & images.
    2.  **Repair Agent**: Estimates if the item can be fixed, spare parts availability, and repair costs.
    3.  **Value Agent**: Utilizes the Google Search tool to check current second-hand prices on Tokopedia, OLX, or Shopee.
    4.  **Sustainability Agent**: Estimates CO2 footprint reduction and eco-disposal options.
    5.  **Decision Agent**: Computes a final decision based on weighted scoring: **Repair (40%)**, **Value (35%)**, and **Sustainability (25%)**.
    6.  **Recommendation Agent**: Generates concise, actionable next steps in Bahasa Indonesia or English.
    7.  **Action Agent**: Uses Google Search to find physical repair shops, recycling hubs (like Waste4Change), or donation points in Indonesia.
*   **Sequential & Parallel Orchestration**: Leverages ADK's parallel flow (`asyncio.gather`) to run Value, Repair, and Sustainability analyses concurrently.
*   **Streamlit Dashboard**: Offers localization toggles (Indonesian / English), Light/Dark themes, Custom typography (Playfair Display & Roboto), custom progress bars, and localized spinners.
*   **SQLite Database**: Automatically logs all analyzed items to `declutter_inventory.db` for historical tracking and deletion in the sidebar.

### 📁 Project Structure

```text
smart-decluttering-assistant/
│
├── agents/
│   ├── understanding_agent.py    # Item identification (Multimodal)
│   ├── repair_agent.py           # Repairability assessment
│   ├── value_agent.py            # Market price search (Google Search)
│   ├── sustainability_agent.py   # Eco-impact analysis
│   ├── decision_agent.py         # Weighted decision maker
│   ├── recommendation_agent.py   # User recommendation compiler
│   └── action_agent.py           # Drop-point locator (Google Search)
│
├── app.py                        # Streamlit frontend dashboard
├── orchestrator.py               # Sequential & Parallel ADK workflow
├── inventory_db.py               # SQLite CRUD operations
└── requirements.txt              # Project dependencies
```

### ⚙️ Getting Started

#### 1. Install Dependencies
Clone or copy the directory, then install the package requirements:
```bash
pip install -r requirements.txt
```

#### 2. Configure Gemini API Key
Export your Gemini API Key in your terminal:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

#### 3. Run the Dashboard
Launch the Streamlit server:
```bash
streamlit run app.py
```

---

## Bahasa Indonesia

Smart Decluttering Assistant adalah sistem multi-agent AI cerdas yang dirancang untuk membantu pengguna menentukan keputusan terbaik terhadap barang-barang tak terpakai. Didukung oleh **Google Agent Development Kit (ADK)** dan model `gemini-2.5-flash`, sistem ini menganalisis deskripsi teks serta foto barang, menelusuri harga pasar, menilai kelayakan perbaikan, serta memberikan rekomendasi terbaik (Keep, Repair, Sell, Donate, atau Recycle).

### 🚀 Fitur Utama

*   **7 Agen AI Spesialis**:
    1.  **Understanding Agent**: Mengidentifikasi barang dan menilai kondisi fisiknya menggunakan teks & gambar (Multimodal).
    2.  **Repair Agent**: Menilai kelayakan perbaikan barang, ketersediaan sparepart, serta estimasi biaya perbaikan.
    3.  **Value Agent**: Menggunakan alat Google Search untuk mencari harga bekas terkini di Tokopedia, OLX, atau Shopee.
    4.  **Sustainability Agent**: Memperkirakan jejak karbon (CO2) yang dihasilkan dan menyarankan opsi pembuangan ramah lingkungan.
    5.  **Decision Agent**: Menentukan keputusan final menggunakan pembobotan: **Repair (40%)**, **Value (35%)**, dan **Sustainability (25%)**.
    6.  **Recommendation Agent**: Menyusun panduan langkah konkret selanjutnya dalam Bahasa Indonesia atau English.
    7.  **Action Agent**: Menggunakan Google Search untuk mencari titik jemput daur ulang (seperti Waste4Change), yayasan donasi, atau bengkel servis terdekat di Indonesia.
*   **Orkestrasi Paralel & Sekuensial**: Menggunakan workflow ADK paralel (`asyncio.gather`) untuk mempercepat analisis nilai jual, perbaikan, dan keberlanjutan secara bersamaan.
*   **Dashboard Streamlit**: Menyediakan toggle bahasa (Bahasa Indonesia / English), tema Terang/Gelap, tipografi khusus (Playfair Display & Roboto), progress bar kustom, serta loading state yang responsif.
*   **Database SQLite**: Menyimpan riwayat barang yang dianalisis secara otomatis ke dalam `declutter_inventory.db` untuk dimonitor dan dihapus langsung melalui sidebar.

### 📁 Struktur Proyek

```text
smart-decluttering-assistant/
│
├── agents/
│   ├── understanding_agent.py    # Identifikasi Barang (Multimodal)
│   ├── repair_agent.py           # Analisis Perbaikan
│   ├── value_agent.py            # Pencarian Harga Pasar (Google Search)
│   ├── sustainability_agent.py   # Analisis Dampak Lingkungan
│   ├── decision_agent.py         # Penentu Keputusan (Weighted)
│   ├── recommendation_agent.py   # Penyusun Rekomendasi
│   └── action_agent.py           # Pencarian Lokasi Fisik (Google Search)
│
├── app.py                        # Dashboard Streamlit UI
├── orchestrator.py               # Orkestrasi Aliran Kerja ADK (Paralel)
├── inventory_db.py               # Operasi Database SQLite (CRUD)
└── requirements.txt              # Daftar Dependensi Proyek
```

### ⚙️ Cara Menjalankan Aplikasi

#### 1. Instal Dependensi
Masuk ke direktori proyek dan pasang dependensi yang diperlukan:
```bash
pip install -r requirements.txt
```

#### 2. Konfigurasi API Key Gemini
Ekspor API Key Gemini Anda di terminal:
```bash
export GEMINI_API_KEY="your-api-key-here"
```

#### 3. Jalankan Aplikasi
Jalankan server Streamlit:
```bash
streamlit run app.py
```
