import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class UnderstandingOutput(BaseModel):
    nama_barang: str = Field(description="Nama lengkap barang hasil identifikasi dalam Bahasa Indonesia")
    kondisi: str = Field(description="Kondisi fisik barang (misal: Baru, Seperti Baru, Bagus, Layak Pakai, Rusak)")
    merek: str = Field(description="Merek atau brand barang, jika tidak diketahui atau tidak bermerek isi 'Tidak Diketahui'")
    umur_perkiraan_tahun: int = Field(description="Estimasi umur barang dalam tahun (bulatkan ke bilangan bulat terdekat)")

# Define the Google ADK Agent
understanding_agent = Agent(
    name="understanding_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "Anda adalah Agen Pemahaman Barang. Tugas Anda adalah menganalisis deskripsi barang "
        "dan/atau foto barang yang disediakan oleh pengguna. Identifikasi nama barang, "
        "merek barang, kondisi barang saat ini, serta perkiraan umur barang dalam tahun.\n\n"
        "PENTING: Asumsikan tahun saat ini (hari ini) adalah 2025. Jika pengguna secara eksplisit menyebutkan tanggal, "
        "bulan, atau tahun pembelian di deskripsi (misal: 'beli februari 2023' atau 'pembelian 2021'), "
        "hitung umur barang tersebut dari tahun/tanggal itu sampai tahun 2025 (contoh: 'beli februari 2023' = 2 tahun, "
        "dan 'beli 2021' = 4 tahun). Jangan pernah mengasumsikan umur default 1 tahun jika terdapat info tanggal "
        "atau tahun pembelian yang eksplisit di input.\n\n"
        "Output harus berupa JSON valid yang mematuhi skema yang ditentukan."
    ),
    output_schema=UnderstandingOutput
)

async def analyze_item_details(item_description: str, image_path: str = None) -> dict:
    """
    Menganalisis detail barang menggunakan Gemini multimodal (teks + gambar).
    
    Args:
        item_description (str): Deskripsi barang dari user.
        image_path (str, optional): Path ke file gambar barang.
        
    Returns:
        dict: Hasil analisis berupa nama_barang, kondisi, merek, umur_perkiraan_tahun.
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Validate API Key availability
        if not os.environ.get("GEMINI_API_KEY") and not os.environ.get("GOOGLE_API_KEY"):
            logger.warning("Warning: GEMINI_API_KEY atau GOOGLE_API_KEY tidak ditemukan di environment variables.")

        # Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(agent=understanding_agent)
        
        # Create runner session
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="user_default", session_id="session_understanding"
        )
        if not session:
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="user_default", session_id="session_understanding"
            )

        # Build parts (text prompt + optional image)
        prompt_text = f"Analisis barang berikut:\nDeskripsi: {item_description}"
        parts = [types.Part.from_text(text=prompt_text)]
        
        if image_path and os.path.exists(image_path):
            with open(image_path, "rb") as f:
                img_bytes = f.read()
            
            # Detect mime type from file extension
            ext = os.path.splitext(image_path)[1].lower()
            mime_type = "image/jpeg"
            if ext == ".png":
                mime_type = "image/png"
            elif ext == ".gif":
                mime_type = "image/gif"
            
            parts.append(types.Part.from_bytes(data=img_bytes, mime_type=mime_type))
            logger.info(f"Menambahkan gambar dari: {image_path} ({mime_type})")

        new_message = types.Content(role="user", parts=parts)
        
        # Execute the agent
        collected_text = []
        async for event in runner.run_async(user_id="user_default", session_id=session.id, new_message=new_message):
            if event.error_message:
                raise RuntimeError(f"Runner error: {event.error_message}")
            if event.content and event.content.parts:
                for part in event.content.parts:
                    if part.text:
                        collected_text.append(part.text)

        response_str = "".join(collected_text).strip()
        logger.info(f"Response raw dari understanding_agent: {response_str}")

        # Clean markdown code blocks from response if present
        if response_str.startswith("```"):
            lines = response_str.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            response_str = "\n".join(lines).strip()

        data = json.loads(response_str)
        return {
            "nama_barang": data.get("nama_barang", "Tidak Diketahui"),
            "kondisi": data.get("kondisi", "Bagus"),
            "merek": data.get("merek", "Tidak Diketahui"),
            "umur_perkiraan_tahun": int(data.get("umur_perkiraan_tahun", 0))
        }

    except Exception as e:
        logger.error(f"Error pada analyze_item_details: {str(e)}")
        # Safe fallback dictionary
        return {
            "nama_barang": item_description[:50] if item_description else "Tidak Diketahui",
            "kondisi": "Tidak Diketahui",
            "merek": "Tidak Diketahui",
            "umur_perkiraan_tahun": 0,
            "error": str(e)
        }
