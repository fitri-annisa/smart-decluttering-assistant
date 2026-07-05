import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class RepairOutput(BaseModel):
    bisa_diperbaiki: bool = Field(description="Apakah barang tersebut secara teknis bisa diperbaiki")
    estimasi_biaya_rp: int = Field(description="Estimasi biaya perbaikan dalam Rupiah (Rp). Jika tidak bisa diperbaiki, isi 0")
    skor: int = Field(description="Skor kelayakan perbaikan (0-100) di mana 100 berarti sangat layak dan mudah diperbaiki, dan 0 berarti tidak layak diperbaiki")

# Define the Google ADK Agent for repair estimation
repair_agent = Agent(
    name="repair_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Anda adalah Agen Perbaikan Barang. Tugas Anda adalah menganalisis apakah barang "
        "dapat diperbaiki berdasarkan nama barang, kondisinya, dan deskripsi masalahnya. "
        "Evaluasi juga ketersediaan sparepart di pasaran Indonesia dan tentukan estimasi "
        "biaya perbaikan (dalam Rupiah) serta berikan skor kelayakan perbaikan (0-100)."
    ),
    output_schema=RepairOutput
)

async def evaluate_repairability(item_name: str, condition: str, issue_description: str = None) -> dict:
    """
    Evaluasi kelayakan perbaikan barang.
    
    Args:
        item_name (str): Nama barang.
        condition (str): Kondisi barang.
        issue_description (str, optional): Deskripsi kerusakan atau masalah pada barang.
        
    Returns:
        dict: Hasil evaluasi perbaikan (bisa_diperbaiki, estimasi_biaya_rp, skor).
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(agent=repair_agent)
        
        # Create runner session
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="user_default", session_id="session_repair"
        )
        if not session:
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="user_default", session_id="session_repair"
            )

        prompt = (
            f"Evaluasi perbaikan untuk barang berikut:\n"
            f"Nama Barang: {item_name}\n"
            f"Kondisi: {condition}\n"
            f"Deskripsi Masalah: {issue_description or 'Tidak disebutkan masalah khusus'}"
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
        logger.info(f"Response raw dari repair_agent: {response_str}")

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
            "bisa_diperbaiki": bool(data.get("bisa_diperbaiki", False)),
            "estimasi_biaya_rp": int(data.get("estimasi_biaya_rp", 0)),
            "skor": int(data.get("skor", 50))
        }

    except Exception as e:
        logger.error(f"Error pada evaluate_repairability: {str(e)}")
        # Safe fallback dictionary
        return {
            "bisa_diperbaiki": False,
            "estimasi_biaya_rp": 0,
            "skor": 0,
            "error": str(e)
        }
