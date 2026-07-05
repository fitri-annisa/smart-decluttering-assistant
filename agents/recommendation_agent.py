import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RecommendationOutput(BaseModel):
    rekomendasi: str = Field(description="Rekomendasi tindakan utama dalam Bahasa Indonesia yang singkat dan padat")
    langkah_selanjutnya: list[str] = Field(description="Daftar langkah-langkah selanjutnya yang konkrit dan actionable (minimal 3 langkah)")

# Define the Google ADK Agent for generating user-friendly advice
recommendation_agent = Agent(
    name="recommendation_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "Anda adalah Agen Rekomendasi. Tugas Anda adalah memberikan saran konkrit dan actionable "
        "dalam Bahasa Indonesia berdasarkan keputusan final yang diambil oleh Agen Keputusan. "
        "Tulis rekomendasi utama yang santun dan mudah dipahami, serta jabarkan langkah selanjutnya "
        "yang harus diambil oleh pengguna (misal: menyiapkan barang, memeriksa kondisi detail, dll)."
    ),
    output_schema=RecommendationOutput
)

async def generate_recommendations(final_decision: str, item_details: dict, market_value: float = None, user_intent: str = "Tidak tahu") -> dict:
    """
    Menghasilkan rekomendasi konkrit berdasarkan keputusan akhir.
    
    Args:
        final_decision (str): Keep, Repair, Sell, Donate, Recycle, dll.
        item_details (dict): Informasi detail barang dari understanding_agent.
        market_value (float, optional): Estimasi harga jual kembali.
        user_intent (str): Intent khusus pengguna.
        
    Returns:
        dict: Rekomendasi utama dan daftar langkah selanjutnya.
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(agent=recommendation_agent)
        
        # Create runner session
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="user_default", session_id="session_recommendation"
        )
        if not session:
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="user_default", session_id="session_recommendation"
            )

        prompt = (
            f"Hasilkan rekomendasi tindakan untuk barang berikut:\n"
            f"Barang: {item_details.get('nama_barang', 'Tidak Diketahui')}\n"
            f"Kondisi: {item_details.get('kondisi', 'Tidak Diketahui')}\n"
            f"Keputusan Akhir: {final_decision}\n"
            f"Harga Jual (jika ada): Rp {market_value if market_value else 'Tidak ada'}\n"
        )
        
        if user_intent and user_intent != "Tidak tahu":
            prompt += (
                f"PENTING: Pengguna memilih intent khusus: '{user_intent}'.\n"
                f"Rekomendasi utama dan langkah selanjutnya harus langsung fokus ke intent '{user_intent}' ini. "
                f"Jangan terlalu banyak membahas opsi atau alternatif lain."
            )
        new_message = types.Content(role="user", parts=[types.Part.from_text(text=prompt)])
        
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
        logger.info(f"Response raw dari recommendation_agent: {response_str}")

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
            "rekomendasi": str(data.get("rekomendasi", "Silakan simpan barang Anda dengan rapi.")),
            "langkah_selanjutnya": list(data.get("langkah_selanjutnya", []))
        }

    except Exception as e:
        logger.error(f"Error pada generate_recommendations: {str(e)}")
        # Safe fallback dictionary
        return {
            "rekomendasi": f"Rekomendasi default karena kegagalan pemrosesan: {str(e)}",
            "langkah_selanjutnya": [
                "Persiapkan barang Anda.",
                "Periksa kembali kebutuhan barang.",
                "Pikirkan kembali keputusan decluttering."
            ],
            "error": str(e)
        }
