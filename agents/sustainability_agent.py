import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class SustainabilityOutput(BaseModel):
    estimasi_co2_kg: float = Field(description="Estimasi jejak karbon (CO2) dalam kilogram (kg) jika barang ini dibuang begitu saja tanpa didaur ulang")
    rekomendasi_eco: str = Field(description="Rekomendasi tindakan ramah lingkungan untuk barang ini (misal: disumbangkan, didaur ulang di e-waste, dijadikan kompos, dll)")
    skor: int = Field(description="Skor keramahan lingkungan penanganan barang (0-100) di mana 100 berarti sangat berkelanjutan/ramah lingkungan")

# Define the Google ADK Agent for sustainability analysis
sustainability_agent = Agent(
    name="sustainability_agent",
    model="gemini-2.5-flash-lite",
    instruction=(
        "Anda adalah Agen Keberlanjutan Lingkungan. Tugas Anda adalah memperkirakan dampak lingkungan "
        "dari pembuangan barang berdasarkan nama barang, kategori, dan kondisinya. "
        "Perkirakan estimasi jejak karbon CO2 (dalam kg) yang dihasilkan jika dibuang begitu saja "
        "dibandingkan jika didaur ulang atau dipakai kembali. Berikan rekomendasi ramah lingkungan "
        "serta skor keberlanjutan dari 0 hingga 100."
    ),
    output_schema=SustainabilityOutput
)

async def evaluate_sustainability_options(item_name: str, category: str) -> dict:
    """
    Evaluasi opsi pembuangan barang yang ramah lingkungan.
    
    Args:
        item_name (str): Nama barang.
        category (str): Kategori barang.
        
    Returns:
        dict: Hasil evaluasi keberlanjutan (estimasi_co2_kg, rekomendasi_eco, skor).
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(agent=sustainability_agent)
        
        # Create runner session
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="user_default", session_id="session_sustainability"
        )
        if not session:
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="user_default", session_id="session_sustainability"
            )

        prompt = (
            f"Evaluasi keberlanjutan untuk barang berikut:\n"
            f"Nama Barang: {item_name}\n"
            f"Kategori: {category}"
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
        logger.info(f"Response raw dari sustainability_agent: {response_str}")

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
            "estimasi_co2_kg": float(data.get("estimasi_co2_kg", 0.0)),
            "rekomendasi_eco": str(data.get("rekomendasi_eco", "Daur ulang secara bertanggung jawab")),
            "skor": int(data.get("skor", 50))
        }

    except Exception as e:
        logger.error(f"Error pada evaluate_sustainability_options: {str(e)}")
        # Safe fallback dictionary
        return {
            "estimasi_co2_kg": 0.0,
            "rekomendasi_eco": "Daur ulang secara bertanggung jawab",
            "skor": 0,
            "error": str(e)
        }
