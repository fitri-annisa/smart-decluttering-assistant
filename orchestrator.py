import asyncio
import logging
from google.adk.agents import SequentialAgent, ParallelAgent
from agents.understanding_agent import understanding_agent, analyze_item_details
from agents.repair_agent import repair_agent, evaluate_repairability
from agents.value_agent import value_agent, estimate_market_value
from agents.sustainability_agent import sustainability_agent, evaluate_sustainability_options
from agents.decision_agent import decision_agent, determine_final_action
from agents.recommendation_agent import recommendation_agent, generate_recommendations
from agents.action_agent import action_agent, execute_post_decision_actions

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Declare the ADK native multi-agent orchestration structure
parallel_assessors = ParallelAgent(
    name="parallel_assessors",
    sub_agents=[repair_agent, value_agent, sustainability_agent]
)

orchestrator_agent = SequentialAgent(
    name="orchestrator_agent",
    sub_agents=[
        understanding_agent,
        parallel_assessors,
        decision_agent,
        recommendation_agent,
        action_agent
    ]
)

async def run_decluttering_flow(item_description: str, image_path: str = None, user_intent: str = "Tidak tahu") -> dict:
    """
    Executes the multi-agent smart decluttering pipeline.
    Runs Repair, Value, and Sustainability assessments in parallel.
    
    Args:
        item_description (str): User description of the item.
        image_path (str, optional): Path to the uploaded image.
        user_intent (str): Special intent of the user.
        
    Returns:
        dict: Full payload of decisions, repair info, sustainability data, and recommendations.
    """
    try:
        logger.info("Executing Agent 1: Understanding Agent...")
        res_under = await analyze_item_details(item_description, image_path)
        logger.info(f"Understanding Agent output: {res_under}")
        
        # SKIP AGENT BASED ON INTENT
        run_repair = True
        run_value = True
        run_sustainability = True

        if user_intent == "Ingin menjual":
            run_repair = False
            run_sustainability = False
            logger.info("Intent is 'Ingin menjual': skipping Repair and Sustainability agents.")
        elif user_intent == "Ingin donasikan":
            run_repair = False
            run_value = False
            logger.info("Intent is 'Ingin donasikan': skipping Repair and Value agents.")
        elif user_intent == "Ingin perbaiki":
            run_value = False
            run_sustainability = False
            logger.info("Intent is 'Ingin perbaiki': skipping Value and Sustainability agents.")
        elif user_intent == "Ingin daur ulang":
            run_repair = False
            run_value = False
            logger.info("Intent is 'Ingin daur ulang': skipping Repair and Value agents.")

        # Build tasks based on skip flags
        if run_repair:
            task_repair = evaluate_repairability(
                res_under.get("nama_barang", "Barang"),
                res_under.get("kondisi", "Bagus"),
                item_description
            )
        else:
            async def get_dummy_repair():
                return {"bisa_diperbaiki": False, "estimasi_biaya_rp": 0, "skor": 0, "skipped": True}
            task_repair = get_dummy_repair()

        if run_value:
            task_value = estimate_market_value(
                res_under.get("nama_barang", "Barang"),
                res_under.get("merek", "Tidak Diketahui"),
                res_under.get("kondisi", "Bagus")
            )
        else:
            async def get_dummy_value():
                return {"harga_pasaran_rp": 0, "tingkat_permintaan": "Tidak Diketahui", "skor": 0, "skipped": True}
            task_value = get_dummy_value()

        if run_sustainability:
            task_sustainability = evaluate_sustainability_options(
                res_under.get("nama_barang", "Barang"),
                res_under.get("kondisi", "Bagus")
            )
        else:
            async def get_dummy_sustainability():
                return {"estimasi_co2_kg": 0.0, "rekomendasi_eco": "Tidak Diketahui", "skor": 0, "skipped": True}
            task_sustainability = get_dummy_sustainability()
            
        logger.info("Executing parallel assessor agents...")
        res_repair, res_value, res_sustainability = await asyncio.gather(
            task_repair, task_value, task_sustainability
        )
        logger.info(f"Repair output: {res_repair}")
        logger.info(f"Value output: {res_value}")
        logger.info(f"Sustainability output: {res_sustainability}")
        
        logger.info("Executing Agent 5: Decision Agent...")
        res_decision = await determine_final_action(
            res_under, res_repair, res_value, res_sustainability, user_intent
        )
        logger.info(f"Decision output: {res_decision}")
        
        logger.info("Executing Agent 6: Recommendation Agent...")
        res_recommendation = await generate_recommendations(
            res_decision.get("keputusan_terbaik", "Keep"),
            res_under,
            res_value.get("harga_pasaran_rp", 0),
            user_intent
        )
        logger.info(f"Recommendation output: {res_recommendation}")
        
        logger.info("Executing Agent 7: Action Agent...")
        res_action = await execute_post_decision_actions(
            res_under.get("nama_barang", "Barang"),
            res_decision.get("keputusan_terbaik", "Keep"),
            user_intent
        )
        logger.info(f"Action output: {res_action}")
        
        return {
            "item_details": res_under,
            "repair_info": res_repair,
            "valuation": res_value,
            "sustainability": res_sustainability,
            "decision": res_decision,
            "recommendations": res_recommendation,
            "action_taken": res_action
        }
    except Exception as e:
        logger.error(f"Error in orchestrator pipeline: {e}")
        # Safe fallback structure
        return {
            "item_details": {
                "nama_barang": item_description[:50] if item_description else "Tidak Diketahui",
                "kondisi": "Tidak Diketahui",
                "merek": "Tidak Diketahui",
                "umur_perkiraan_tahun": 0,
                "error": str(e)
            },
            "repair_info": {
                "bisa_diperbaiki": False,
                "estimasi_biaya_rp": 0,
                "skor": 0,
                "error": str(e)
            },
            "valuation": {
                "harga_pasaran_rp": 0,
                "tingkat_permintaan": "Tidak Diketahui",
                "skor": 0,
                "error": str(e)
            },
            "sustainability": {
                "estimasi_co2_kg": 0.0,
                "rekomendasi_eco": "Daur ulang",
                "skor": 0,
                "error": str(e)
            },
            "decision": {
                "keputusan_terbaik": "Keep",
                "skor_tiap_opsi": {"Keep": 100},
                "alasan": f"Gagal memproses pipeline: {e}",
                "error": str(e)
            },
            "recommendations": {
                "rekomendasi": "Simpan barang Anda terlebih dahulu.",
                "langkah_selanjutnya": ["Periksa kembali nanti."],
                "error": str(e)
            },
            "action_taken": {
                "lokasi": ["Rumah"],
                "tautan": ["#"],
                "error": str(e)
            }
        }
