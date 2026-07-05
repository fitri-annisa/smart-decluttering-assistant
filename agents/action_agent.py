import os
import json
import logging
import subprocess
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.tools import google_search
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def call_mcp_stdio_server(command: list[str], env: dict, tool_name: str, arguments: dict) -> str:
    """
    Calls a local MCP server over stdio using JSON-RPC 2.0 protocol.
    """
    try:
        process = subprocess.Popen(
            command,
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            env={**os.environ, **env}
        )
    except Exception as e:
        raise RuntimeError(f"Failed to start MCP server process: {str(e)}")
    
    def send_msg(msg):
        payload = json.dumps(msg) + "\n"
        process.stdin.write(payload)
        process.stdin.flush()
        
    def read_response(expected_id):
        while True:
            line = process.stdout.readline()
            if not line:
                break
            try:
                data = json.loads(line)
                if data.get("id") == expected_id:
                    return data
            except json.JSONDecodeError:
                continue
        return None

    try:
        # 1. Initialize
        init_req = {
            "jsonrpc": "2.0",
            "id": 1,
            "method": "initialize",
            "params": {
                "protocolVersion": "2024-11-05",
                "capabilities": {},
                "clientInfo": {"name": "SmartDeclutteringClient", "version": "1.0"}
            }
        }
        send_msg(init_req)
        init_res = read_response(1)
        if not init_res:
            raise RuntimeError("MCP initialization failed or timed out.")
            
        # 2. Initialized Notification
        initialized_notification = {
            "jsonrpc": "2.0",
            "method": "notifications/initialized"
        }
        send_msg(initialized_notification)
        
        # 3. Call Tool
        tool_req = {
            "jsonrpc": "2.0",
            "id": 2,
            "method": "tools/call",
            "params": {
                "name": tool_name,
                "arguments": arguments
            }
        }
        send_msg(tool_req)
        tool_res = read_response(2)
        
        if tool_res and "result" in tool_res:
            content = tool_res["result"].get("content", [])
            text_parts = [c.get("text", "") for c in content if c.get("type") == "text"]
            return "\n".join(text_parts)
        else:
            err = tool_res.get("error", {}) if tool_res else {}
            raise RuntimeError(f"MCP tool call failed: {err.get('message', 'Unknown error')}")
            
    finally:
        try:
            process.stdin.close()
        except:
            pass
        try:
            process.terminate()
            process.wait(timeout=2)
        except:
            pass

def brave_search_mcp_tool(query: str) -> str:
    """
    Search the web for real-time information using the Brave Search MCP server (Requires BRAVE_API_KEY).
    """
    brave_key = os.environ.get("BRAVE_API_KEY")
    if not brave_key:
        return "ERROR: BRAVE_API_KEY is not set in environment. Use google_search fallback tool."
        
    cmd = ["npx", "-y", "@modelcontextprotocol/server-brave-search"]
    env = {"BRAVE_API_KEY": brave_key}
    try:
        logger.info(f"Invoking Brave Search MCP tool for query: {query}")
        result = call_mcp_stdio_server(cmd, env, "brave_web_search", {"query": query})
        return result
    except Exception as e:
        return f"ERROR running Brave Search MCP: {str(e)}"

def google_maps_mcp_tool(query: str) -> str:
    """
    Search for physical locations, coordinates, and details in Indonesia using Google Maps MCP server (Requires GOOGLE_MAPS_API_KEY).
    """
    maps_key = os.environ.get("GOOGLE_MAPS_API_KEY")
    if not maps_key:
        return "ERROR: GOOGLE_MAPS_API_KEY is not set in environment. Use google_search fallback tool."
        
    cmd = ["npx", "-y", "@modelcontextprotocol/server-google-maps"]
    env = {"GOOGLE_MAPS_API_KEY": maps_key}
    try:
        logger.info(f"Invoking Google Maps MCP tool for query: {query}")
        result = call_mcp_stdio_server(cmd, env, "search_places", {"query": query})
        return result
    except Exception as e:
        return f"ERROR running Google Maps MCP: {str(e)}"

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
    model="gemini-2.5-flash",
    instruction=(
        "Anda adalah Agen Riset Lokasi. Tugas Anda adalah mencari lokasi fisik atau daring "
        "spesifik, nyata, dan aktif di Indonesia beserta alamat lengkap, kontak/WA jika ada, estimasi harga/langkah daftar, dan tautan (URL) SPESIFIK untuk memproses keputusan decluttering barang:\n"
        "- Jika user_intent adalah 'Ingin menjual': Cari link listing produk bekas sejenis di Tokopedia/OLX (misal Tokopedia search query path seperti https://www.tokopedia.com/search?q=iphone+13+second), estimasi harga pasaran bekas sejenis, serta tips jual.\n"
        "- Jika user_intent adalah 'Ingin donasikan': Cari nama yayasan/komunitas di Indonesia (misal: Yayasan Sayap Ibu, Panti Asuhan), alamat fisik lengkap, nomor WA/kontak donasi jika ada, dan tautan spesifik.\n"
        "- Jika user_intent adalah 'Ingin perbaiki': Cari nama toko servis/service center resmi terdekat, alamat fisik lengkap, rating toko jika ada, serta link Google Maps spesifik menuju lokasi tersebut.\n"
        "- Jika user_intent adalah 'Ingin daur ulang': Cari nama program daur ulang resmi (misal: Waste4Change, program Trade In Samsung/Apple) beserta drop point e-waste/bank sampah, cara daftar/proses daur ulang, dan tautan pendaftaran/lokasi valid.\n"
        "- Jika user_intent adalah 'Tidak tahu': Cari ringkasan singkat dari keempat opsi di atas secara umum.\n\n"
        "Gunakan tools yang tersedia. Anda memiliki brave_search_mcp_tool untuk mencari informasi web secara real-time via Brave Search MCP, "
        "dan google_maps_mcp_tool untuk mencari tempat servis/donasi/daur ulang secara fisik via Google Maps MCP. "
        "Jika environment key tidak terkonfigurasi untuk MCP tools tersebut (response mengembalikan pesan 'ERROR: ... API_KEY is not set'), "
        "kembalilah menggunakan google_search bawaan sebagai fallback utama.\n\n"
        "PENTING: Jangan pernah memberikan tautan homepage generik (seperti tokopedia.com, olx.co.id, google.com). URL harus memiliki path spesifik (misal: link produk search Tokopedia/OLX, link lokasi Google Maps spesifik, link form pendaftaran). "
        "Jika hasil spesifik tidak ditemukan, tuliskan panduan teks (langkah demi langkah) tentang cara mencarinya secara manual."
    ),
    tools=[google_search, brave_search_mcp_tool, google_maps_mcp_tool]
)

# Define the Google ADK Agent for formatting action recommendations (no tools, has output schema)
action_agent = Agent(
    name="action_agent",
    model="gemini-2.5-flash",
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

async def execute_post_decision_actions(item_name: str, final_decision: str, user_intent: str = "Tidak tahu", language: str = "id") -> dict:
    """
    Mencari lokasi/resource terdekat untuk memproses keputusan decluttering.
    
    Args:
        item_name (str): Nama barang yang dievaluasi.
        final_decision (str): Keputusan akhir (Keep, Repair, Sell, Donate, Recycle).
        user_intent (str): Intent khusus pengguna.
        language (str): Kode bahasa ("id" atau "en").
        
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

        lang_instruction = (
            "You must respond entirely in English. All field values, explanations, and recommendations must be in English."
            if language == "en" else
            "Kamu harus merespons sepenuhnya dalam Bahasa Indonesia. Semua nilai field, penjelasan, dan rekomendasi harus dalam Bahasa Indonesia."
        )

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
        prompt_search += f"\n\n{lang_instruction}"
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

        prompt_format = f"Format hasil riset berikut ke JSON terstruktur:\n{search_results}\n\n{lang_instruction}"
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
