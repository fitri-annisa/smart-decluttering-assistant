import os
import json
import logging
from pydantic import BaseModel, Field
from google.adk import Agent
from google.adk.runners import InMemoryRunner
from google.genai import types

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class OptionScores(BaseModel):
    Keep: int = Field(description="Skor kelayakan untuk opsi Keep (0-100)")
    Repair: int = Field(description="Skor kelayakan untuk opsi Repair (0-100)")
    Sell: int = Field(description="Skor kelayakan untuk opsi Sell (0-100)")
    Donate: int = Field(description="Skor kelayakan untuk opsi Donate (0-100)")
    Recycle: int = Field(description="Skor kelayakan untuk opsi Recycle (0-100)")

class DecisionOutput(BaseModel):
    keputusan_terbaik: str = Field(description="Keputusan terbaik (pilih salah satu dari: Keep, Repair, Sell, Donate, Recycle)")
    skor_tiap_opsi: OptionScores = Field(description="Skor kelayakan untuk masing-masing opsi (Keep, Repair, Sell, Donate, Recycle) dalam rentang 0-100")
    alasan: str = Field(description="Penjelasan detail dari hasil keputusan berbasis pembobotan (Repair 40%, Value 35%, Sustainability 25%)")

# Define the Google ADK Agent for compiling assessments and deciding status
decision_agent = Agent(
    name="decision_agent",
    model="gemini-2.5-flash",
    instruction=(
        "Anda adalah Agen Keputusan. Tugas Anda adalah mengintegrasikan evaluasi dari Agen Perbaikan, "
        "Agen Penaksir Nilai, dan Agen Keberlanjutan. "
        "Gunakan pembobotan berikut untuk menentukan opsi terbaik:\n"
        "- Kelayakan Perbaikan (Repair Agent score): Bobot 40%\n"
        "- Nilai Pasar/Jual Kembali (Value Agent score): Bobot 35%\n"
        "- Dampak Keberlanjutan (Sustainability Agent score): Bobot 25%\n\n"
        "Hitung skor kelayakan untuk setiap opsi (Keep, Repair, Sell, Donate, dan Recycle). "
        "Tentukan keputusan terbaik (keputusan_terbaik) beserta penjelasan detail (alasan) mengapa "
        "opsi tersebut dipilih berdasarkan perhitungan bobot tadi."
    ),
    output_schema=DecisionOutput
)

async def determine_final_action(item_details: dict, repair_assessment: dict, value_assessment: dict, sustainability_assessment: dict, user_intent: str = "Tidak tahu", language: str = "id") -> dict:
    """
    Menentukan keputusan terbaik menggunakan decision_agent.
    
    Args:
        item_details (dict): Informasi dasar barang dari understanding_agent.
        repair_assessment (dict): Hasil analisis perbaikan dari repair_agent.
        value_assessment (dict): Hasil analisis harga dari value_agent.
        sustainability_assessment (dict): Hasil analisis jejak karbon dari sustainability_agent.
        user_intent (str): Intent khusus pengguna (Tidak tahu, Ingin menjual, Ingin donasikan, Ingin perbaiki, Ingin daur ulang).
        language (str): Kode bahasa ("id" atau "en").
        
    Returns:
        dict: Keputusan terbaik, nilai skor tiap opsi, dan alasan terperinci.
    """
    try:
        # Load environment variables if available
        try:
            from dotenv import load_dotenv
            load_dotenv()
        except ImportError:
            pass

        # Initialize the ADK InMemoryRunner
        runner = InMemoryRunner(agent=decision_agent)
        
        # Create runner session
        session = await runner.session_service.get_session(
            app_name=runner.app_name, user_id="user_default", session_id="session_decision"
        )
        if not session:
            session = await runner.session_service.create_session(
                app_name=runner.app_name, user_id="user_default", session_id="session_decision"
            )

        prompt = (
            f"Tentukan keputusan terbaik berdasarkan data evaluasi berikut:\n"
            f"Barang: {item_details.get('nama_barang', 'Tidak Diketahui')}\n"
            f"Kondisi: {item_details.get('kondisi', 'Tidak Diketahui')}\n"
            f"Hasil Evaluasi Perbaikan: {json.dumps(repair_assessment)}\n"
            f"Hasil Evaluasi Nilai Jual: {json.dumps(value_assessment)}\n"
            f"Hasil Evaluasi Dampak Keberlanjutan: {json.dumps(sustainability_assessment)}"
        )
        
        if user_intent and user_intent != "Tidak tahu":
            prompt += (
                f"\n\nCATATAN INTENT KHUSUS PENGGUNA: Pengguna secara eksplisit menyatakan berniat: '{user_intent}'.\n"
                f"- Jika user_intent adalah 'Ingin menjual', naikkan (boost) skor kelayakan opsi 'Sell' sebesar +20 poin.\n"
                f"- Jika user_intent adalah 'Ingin donasikan', naikkan (boost) skor kelayakan opsi 'Donate' sebesar +20 poin.\n"
                f"- Jika user_intent adalah 'Ingin perbaiki', naikkan (boost) skor kelayakan opsi 'Repair' sebesar +20 poin.\n"
                f"- Jika user_intent adalah 'Ingin daur ulang', naikkan (boost) skor kelayakan opsi 'Recycle' sebesar +20 poin.\n"
                f"Sesuaikan keputusan_terbaik dan alasan penjelasan agar fokus dan berorientasi pada intent tersebut."
            )

        lang_instruction = (
            "You must respond entirely in English. All field values, explanations, and recommendations must be in English."
            if language == "en" else
            "Kamu harus merespons sepenuhnya dalam Bahasa Indonesia. Semua nilai field, penjelasan, dan rekomendasi harus dalam Bahasa Indonesia."
        )
        prompt += f"\n\n{lang_instruction}"

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
        logger.info(f"Response raw dari decision_agent: {response_str}")

        # Clean markdown code blocks from response if present
        if response_str.startswith("```"):
            lines = response_str.split("\n")
            if lines[0].strip().startswith("```"):
                lines = lines[1:]
            if lines[-1].strip().startswith("```"):
                lines = lines[:-1]
            response_str = "\n".join(lines).strip()

        data = json.loads(response_str)
        skor_opsi = dict(data.get("skor_tiap_opsi", {}))
        keputusan = str(data.get("keputusan_terbaik", "Keep"))

        # Apply Python-level intent scoring boost and override
        intent_to_option = {
            "Ingin menjual": "Sell",
            "Ingin donasikan": "Donate",
            "Ingin perbaiki": "Repair",
            "Ingin daur ulang": "Recycle"
        }
        
        target_option = intent_to_option.get(user_intent)
        if target_option:
            if target_option in skor_opsi:
                skor_opsi[target_option] = min(skor_opsi[target_option] + 20, 100)
            else:
                skor_opsi[target_option] = 60 # Safe default for boosted option if not found
            keputusan = target_option

        return {
            "keputusan_terbaik": keputusan,
            "skor_tiap_opsi": skor_opsi,
            "alasan": str(data.get("alasan", "Keputusan diambil berdasarkan intent khusus pengguna."))
        }

    except Exception as e:
        logger.error(f"Error pada determine_final_action: {str(e)}")
        # Safe fallback dictionary
        fallback_decision = "Keep"
        intent_to_option = {
            "Ingin menjual": "Sell",
            "Ingin donasikan": "Donate",
            "Ingin perbaiki": "Repair",
            "Ingin daur ulang": "Recycle"
        }
        if user_intent in intent_to_option:
            fallback_decision = intent_to_option[user_intent]
            
        return {
            "keputusan_terbaik": fallback_decision,
            "skor_tiap_opsi": {"Keep": 40, "Repair": 40, "Sell": 40, "Donate": 40, "Recycle": 40},
            "alasan": f"Error dalam mengambil keputusan: {str(e)}. Memilih fallback '{fallback_decision}' sesuai intent pengguna.",
            "error": str(e)
        }
