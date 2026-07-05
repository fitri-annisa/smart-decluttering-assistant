import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.tools import google_search
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class LocationDetail(BaseModel):
    nama: str = Field(description="Nama tempat/platform/program spesifik di Indonesia (misal: Tokopedia - iPhone 13 Second, Mitra Care Apple, Waste4Change)")
    alamat: str = Field(description="Alamat fisik lengkap, keterangan platform, WA/kontak, estimasi harga, atau langkah daftar")
    tautan: str = Field(description="Tautan URL valid spesifik (bukan homepage generik, misal link produk Tokopedia/OLX, Google Maps lokasi spesifik, form pendaftaran)")

class ActionOutput(BaseModel):
    judul_section: str = Field(description="Judul section sesuai dengan user_intent (Platform Jual & Estimasi Harga, Tempat Donasi, Tempat Servis Rekomendasi, Program Daur Ulang & Drop Point, atau Rekomendasi Tindakan)")
    rekomendasi_lokasi: list[LocationDetail] = Field(description="Daftar rekomendasi lokasi spesifik di Indonesia (minimal 3 lokasi)")
    panduan_pencarian: str = Field(description="Panduan teks cara mencari mandiri jika hasil spesifik tidak ditemukan di internet")

# Helper search agent for taking action (has tools, no output schema)
action_search_agent = Agent(
    name="action_search_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "Anda adalah Agen Riset Lokasi. Tugas Anda adalah mencari lokasi fisik atau daring "
        "spesifik, nyata, dan aktif di Indonesia beserta alamat lengkap, kontak/WA jika ada, estimasi harga/langkah daftar, dan tautan (URL) SPESIFIK untuk memproses keputusan decluttering barang:\n"
        "- Jika user_intent adalah 'Ingin menjual': Cari link listing produk bekas sejenis di Tokopedia/OLX (misal Tokopedia search query path seperti https://www.tokopedia.com/search?q=iphone+13+second), estimasi harga pasaran bekas sejenis, serta tips jual.\n"
        "- Jika user_intent adalah 'Ingin donasikan': Cari nama yayasan/komunitas di Indonesia (misal: Yayasan Sayap Ibu, Panti Asuhan), alamat fisik lengkap, nomor WA/kontak donasi jika ada, dan tautan spesifik.\n"
        "- Jika user_intent adalah 'Ingin perbaiki': Cari nama toko servis/service center resmi terdekat, alamat fisik lengkap, rating toko jika ada, serta link Google Maps spesifik menuju lokasi tersebut.\n"
        "- Jika user_intent adalah 'Ingin daur ulang': Cari nama program daur ulang resmi (misal: Waste4Change, program Trade In Samsung/Apple) beserta drop point e-waste/bank sampah, cara daftar/proses daur ulang, dan tautan pendaftaran/lokasi valid.\n"
        "- Jika user_intent adalah 'Tidak tahu': Cari ringkasan singkat dari keempat opsi di atas secara umum.\n\n"
        "PENTING: Jangan pernah memberikan tautan homepage generik (seperti tokopedia.com, olx.co.id, google.com). URL harus memiliki path spesifik (misal: link produk search Tokopedia/OLX, link lokasi Google Maps spesifik, link form pendaftaran). "
        "Jika hasil spesifik tidak ditemukan, tuliskan panduan teks (langkah demi langkah) tentang cara mencarinya secara manual."
    ),
    tools=[google_search]
)

# Define the Google ADK Agent for formatting action recommendations (no tools, has output schema)
action_agent = Agent(
    name="action_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "Anda adalah Agen Tindakan (Action Agent). Tugas Anda adalah memformat hasil riset lokasi "
        "menjadi format JSON terstruktur sesuai skema output yang ditentukan.\n\n"
        "Petakan data hasil riset ke dalam bidang berikut:\n"
        "- judul_section: Gunakan judul sesuai intent pengguna:\n"
        "  * 'Ingin menjual' -> 'Platform Jual & Estimasi Harga'\n"
        "  * 'Ingin donasikan' -> 'Tempat Donasi'\n"
        "  * 'Ingin perbaiki' -> 'Tempat Servis Rekomendasi'\n"
        "  * 'Ingin daur ulang' -> 'Program Daur Ulang & Drop Point'\n"
        "  * 'Tidak tahu' -> 'Rekomendasi Tindakan'\n"
        "- rekomendasi_lokasi: List dari objek LocationDetail dengan nama, alamat (berisi alamat lengkap, kontak/WA jika ada, estimasi harga/langkah daftar), dan tautan (URL spesifik, bukan homepage generik).\n"
        "- panduan_pencarian: Panduan teks cara mencari mandiri jika hasil spesifik tidak ditemukan."
    ),
    output_schema=ActionOutput
)

async def execute_post_decision_actions(item_name: str, final_decision: str, user_intent: str = "Tidak tahu") -> dict:
    """
    Mencari lokasi/resource terdekat untuk memproses keputusan decluttering.
    
    Args:
        item_name (str): Nama barang yang dievaluasi.
        final_decision (str): Keputusan akhir (Keep, Repair, Sell, Donate, Recycle).
        user_intent (str): Intent khusus pengguna.
        
    Returns:
        dict: Daftar lokasi, judul section, panduan pencarian, dan tautan terkait.
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Step 1: Run search agent to search for locations
        runner_search = InMemoryRunner(agent=action_search_agent)
        session_search = await runner_search.session_service.get_session(
            app_name=runner_search.app_name, user_id="user_default", session_id="session_action_search"
        )
        if not session_search:
            session_search = await runner_search.session_service.create_session(
                app_name=runner_search.app_name, user_id="user_default", session_id="session_action_search"
            )

        prompt_search = (
            f"Cari lokasi fisik/daring dan tautan web di Indonesia menggunakan google_search untuk keputusan berikut:\n"
            f"Nama Barang: {item_name}\n"
            f"Keputusan: {final_decision}\n"
        )
        if user_intent and user_intent != "Tidak tahu":
            prompt_search += f"Intent Pengguna: {user_intent}\n\n"
            if user_intent == "Ingin menjual":
                prompt_search += (
                    "Tugas Khusus Pencarian:\n"
                    "- Cari platform jual beli bekas terbaik di Indonesia (misal Tokopedia, OLX, Facebook Marketplace).\n"
                    "- Temukan link listing produk bekas sejenis yang spesifik (bukan homepage generik tokopedia.com, "
                    "gunakan format pencarian seperti https://www.tokopedia.com/search?q=keyword atau url listing produk spesifik).\n"
                    "- Cari tips singkat untuk menjual barang sejenis agar cepat laku di Indonesia.\n"
                    "- Sertakan nama platform, alamat/keterangan platform, dan URL tautan spesifik."
                )
            elif user_intent == "Ingin donasikan":
                prompt_search += (
                    "Tugas Khusus Pencarian:\n"
                    "- Cari nama, alamat lengkap, kontak/link WA yayasan, panti asuhan, atau komunitas sosial yang nyata di Indonesia yang menerima donasi barang sejenis.\n"
                    "- Sertakan detail nama, alamat, nomor kontak/WA jika ada, dan tautan."
                )
            elif user_intent == "Ingin perbaiki":
                prompt_search += (
                    "Tugas Khusus Pencarian:\n"
                    "- Cari bengkel reparasi atau tempat servis resmi/terpercaya di Indonesia untuk barang sejenis, beserta alamat lengkap dan Google Maps link spesifik ke tempat itu.\n"
                    "- Cari perkiraan range biaya servis untuk barang sejenis di Indonesia.\n"
                    "- Sertakan nama tempat servis, alamat lengkap, dan tautan Google Maps spesifik."
                )
            elif user_intent == "Ingin daur ulang":
                prompt_search += (
                    "Tugas Khusus Pencarian:\n"
                    "- Cari program daur ulang resmi (misal program daur ulang brand seperti Samsung, Apple Trade In, atau Waste4Change) beserta alamat drop point e-waste atau bank sampah terdekat di Indonesia.\n"
                    "- Cari cara daftar/proses daur ulang barang tersebut di Indonesia.\n"
                    "- Sertakan nama tempat daur ulang/drop point, langkah pendaftaran, dan tautan pendaftaran/lokasi valid."
                )
        msg_search = types.Content(role="user", parts=[types.Part.from_text(text=prompt_search)])
        
        collected_search = []
        async for event in runner_search.run_async(user_id="user_default", session_id=session_search.id, new_message=msg_search):
            if event.error_message:
                raise RuntimeError(f"Search Agent error: {event.error_message}")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        collected_search.append(part.text)

        search_results = "".join(collected_search).strip()
        logger.info(f"Raw search results from action_search_agent: {search_results}")

        # Step 2: Run format agent to format the search results into JSON
        runner_format = InMemoryRunner(agent=action_agent)
        session_format = await runner_format.session_service.get_session(
            app_name=runner_format.app_name, user_id="user_default", session_id="session_action_format"
        )
        if not session_format:
            session_format = await runner_format.session_service.create_session(
                app_name=runner_format.app_name, user_id="user_default", session_id="session_action_format"
            )

        prompt_format = f"Format hasil riset berikut ke JSON terstruktur:\n{search_results}"
        msg_format = types.Content(role="user", parts=[types.Part.from_text(text=prompt_format)])
        
        collected_format = []
        async for event in runner_format.run_async(user_id="user_default", session_id=session_format.id, new_message=msg_format):
            if event.error_message:
                raise RuntimeError(f"Format Agent error: {event.error_message}")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        collected_format.append(part.text)

        response_str = "".join(collected_format).strip()
        logger.info(f"Formatted JSON response from action_agent: {response_str}")

        # Clean markdown code blocks from response if present
        if response_str.startswith("```"):
            lines = response_str.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            response_str = "\n".join(lines).strip()

        data = json.loads(response_str)
        rekomendasi = data.get("rekomendasi_lokasi", [])
        return {
            "judul_section": data.get("judul_section", "Rekomendasi Tindakan"),
            "rekomendasi_lokasi": rekomendasi,
            "panduan_pencarian": data.get("panduan_pencarian", ""),
            "lokasi": [loc.get("nama", "") for loc in rekomendasi],
            "tautan": [loc.get("tautan", "") for loc in rekomendasi]
        }

    except Exception as e:
        logger.error(f"Error pada execute_post_decision_actions: {str(e)}")
        
        # Determine fallback section title
        intent_to_title = {
            "Ingin menjual": "Platform Jual & Estimasi Harga",
            "Ingin donasikan": "Tempat Donasi",
            "Ingin perbaiki": "Tempat Servis Rekomendasi",
            "Ingin daur ulang": "Program Daur Ulang & Drop Point"
        }
        fallback_title = intent_to_title.get(user_intent, "Rekomendasi Tindakan")
        
        # Build specific fallback search guide
        panduan_map = {
            "Ingin menjual": f"Silakan buka situs Tokopedia/OLX lalu cari kata kunci '{item_name} second' untuk melihat listings yang aktif.",
            "Ingin donasikan": f"Gunakan Google Maps dengan kata kunci 'Panti Asuhan terdekat' atau hubungi Yayasan Sosial sejenis.",
            "Ingin perbaiki": f"Buka Google Maps dan cari 'Service Center {item_name}' atau 'Tempat servis {item_name} terdekat'.",
            "Ingin daur ulang": "Kunjungi situs resmi Waste4Change atau cari drop point e-waste terdekat di DKI Jakarta/kota Anda."
        }
        fallback_panduan = panduan_map.get(user_intent, "Cari tempat donasi, tempat perbaikan, atau bank sampah terdekat menggunakan Google Maps.")

        # Safe structured fallback based on the final decision
        fallback_map = {
            "Sell": [
                {"nama": "Tokopedia - Cari Jual Beli Bekas", "alamat": "Silakan cari produk sejenis dengan keyword di kolom pencarian", "tautan": f"https://www.tokopedia.com/search?q={item_name}+bekas"},
                {"nama": "OLX Indonesia - Barang Bekas", "alamat": "Cari listings aktif sesuai kota Anda", "tautan": f"https://www.olx.co.id/items/q-{item_name}"},
                {"nama": "Shopee Indonesia - Produk Second", "alamat": "Kategori produk bekas/layak pakai", "tautan": f"https://shopee.co.id/search?keyword={item_name}"}
            ],
            "Repair": [
                {"nama": "Pusat Servis Resmi (Brand Service Center)", "alamat": "Cari Pusat Servis Resmi terdekat dari merk/brand barang Anda di Google Maps", "tautan": f"https://www.google.com/maps/search/Service+Center+{item_name}"},
                {"nama": "Bengkel Reparasi Terdekat", "alamat": "Lokasi servis lokal di daerah sekitar Anda", "tautan": "https://www.google.com/maps/search/Servis+Terdekat"}
            ],
            "Donate": [
                {"nama": "Yayasan Sayap Ibu", "alamat": "Jl. Barito II No.55, Kebayoran Baru, Jakarta Selatan. Telp: +62 21-722-0442", "tautan": "https://yayasansayapibu.or.id"},
                {"nama": "Kitabisa (Donasi Online)", "alamat": "Platform Penggalangan Dana dan Donasi Online Indonesia", "tautan": "https://kitabisa.com"},
                {"nama": "Panti Asuhan Terdekat", "alamat": "Cari Lembaga Kesejahteraan Sosial Anak terdekat", "tautan": "https://www.google.com/maps/search/Panti+Asuhan"}
            ],
            "Recycle": [
                {"nama": "Waste4Change", "alamat": "Kompleks Vida Bekasi, Jawa Barat / Layanan Penjemputan Daur Ulang", "tautan": "https://waste4change.com"},
                {"nama": "Dropbox E-Waste Dinas Lingkungan Hidup", "alamat": "Berbagai titik halte Transjakarta dan kantor pemerintahan DKI Jakarta", "tautan": "https://lingkunganhidup.jakarta.go.id"},
                {"nama": "Bank Sampah Terdekat", "alamat": "Cari titik bank sampah aktif di sekitar pemukiman Anda", "tautan": "https://www.google.com/maps/search/Bank+Sampah"}
            ]
        }
        fallback_list = fallback_map.get(final_decision, [
            {"nama": "Ide Penyimpanan Kreatif (Storage Hacks)", "alamat": "Panduan merapikan barang dan wadah penyimpanan di rumah", "tautan": "https://id.pinterest.com"},
            {"nama": "Metode Marie Kondo (KonMari)", "alamat": "Tips melipat dan menyimpan barang agar menghemat ruang", "tautan": "https://konmari.com"}
        ])
        
        return {
            "judul_section": fallback_title,
            "rekomendasi_lokasi": fallback_list,
            "panduan_pencarian": fallback_panduan,
            "lokasi": [loc["nama"] for loc in fallback_list],
            "tautan": [loc["tautan"] for loc in fallback_list],
            "error": str(e)
        }
