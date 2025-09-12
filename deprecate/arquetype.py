import os
import random
import logging
import re # Importar re para expresiones regulares
from datetime import datetime
from pymongo import MongoClient
from fastapi import HTTPException, status
from dotenv import load_dotenv
import urllib.parse
from typing import Optional, Dict, List, Any, Union
import anthropic # Necesitarás `pip install anthropic`
from openai import OpenAI # Uncomment if not imported at the top of the file
import json # Added for JSON parsing
import asyncio # Added for asyncio.to_thread if needed for sse_dispatch_event
import redis.asyncio as aioredis

# Import sse_dispatch_event
from helper.sse_utils import sse_dispatch_event

# Cargar variables de entorno
load_dotenv()

# Configurar logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Configuración de API (necesitaremos importar ask_claude)
# Asumiendo que está disponible en n_informes o un módulo similar
# from .n_informes import ask_claude # O la ubicación correcta
# --- Placeholder para ask_claude --- 
# Necesitarás importar o definir la función ask_claude aquí. 
# Por ahora, la definiré como un placeholder para que el código sea válido.
# ASEGÚRATE DE REEMPLAZAR ESTO CON LA IMPORTACIÓN REAL
def ask_claude(prompt: str, model: str = "anthropic/claude-3.5-sonnet", max_tokens: int = 4000) -> Union[Dict[str, Any], str]:
    try:
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables.")
            return "Error: OPENROUTER_API_KEY not set."

        site_url = os.getenv("OPENROUTER_SITE_URL", "")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        headers = {}
        if site_url:
            headers["HTTP-Referer"] = site_url

        # Define the schema for a single archetype
        single_archetype_props = {
            "name": {"type": "string", "description": "The name of the archetype."},
            "general_description": {"type": "string", "description": "Essence of the archetype: main motivation, distinctive behavior, core need. 3-4 lines max."},
            "pain_points": {"type": "array", "items": {"type": "string"}, "description": "Frustrations expressed in reviews. 4-5 points max, ordered by frequency."},
            "fears_and_concerns": {"type": "array", "items": {"type": "string"}, "description": "Underlying worries, implicit fears from language used."},
            "objections": {"type": "array", "items": {"type": "string"}, "description": "Rational and argued barriers expressed towards the product/service."},
            "goals_and_objectives": {"type": "array", "items": {"type": "string"}, "description": "What the user expresses wanting to achieve, desired outcomes."},
            "expected_benefits": {"type": "array", "items": {"type": "string"}, "description": "Advantages the user expects, functional and emotional."},
            "values": {"type": "array", "items": {"type": "string"}, "description": "Fundamental principles and beliefs inferred from evaluative language."},
            "social_behavior": {"type": "string", "description": "Observable interaction patterns, usage/consumption descriptions."},
            "influence_factors": {"type": "array", "items": {"type": "string"}, "description": "Elements impacting decisions, rational and emotional."},
            "internal_narrative": {"type": "string", "description": "Deep, unexpressed motivations, underlying psychological needs."}
        }
        single_archetype_required = list(single_archetype_props.keys())

        # Define the overall tool schema for the LLM to generate a list of archetypes
        tools = [
            {
                "type": "function",
                "function": {
                    "name": "extract_customer_archetypes",
                    "description": "Extracts 3 behavioral customer archetypes based on the provided reviews and brand context.",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "archetypes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": single_archetype_props,
                                    "required": single_archetype_required
                                },
                                "description": "A list of 3 generated behavioral archetypes."
                            }
                        },
                        "required": ["archetypes"]
                    }
                }
            }
        ]

        completion = client.chat.completions.create(
            extra_headers=headers if headers else None,
            model=model,
            messages=[
                {"role": "system", "content": "You are an expert market researcher specializing in consumer behavior analysis. Please generate exactly 3 distinct customer archetypes based on the user's input, following the structure of the 'extract_customer_archetypes' tool."},
                {"role": "user", "content": prompt}
            ],
            tools=tools,
            tool_choice={"type": "function", "function": {"name": "extract_customer_archetypes"}},
            max_tokens=max_tokens,
            temperature=0.5,
        )

        message = completion.choices[0].message
        if message.tool_calls and message.tool_calls[0].function.name == "extract_customer_archetypes":
            function_arguments_json_str = message.tool_calls[0].function.arguments
            try:
                structured_data = json.loads(function_arguments_json_str)
                # Basic validation for the expected structure
                if "archetypes" in structured_data and isinstance(structured_data["archetypes"], list):
                    logger.info(f"Successfully extracted {len(structured_data['archetypes'])} archetypes via structured output.")
                    return structured_data # This will be like {"archetypes": [...]}
                else:
                    logger.error("Structured output from LLM is missing 'archetypes' list or is malformed.")
                    return "Error: LLM output malformed (missing archetypes list)."
            except json.JSONDecodeError as e:
                logger.error(f"Failed to parse JSON from LLM tool call arguments: {e}. Arguments: {function_arguments_json_str}")
                return f"Error: Failed to parse LLM JSON response. {e}"
        else:
            logger.warning("OpenRouter response did not use the 'extract_customer_archetypes' tool as expected or had no tool calls.")
            # Log the actual response content for debugging if it's not a tool call
            logger.debug(f"LLM response content: {message.content}")
            return "Error: LLM did not use the required tool for structured output."

    except Exception as e:
        logger.error(f"Error connecting to OpenRouter or processing LLM response: {e}", exc_info=True)
        return "Error: API call to OpenRouter/LLM failed."
# --- Fin Placeholder ask_claude ---


def get_llm_chat_response(system_prompt: str, messages_history: List[Dict[str, str]], model: str = "openai/gpt-4.1", max_tokens: int = 1000) -> Union[str, Dict[str, Any]]:
    try:
        openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        if not openrouter_api_key:
            logger.error("OPENROUTER_API_KEY not found in environment variables.")
            return {"error": "OPENROUTER_API_KEY not set."}

        site_url = os.getenv("OPENROUTER_SITE_URL", "")

        client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=openrouter_api_key,
        )

        headers = {}
        if site_url:
            headers["HTTP-Referer"] = site_url
        
        # Construct messages for the API call
        # System prompt first, then history
        api_messages = [{"role": "system", "content": system_prompt}] + messages_history

        logger.debug(f"Sending chat request to OpenRouter model {model}. System prompt: {system_prompt[:200]}... History length: {len(messages_history)}")

        completion = client.chat.completions.create(
            extra_headers=headers if headers else None,
            model=model,
            messages=api_messages,
            max_tokens=max_tokens,
            temperature=0.7, # Suitable for creative chat
        )

        response_content = completion.choices[0].message.content
        if response_content:
            logger.info(f"Successfully received chat response from LLM model {model}.")
            return response_content.strip()
        else:
            logger.warning(f"LLM model {model} response content was empty.")
            return {"error": "LLM returned an empty response."}

    except Exception as e:
        logger.error(f"Error connecting to OpenRouter or processing LLM chat response from model {model}: {e}", exc_info=True)
        return {"error": f"API call to OpenRouter/LLM failed: {str(e)}"}


# Conexión a MongoDB
MONGODB_URI = os.getenv("MONGODB_URI")
if not MONGODB_URI:
    logger.error("MongoDB URI not found in environment variables.")
    # Decide cómo manejar esto: ¿lanzar error o usar un default?
    # raise ValueError("MONGODB_URI environment variable not set.")

# CORRECT Database name for Archetypes
DB_NAME_ARCHETYPES = "Archetypes" 

# Database for Reviews (if needed by other potential functions in this file, otherwise can be removed)
DB_NAME_REVIEWS = "Reviews" 

# Lista de colecciones de donde extraer reseñas - ¡¡CONFIRMAR ESTA LISTA!!
REVIEW_COLLECTIONS = [
    "reviews_trustpilot_gold",
    "reviews_tripadvisor_gold",
    "reviews_google_gold",
    "reviews_amazon_gold",
    "reviews_druni_gold" # Asegúrate que el nombre sea correcto
    # Añadir otras colecciones si existen (ej. Amazon, etc.)
]

DEFAULT_SAMPLE_SIZE = 100 # Número de reseñas a muestrear

def get_mongo_client():
    """Crea y devuelve un cliente MongoDB."""
    try:
        client = MongoClient(MONGODB_URI)
        # Probar conexión
        client.admin.command('ping')
        logger.info("MongoDB connection successful.")
        return client
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        return None

def fetch_review_sample(brand_name: str, sample_size: int = DEFAULT_SAMPLE_SIZE) -> list[str]:
    """Obtiene una muestra aleatoria de textos de reseñas para una marca específica desde MongoDB."""
    client = get_mongo_client()
    if not client:
        raise HTTPException(status_code=503, detail="Database connection unavailable")

    all_reviews = []
    try:
        db = client[DB_NAME_REVIEWS]
        for coll_name in REVIEW_COLLECTIONS:
            if coll_name in db.list_collection_names():
                collection = db[coll_name]
                # Asume que hay un campo 'brand_name' para filtrar
                # ¡¡VERIFICAR QUE EL CAMPO brand_name EXISTE Y ES CORRECTO EN LAS COLECCIONES!!
                # Si no existe, necesitarás otro método para filtrar (ej. audit_id si aplica)
                query = {"brand_name": brand_name, "review": {"$exists": True, "$ne": ""}}
                # Proyectar solo el campo 'review'
                reviews_cursor = collection.find(query, {"review": 1, "_id": 0})
                reviews_texts = [doc.get("review") for doc in reviews_cursor if doc.get("review")]
                all_reviews.extend(reviews_texts)
                logger.info(f"Fetched {len(reviews_texts)} reviews from {coll_name} for brand '{brand_name}'.")
            else:
                logger.warning(f"Collection {coll_name} not found in database {DB_NAME_REVIEWS}.")

    except Exception as e:
        logger.error(f"Error fetching reviews from MongoDB for brand {brand_name}: {e}", exc_info=True)
        # No lanzar excepción aquí, intentaremos generar con lo que tengamos (si hay algo)
    finally:
        client.close()

    if not all_reviews:
        logger.warning(f"No reviews found for brand '{brand_name}' in specified collections.")
        return []

    # Tomar muestra aleatoria
    sample_size = min(len(all_reviews), sample_size)
    sampled_reviews = random.sample(all_reviews, sample_size)
    logger.info(f"Returning {len(sampled_reviews)} sampled reviews for brand '{brand_name}'.")
    return sampled_reviews

def generate_archetypes_from_reviews(brand_name: str, reviews_sample: list[str]) -> Union[List[Dict[str, Any]], str]:
    """Genera arquetipos llamando a Claude con el prompt formateado."""
    if not reviews_sample:
        return "Error: No reviews provided to generate archetypes."

    reviews_formatted = "\n".join(f"- {review.strip()}" for review in reviews_sample)

    # El prompt largo proporcionado por el usuario
    prompt_template = f"""Generate 3 behavioral archetypes for the brand {brand_name}, based on brand knowledge and user opinions. Base this on the methodology of Adele Revelle and Forrester.

---
REVIEWS
{reviews_formatted}
---
EXPECTED RESULT (now to be delivered as structured JSON via tool use)

You must provide your response by calling the 'extract_customer_archetypes' tool.
Each archetype should have the following sections, as defined in the tool's schema:
- name
- general_description
- pain_points (list)
- fears_and_concerns (list)
- objections (list)
- goals_and_objectives (list)
- expected_benefits (list)
- values (list)
- social_behavior (text)
- influence_factors (list)
- internal_narrative (text)

GENERAL CONSTRUCTION CRITERIA from the original prompt still apply to the *content* of these fields:
All content must derive from observable data in UGC.
Insights must be actionable.
Avoid assumptions not supported by data.
Maintain consistency in the level of analysis.
Prioritize recurring patterns over isolated cases."""

    logger.info(f"Calling LLM API for brand '{brand_name}' with {len(reviews_sample)} reviews for structured archetype generation.")
    
    llm_response = ask_claude(prompt_template) # ask_claude now returns dict or error string

    if isinstance(llm_response, str) and llm_response.startswith("Error:"):
         logger.error(f"LLM API call failed for brand '{brand_name}': {llm_response}")
         return llm_response

    if not isinstance(llm_response, dict) or "archetypes" not in llm_response:
        logger.error(f"LLM response for brand '{brand_name}' was not a dict with 'archetypes' key. Response: {llm_response}")
        return "Error: Unexpected response structure from LLM."

    archetypes_list = llm_response.get("archetypes", [])
    
    processed_archetypes = []
    for i, arch_data in enumerate(archetypes_list):
        if not isinstance(arch_data, dict):
            logger.warning(f"Skipping an item in archetypes list as it's not a dictionary: {arch_data}")
            continue
            
        name_text = arch_data.get("name", f"Unnamed Archetype {i+1}")
        
        # Add id and avatar, similar to parse_archetype_text
        arch_data["id"] = f"archetype-{i+1}"
        name_seed = name_text.lower().replace(' ', '-')
        name_seed_encoded = urllib.parse.quote(name_seed)
        arch_data["avatar"] = f'https://api.dicebear.com/7.x/personas/svg?seed={name_seed_encoded}&backgroundColor=b7c7ff'
        
        # Ensure all required fields from the schema are present, even if empty lists/strings,
        # for consistency with how parse_archetype_text initializes them.
        # The LLM (if strictly following schema) should provide them, but this is a safeguard.
        arch_data.setdefault("description", arch_data.get("general_description", "")) # Map general_description to description
        if "general_description" in arch_data and "description" not in arch_data: # if LLM used general_description
             arch_data["description"] = arch_data.pop("general_description")

        list_fields = ["pain_points", "fears_and_concerns", "objections", "goals_and_objectives", "expected_benefits", "values", "influence_factors"]
        text_fields = ["social_behavior", "internal_narrative"]
        
        for field in list_fields:
            arch_data.setdefault(field, [])
        for field in text_fields:
            arch_data.setdefault(field, "")
        arch_data.setdefault("other_sections", {}) # Though less likely with structured output

        processed_archetypes.append(arch_data)

    logger.info(f"Successfully processed {len(processed_archetypes)} archetypes from LLM for brand '{brand_name}'.")
    return processed_archetypes

def save_generated_archetypes(brand_name: str, archetypes_data: List[Dict[str, Any]]):
    """Guarda los arquetipos generados en una colección específica de MongoDB."""
    client = get_mongo_client()
    if not client:
        # En una tarea de fondo, no podemos lanzar HTTPException. Logueamos el error.
        logger.error(f"Could not connect to MongoDB to save archetypes for brand {brand_name}.")
        return

    try:
        db = client[DB_NAME_ARCHETYPES]
        collection_name = f"archetypes_{brand_name.lower().replace(' ', '_')}"
        collection = db[collection_name]

        # Crear un documento que contenga la lista de arquetipos y metadatos
        archetype_document = {
            "brand_name": brand_name,
            "archetypes": archetypes_data,
            "created_at": datetime.utcnow(),
            "llm_model": "anthropic/claude-3.5-sonnet" # O el modelo que se usó
        }

        # Insertar el documento. Si ya existe, podrías decidir reemplazarlo o versionarlo.
        # Usar brand_name como _id puede ser una opción para asegurar un único doc por marca.
        # Por ahora, simplemente insertamos un nuevo documento cada vez.
        result = collection.insert_one(archetype_document)
        logger.info(f"Successfully saved archetypes for brand '{brand_name}' with document ID: {result.inserted_id}")

    except Exception as e:
        logger.error(f"Error saving archetypes to MongoDB for brand {brand_name}: {e}", exc_info=True)
    finally:
        client.close()

async def run_archetype_generation_background(task_id: str, brand_name: str, redis_pool: Optional[aioredis.Redis] = None):
    """
    Función de fondo para la generación de arquetipos.
    Esta función se ejecuta en un hilo separado por FastAPI's BackgroundTasks.
    """
    logger.info(f"Task [{task_id}] - Starting archetype generation process for brand: {brand_name}")
    try:
        # 1. Notificar al cliente que el proceso ha comenzado
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "starting", "message": "Archetype generation process initiated."})

        # 2. Obtener muestra de reseñas
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "fetching", "message": "Fetching review samples..."})
        
        # Esta es una operación de I/O bloqueante, ejecutar en un hilo separado
        reviews_sample = await asyncio.to_thread(fetch_review_sample, brand_name)

        if not reviews_sample:
            logger.warning(f"Task [{task_id}] - No reviews found for brand {brand_name}. Aborting archetype generation.")
            await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "failed", "error": "NoReviews", "message": "No reviews found for this brand to generate archetypes."})
            return
        
        logger.info(f"Task [{task_id}] - Fetched {len(reviews_sample)} reviews for brand {brand_name}.")
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "generating", "message": f"Generating archetypes from {len(reviews_sample)} reviews..."})

        # 3. Generar arquetipos (potencialmente I/O y CPU bound, usar to_thread)
        # Aquí llamamos a la función que usa la API de Claude/OpenAI
        archetypes_result = await asyncio.to_thread(generate_archetypes_from_reviews, brand_name, reviews_sample)

        # Verificar si la generación falló (ask_claude devuelve un string con "Error:" en caso de fallo)
        if isinstance(archetypes_result, str) and "Error:" in archetypes_result:
             error_message = f"LLM API call failed during archetype generation. Details: {archetypes_result}"
             logger.error(f"Task [{task_id}] - {error_message}")
             await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "failed", "error": "LLMError", "message": error_message})
             return
        
        # Si la respuesta no es una lista (inesperado si no es un error), tratar como fallo
        if not isinstance(archetypes_result, list):
            error_message = f"Unexpected response type from LLM generation: {type(archetypes_result)}"
            logger.error(f"Task [{task_id}] - {error_message}")
            await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "failed", "error": "LLMResponseFormatError", "message": error_message})
            return

        logger.info(f"Task [{task_id}] - Successfully generated {len(archetypes_result)} archetypes.")
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "saving", "message": "Saving generated archetypes..."})

        # 4. Guardar arquetipos en MongoDB (I/O bloqueante)
        await asyncio.to_thread(save_generated_archetypes, brand_name, archetypes_result)
        logger.info(f"Task [{task_id}] - Archetypes saved to MongoDB for brand {brand_name}.")

        # 5. Notificar finalización exitosa
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "completed", "message": "Archetype generation completed successfully.", "archetypes": archetypes_result})
        logger.info(f"Task [{task_id}] - Archetype generation process finished successfully for brand: {brand_name}")

    except Exception as e:
        logger.error(f"Task [{task_id}] - An unexpected error occurred during archetype generation for brand {brand_name}: {e}", exc_info=True)
        # Notificar al cliente sobre el fallo
        await sse_dispatch_event(redis_pool, task_id, "archetype_generation", {"status": "failed", "error": "ServerError", "message": f"An unexpected server error occurred: {str(e)}"})

def run_archetype_generation(brand_name: str) -> dict:
    """
    DEPRECATED or for direct/synchronous use if ever needed.
    The main flow for API endpoint now uses run_archetype_generation_background.
    This function remains for potential direct calls or testing but won't dispatch SSE.
    """
    logger.info(f"Starting SYNC archetype generation process for brand: {brand_name}")

    reviews_sample = fetch_review_sample(brand_name)
    if not reviews_sample:
        logger.warning(f"Could not generate archetypes for {brand_name} due to lack of reviews.")
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail=f"No reviews found for brand '{brand_name}' to generate archetypes.")

    archetype_result = generate_archetypes_from_reviews(brand_name, reviews_sample)

    if isinstance(archetype_result, str) and archetype_result.startswith("Error:"):
        status_code = 503 if "API call" in archetype_result or "LLM" in archetype_result else 500
        raise HTTPException(status_code=status_code, detail=archetype_result)
    
    if not isinstance(archetype_result, list):
        logger.error(f"Archetype generation for {brand_name} did not return a list of archetypes. Got: {type(archetype_result)}")
        raise HTTPException(status_code=500, detail="Archetype generation failed to produce expected structured data.")

    save_generated_archetypes(brand_name, archetype_result)

    logger.info(f"SYNC Archetype generation and saving completed successfully for brand: {brand_name}")
    return {"message": f"Archetypes generated and saved successfully for brand '{brand_name}'. (SYNC)"}

# --- NUEVAS FUNCIONES PARA LEER Y PARSEAR ARQUETIPOS --- 

def parse_archetype_text(raw_text: str) -> list[dict]:
    """Intenta parsear el texto crudo de arquetipos en una lista estructurada."""
    archetypes = []
    if not raw_text or raw_text.startswith("Error:"):
        logger.warning(f"Parsing skipped due to empty or error text: {raw_text[:100]}...")
        return []

    # 1. Eliminar texto introductorio conocido (si existe) - Mantenemos esto como primera línea de defensa
    intro_phrase = "Based on the methodology of Adele Revelle and Forrester, and analyzing the provided reviews, I\'ve generated 3 behavioral archetypes for the CeraVe brand:"
    if raw_text.startswith(intro_phrase):
        logger.debug("Removing known introductory phrase.")
        text_to_parse = raw_text[len(intro_phrase):].strip()
    else:
        text_to_parse = raw_text.strip()

    # 2. Dividir en bloques usando re.split (basado en la numeración)
    # El patrón busca un salto de línea, seguido de uno o más dígitos, un punto y espacio(s)
    blocks = re.split(r'\n\d+\.\s+', text_to_parse)

    # El primer elemento de split podría ser basura si el texto no empezaba directamente con \n1.
    # Lo filtraremos más adelante con la validación.

    logger.info(f"Found {len(blocks)} potential archetype blocks after split.")

    # Mapa de títulos esperados para validación (insensible a mayúsculas)
    expected_section_titles_lower = {
        "general description", "pain points", "fears and concerns", "objections",
        "goals and objectives", "expected benefits", "values", "social behavior",
        "influence factors", "internal narrative"
    }

    archetype_count = 0 # Contador para generar IDs correctos
    for index, block in enumerate(blocks):
        block = block.strip()
        if not block:
            logger.debug(f"Skipping empty block at index {index}.")
            continue # Saltar bloques vacíos

        logger.debug(f"--- Processing Block {index} (Potential Archetype {archetype_count + 1}) ---")
        logger.debug(f"Block content (start): {block[:150]}...")

        # 3. Extraer Nombre (primera línea del bloque)
        lines = block.split('\n', 1)
        name_text_raw = lines[0].strip() if lines else ""
        name_text = re.sub(r"^\d+\.\s*", "", name_text_raw).strip() # Limpiar posible numeración residual

        # 4. **VALIDACIÓN MEJORADA DEL BLOQUE**
        # Validación 4.a: ¿El nombre parece razonable? (No demasiado largo, no vacío)
        is_reasonable_name = bool(name_text) and len(name_text) < 100 # Ajusta el límite si es necesario
        if not is_reasonable_name:
             logger.warning(f"Block {index}: Skipping block due to unreasonable name: '{name_text_raw}'")
             continue

        # Validación 4.b: ¿Contiene al menos una sección esperada?
        content_after_name = lines[1].strip() if len(lines) > 1 else ""
        contains_expected_section = False
        if content_after_name:
             # Buscar títulos de sección al inicio de línea (case-insensitive)
             section_pattern_validation = re.compile(r"^[A-Z][a-zA-Z\s&/]+:", re.MULTILINE)
             found_titles = section_pattern_validation.findall(content_after_name)
             for title in found_titles:
                 if title.strip(':').strip().lower() in expected_section_titles_lower:
                     contains_expected_section = True
                     logger.debug(f"Block {index}: Found expected section title: '{title}'")
                     break # Encontramos una, suficiente para validar

        if not contains_expected_section:
             logger.warning(f"Block {index}: Skipping block '{name_text}'. No expected section titles found in content starting with: {content_after_name[:100]}...")
             continue

        # --- Si pasa las validaciones, proceder a parsear ---
        archetype_count += 1 # Incrementar contador de arquetipos válidos
        archetype_data = {
            "id": f"archetype-{archetype_count}", # Usar contador válido
            "name": name_text,
            "avatar": f'https://api.dicebear.com/7.x/personas/svg?seed=archetype{archetype_count}&backgroundColor=eeeeee',
            "description": "",
            "pain_points": [], "fears_concerns": [], "objections": [],
            "goals_objectives": [], "expected_benefits": [], "values": [],
            "social_behavior": "", "influence_factors": [], "internal_narrative": "",
            "other_sections": {}
        }
        
        logger.info(f"Block {index}: Identified as Archetype {archetype_count}: '{name_text}'")
        # Actualizar avatar con nombre real
        name_seed = name_text.lower().replace(' ', '-')
        name_seed_encoded = urllib.parse.quote(name_seed)
        archetype_data["avatar"] = f'https://api.dicebear.com/7.x/personas/svg?seed={name_seed_encoded}&backgroundColor=b7c7ff'


        # --- Extracción de Secciones (misma lógica que antes, aplicada a content_after_name) ---
        section_pattern = re.compile(r"^([A-Z][a-zA-Z\s&/]+):\s*(.*?)(?=(?:^[A-Z][a-zA-Z\s&/]+:)|\Z)", re.MULTILINE | re.DOTALL)
        current_sections = {}
        for section_match in section_pattern.finditer(content_after_name):
            title = section_match.group(1).strip()
            content = section_match.group(2).strip()
            current_sections[title] = content

        # Mapear contenido a claves estructuradas (mismo mapeo que antes)
        list_keys_map = {
             "Pain Points": "pain_points", "Fears and Concerns": "fears_concerns", "Objections": "objections",
             "Goals and Objectives": "goals_objectives", "Expected Benefits": "expected_benefits",
             "Values": "values", "Influence Factors": "influence_factors"
        }
        text_keys_map = {
             "General Description": "description", "Social Behavior": "social_behavior", "Internal Narrative": "internal_narrative"
        }

        for title, content in current_sections.items():
            found_match = False
            # Mapear a listas
            for map_title, map_key in list_keys_map.items():
                if title.lower() == map_title.lower():
                    points = [p.strip().lstrip('*- ').strip() for p in content.split('\n') if p.strip().lstrip('*- ').strip()]
                    archetype_data[map_key] = points
                    found_match = True
                    logger.debug(f"Block {index} ('{name_text}'): Mapped list section '{title}' to '{map_key}'")
                    break
            if found_match: continue

            # Mapear a texto
            for map_title, map_key in text_keys_map.items():
                 if title.lower() == map_title.lower():
                    archetype_data[map_key] = content
                    found_match = True
                    logger.debug(f"Block {index} ('{name_text}'): Mapped text section '{title}' to '{map_key}'")
                    break
            if found_match: continue

            # Secciones no mapeadas
            archetype_data["other_sections"][title] = content
            logger.debug(f"Block {index} ('{name_text}'): Section not mapped directly: '{title}'")

        # Log final de la descripción extraída
        extracted_description = archetype_data.get("description")
        if extracted_description:
             logger.debug(f"Block {index} ('{name_text}'): Final extracted description (start): {extracted_description[:50]}...")
        else:
             logger.warning(f"Block {index} ('{name_text}'): Could not extract description.")

        archetypes.append(archetype_data)
        logger.debug(f"--- Finished Processing Block {index} (Archetype {archetype_count}) ---")

    logger.info(f"Finished parsing. Total valid archetypes extracted: {len(archetypes)}.")
    return archetypes

def fetch_archetypes_from_db(brand_name: str) -> list[dict]:
    """Obtiene y parsea los arquetipos ACTIVOS generados para una marca desde MongoDB."""
    client = get_mongo_client()
    if not client:
        logger.error("fetch_archetypes_from_db: Database connection unavailable")
        return []

    try:
        db = client[DB_NAME_ARCHETYPES]
        collection_name = f"{brand_name.lower().replace(' ', '_')}_archetype"
        collection = db[collection_name]

        # Modificar la consulta para buscar solo el documento activo
        document = collection.find_one({"brand_name": brand_name, "is_active": True})

        if document:
            # Prioritize new structured data
            if "archetype_data" in document and isinstance(document["archetype_data"], list):
                logger.info(f"Found active structured archetype data for brand '{brand_name}' in DB.")
                # Ensure id and avatar are present if they were missed during save somehow
                # (though generate_archetypes_from_reviews should add them)
                processed_list = []
                for i, arch in enumerate(document["archetype_data"]):
                    if isinstance(arch, dict):
                        arch.setdefault("id", f"archetype-{i+1}")
                        name_seed = arch.get("name", f"arch{i+1}").lower().replace(' ', '-')
                        name_seed_encoded = urllib.parse.quote(name_seed)
                        arch.setdefault("avatar", f'https://api.dicebear.com/7.x/personas/svg?seed={name_seed_encoded}&backgroundColor=b7c7ff')
                        processed_list.append(arch)
                return processed_list
            
            # Fallback to old raw text data (ESTO DEBERÍA SER REVISADO - si usamos is_active, el texto generado también debería tenerlo)
            # Por ahora, asumimos que si hay 'generated_text' en un doc activo, es el que se debe parsear.
            # Lo ideal sería que 'generated_text' también estuviera bajo el paraguas de 'is_active'.
            elif "generated_text" in document and document["generated_text"]:
                logger.info(f"Found raw generated_text in active document for brand '{brand_name}'. Parsing with legacy parser...")
                parsed_data = parse_archetype_text(document["generated_text"])
                logger.info(f"Parsed {len(parsed_data)} archetypes from raw text for brand '{brand_name}'.")
                return parsed_data # Devolver el resultado del parseo directamente
            else:
                logger.warning(f"Active document found for brand '{brand_name}' but no 'archetype_data' (list) or 'generated_text' (string) field found.")
                return []
        else:
            logger.warning(f"No active archetype document found for brand '{brand_name}' in DB '{DB_NAME_ARCHETYPES}', collection '{collection_name}'.")
            return []

    except Exception as e:
        logger.error(f"Error fetching or parsing active archetypes from MongoDB for brand {brand_name}: {e}", exc_info=True)
        return []
    finally:
        if client:
            client.close()

# --- FIN NUEVAS FUNCIONES --- 

# --- NUEVA FUNCIÓN --- 
def fetch_single_archetype_details(brand_name: str, archetype_identifier: str) -> Optional[dict]:
    """Busca y devuelve los detalles de un arquetipo específico por ID o nombre."""
    # Obtener la lista completa de arquetipos parseados para la marca
    all_archetypes = fetch_archetypes_from_db(brand_name)
    if not all_archetypes:
        logger.warning(f"No archetypes list found for brand '{brand_name}' when searching for '{archetype_identifier}'")
        return None

    # Buscar el arquetipo por ID o por Nombre (case-insensitive)
    for archetype in all_archetypes:
        # Comprobar ID (si existe en los datos parseados)
        if archetype.get('id') == archetype_identifier:
            logger.info(f"Found archetype for brand '{brand_name}' by ID: '{archetype_identifier}'")
            return archetype
        # Comprobar Nombre (comparación insensible a mayúsculas)
        if archetype.get('name') and archetype.get('name').lower() == archetype_identifier.lower():
            logger.info(f"Found archetype for brand '{brand_name}' by Name: '{archetype_identifier}'")
            return archetype
        # Fallback: comprobar nombre normalizado si el ID no es estándar
        if archetype.get('name') and archetype.get('name').lower().replace(' ', '-') == archetype_identifier.lower():
            logger.info(f"Found archetype for brand '{brand_name}' by normalized name: '{archetype_identifier}'")
            return archetype


    logger.warning(f"Archetype with identifier '{archetype_identifier}' not found in the parsed list for brand '{brand_name}'")
    return None

# --- FIN NUEVA FUNCIÓN ---
