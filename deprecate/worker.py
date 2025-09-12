import asyncio
import os
import logging
import sys
from typing import Dict, Any, Optional, List, Tuple
from dotenv import load_dotenv
import arq
from arq import func
import aiohttp
import re
from scrapers.main_trustpilot import reviews_trustpilot as trustpilot_scraper
from scrapers.main_tripadvisor import reviews_tripadvisor as tripadvisor_scraper
from scrapers.main_druni import reviews_druni as druni_scraper
from scrapers.main_google import search_google_places_detailed
from scrapers.main_google import reviews_google as google_reviews_scraper
from helper.utilsdb import update_job_status_mysql
from helper.sse_utils import sse_dispatch_event
from models import SourceData
import redis.asyncio as aioredis
import motor.motor_asyncio
import uuid
from gold.clean_amazon import separate_urls_and_asins, clean_amazon_reviews
# Import brightdata handlers
from scrapers.brightdata_amazon_handler import (
    trigger_amazon_keyword_discovery,
    trigger_manual_product_lookup,
    get_snapshot_results,
    trigger_amazon_reviews_scrape,
    AMAZON_DOMAINS
)
from auth import get_marca_name_by_id

from helper.utilsdb import save_discovered_product_in_db, fetch_discovered_product_by_title

# Configure logging for the entire worker process
# This setup ensures that logs from all modules will be captured.
log_formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log_handler = logging.StreamHandler(sys.stdout)
log_handler.setFormatter(log_formatter)
root_logger = logging.getLogger()
# Set the root logger level. You can set this to DEBUG for more verbose output.
root_logger.setLevel(logging.INFO)
# Avoid adding handlers multiple times in case of reloads
if not root_logger.handlers:
    root_logger.addHandler(log_handler)

logger = logging.getLogger(__name__)


# Load env vars for the worker
dotenv_path = os.path.join(os.path.dirname(__file__), '..', '.env')
load_dotenv(dotenv_path=dotenv_path)

# Important: We need to import the functions we want to run as tasks
# from main import check_and_finalize_job # Yes, we can even make our finalizer a task!

# This should point to your Redis instance from environment variables
REDIS_URL = os.getenv("REDIS_URL", "redis://localhost:6379")
# We need to create a pool for sse_dispatch_event, as ctx['redis'] is for arq commands
_redis_pool = None 

# Define the key for the SSE Redis pool in the context
SSE_REDIS_CONNECTION_KEY = "sse_redis_pool"

# --- Constants for Outscraper API retry logic ---
MAX_RETRIES_INITIAL = 3
MAX_RETRIES_POLLING = 15
BASE_RETRY_SECONDS = 2
MAX_RETRY_SECONDS = 60

async def startup(ctx: Dict[str, Any]):
    """
    Initializes resources for the worker when it starts up.
    This is where we'll create our Redis connection pool.
    """
    global _redis_pool
    logger.info("ARQ worker is starting up...")
    redis_url = os.getenv("REDIS_URL", "redis://localhost:6379")
    try:
        # Create a standard Redis pool for SSE and other non-ARQ tasks
        sse_redis_pool = aioredis.from_url(redis_url, encoding="utf-8", decode_responses=True)
        await sse_redis_pool.ping()
        ctx[SSE_REDIS_CONNECTION_KEY] = sse_redis_pool
        _redis_pool = sse_redis_pool
        logger.info(f"Successfully connected standard Redis pool for SSE in worker. Stored in context with key '{SSE_REDIS_CONNECTION_KEY}'.")

    except Exception as e:
        logger.error(f"Error during worker startup while creating Redis pools: {e}", exc_info=True)
        ctx[SSE_REDIS_CONNECTION_KEY] = None
        _redis_pool = None

async def shutdown(ctx: Dict[str, Any]):
    """
    Cleans up resources when the worker shuts down.
    """
    global _redis_pool
    logger.info("ARQ worker is shutting down...")
    if _redis_pool:
        await _redis_pool.close()
        logger.info("Closed standard Redis pool for SSE in worker.")
    # ARQ handles its own pool closure.

# --- Task Definitions ---

async def discover_druni_urls(product_name: str) -> List[str]:
    """
    Searches Google for a product on druni.es using the Outscraper API.
    """
    search_query = f"site:druni.es {product_name}"
    logger.info(f"Discovering Druni URL with query: '{search_query}'")

    base_url = "https://api.app.outscraper.com"
    search_endpoint = f"{base_url}/google-search-v3"
    params = {
        "query": search_query,
        "limit": 3,
        "async": "true",
        "language": "es"
    }
    headers = {"X-API-KEY": os.getenv("OUTSCRAPER_API_KEY")}
    
    async with aiohttp.ClientSession() as session:
        for attempt in range(MAX_RETRIES_INITIAL):
            try:
                async with session.get(search_endpoint, params=params, headers=headers, timeout=30) as response:
                    if response.status not in [200, 202]:
                        logger.error(f"Outscraper initial request failed with status {response.status}")
                        continue
                    
                    data = await response.json()
                    results_url = data.get('results_location')

                    if not results_url:
                        logger.warning("Outscraper did not return a results_location URL.")
                        continue

                    # Poll for results
                    for poll_attempt in range(MAX_RETRIES_POLLING):
                        await asyncio.sleep(BASE_RETRY_SECONDS)
                        async with session.get(results_url, headers=headers, timeout=45) as poll_response:
                            results_data = await poll_response.json()
                            if poll_response.status == 200 and results_data.get('status') == 'Success':
                                if results_data and 'data' in results_data and results_data['data']:
                                    google_results = results_data['data'][0].get('organic_results', [])
                                    # Filter for valid Druni URLs
                                    druni_urls = [
                                        res.get('link') for res in google_results
                                        if res.get('link') and 'druni.es' in res.get('link') and '/marcas/' not in res.get('link')
                                    ]
                                    return druni_urls[:1] # Return the first valid product page URL
                    logger.warning(f"Polling for Druni URL timed out for query: {search_query}")
            except Exception as e:
                logger.error(f"Error during Druni URL discovery (attempt {attempt + 1}): {e}", exc_info=True)
                await asyncio.sleep(BASE_RETRY_SECONDS)
    return []

async def scrape_druni_task(ctx, job_id: str, source_data: dict, user_id: str, brand_name: str):
    """
    ARQ task to scrape Druni reviews.
    If an identifier is not a URL, it searches Google to find the Druni product page.
    """
    source_type = "druni"
    logger.info(f"[{job_id}] ARQ task '{source_type}' started.")

    identifiers_str = source_data.get("brand_name", "")
    # Treat the entire string as a single identifier, as product names can contain commas.
    identifiers = [i.strip() for i in identifiers_str.split('\n') if i.strip()]
    limit = source_data.get("number_of_reviews", 500)

    urls_to_scrape = []
    source_result = {}
    
    mongo_uri = os.getenv("MONGODB_URI")
    db_name = os.getenv("MONGO_DB_NAME")
    mongo_client = None

    try:
        mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
        db = mongo_client[db_name]

        for identifier in identifiers:
            # The 'identifier' from the job is the product title. We use it to find the document.
            product_doc = await fetch_discovered_product_by_title(db, identifier, brand_name)
            druni_url = product_doc.get("druni_url") if product_doc else None

            if druni_url:
                logger.info(f"[{job_id}] Found existing Druni URL for product '{identifier[:50]}...': {druni_url}")
                urls_to_scrape.append(druni_url)
            elif "druni.es" in identifier and identifier.startswith("http"):
                urls_to_scrape.append(identifier)
            else:
                # Truncate the product name for a more effective Google search query.
                product_name_for_search = ','.join(identifier.split(',')[:2])
                logger.info(f"[{job_id}] Druni URL not provided for '{identifier[:50]}...'. Searching with name: '{product_name_for_search}'.")
                
                discovered_urls = await discover_druni_urls(product_name_for_search)
                
                if discovered_urls:
                    new_druni_url = discovered_urls[0]
                    logger.info(f"[{job_id}] Discovered Druni URL for '{product_name_for_search}': {new_druni_url}")
                    urls_to_scrape.append(new_druni_url)

                    if product_doc:
                        product_doc['druni_url'] = new_druni_url
                        # save_discovered_product_in_db uses the 'identifier' (ASIN) from the doc to update, which is reliable.
                        await save_discovered_product_in_db(db, product_doc, brand_name, int(user_id))
                        logger.info(f"[{job_id}] Updated product document for '{identifier[:50]}...' with new Druni URL.")
                    else:
                        logger.warning(f"[{job_id}] Scraped Druni URL for '{identifier[:50]}...' but could not find a matching product document by title to update.")

                else:
                    logger.warning(f"[{job_id}] Could not find a Druni URL for '{product_name_for_search}' via Google search.")

        if not urls_to_scrape:
            logger.warning(f"[{job_id}] No Druni URLs to scrape after discovery phase. Task will be marked as complete.")
            source_result = {"status": "success", "message": "No URLs found to scrape."}
        else:
            final_urls_str = ",".join(list(set(urls_to_scrape))) # Use unique URLs
            s3_paths_for_source = {}
            
            await druni_scraper(
                urls=final_urls_str,
                limit=limit,
                regions=[],
                audit_id=job_id,
                s3_paths=s3_paths_for_source,
                user_id=int(user_id),
                actual_brand_name=brand_name
            )

            final_s3_path = s3_paths_for_source.get(source_type)
            source_result = {
                "status": "success",
                "source_type": source_type,
                "s3_path": final_s3_path
            }
            logger.info(f"[{job_id}] Task '{source_type}' completed successfully. S3 Path: {final_s3_path}")

    except Exception as e:
        logger.error(f"[{job_id}] Task '{source_type}' failed with error: {e}", exc_info=True)
        source_result = {"error": str(e)}
        update_job_status_mysql(job_id, 'failed', f"Druni scraping failed: {e}", int(user_id))
    finally:
        if mongo_client:
            mongo_client.close()

    await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, source_result)

async def scrape_trustpilot_task(ctx, job_id: str, source_data: dict, user_id: str, brand_name: str):
    """
    ARQ task to scrape Trustpilot reviews.
    """
    source_type = "trustpilot"
    logger.info(f"[{job_id}] ARQ task '{source_type}' started.")

    search_input = source_data.get("brand_name", "").split(',')[0].strip()
    limit = source_data.get("number_of_reviews", 100)
    regions = source_data.get("regions", [])
    region = regions[0] if regions else ""

    s3_paths_for_source = {}
    source_result = {}
    try:
        # The scraper function is async and modifies s3_paths_for_source in-place
        await trustpilot_scraper(
            search_input=search_input,
            limit=limit,
            region=region,
            job_id=job_id,
            s3_paths=s3_paths_for_source,
            user_id=int(user_id),
            actual_brand_name=brand_name,
        )

        # The key is generated inside the scraper as f"trustpilot_{region}"
        s3_path_key = f"{source_type}_{region}"
        final_s3_path = s3_paths_for_source.get(s3_path_key)

        source_result = {
            "status": "success",
            "source_type": source_type,
            "s3_path": final_s3_path
        }
        logger.info(f"[{job_id}] Task '{source_type}' completed successfully. Result: {source_result}")

    except Exception as e:
        logger.error(f"[{job_id}] Task '{source_type}' failed with error: {e}", exc_info=True)
        source_result = {"error": str(e)}
        update_job_status_mysql(job_id, 'failed', f"Trustpilot scraping failed: {e}", int(user_id))

    # Enqueue the finalization task, which checks if all sources for the job are done
    await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, source_result)

async def scrape_tripadvisor_task(ctx, job_id: str, source_data: dict, user_id: str, brand_name: str):
    """
    ARQ task to scrape TripAdvisor reviews.
    """
    source_type = "tripadvisor"
    logger.info(f"[{job_id}] ARQ task '{source_type}' started.")
    
    query = source_data.get("brand_name")
    limit = source_data.get("number_of_reviews", 5) # Default to 5 if not provided

    source_result = {}
    try:
        # Assuming reviews_tripadvisor is async and returns a dict with results (e.g., S3 path)
        source_result = await tripadvisor_scraper(
            query=query,
            limit=limit,
            job_id=job_id,
            user_id=int(user_id),
            actual_brand_name=brand_name
        )
        logger.info(f"[{job_id}] Task '{source_type}' completed successfully. Result: {source_result}")
    except Exception as e:
        logger.error(f"[{job_id}] Task '{source_type}' failed with error: {e}", exc_info=True)
        source_result = {"error": str(e)}
        # Optionally update job status in MySQL to reflect task-specific failure
        update_job_status_mysql(job_id, 'failed', f"TripAdvisor scraping failed: {e}", int(user_id))
    
    # Enqueue the finalization task
    await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, source_result)

async def process_amazon_reviews_webhook_task(ctx, snapshot_id: str, payload_data: dict):
    """
    Worker task to process the completed Amazon reviews scrape from Bright Data.
    """
    logger.info(f"Worker processing amazon-reviews-complete webhook for snapshot_id: {snapshot_id}")
    
    if not _redis_pool:
        logger.error(f"[{snapshot_id}] Cannot process webhook task. Redis pool is not available.")
        return

    job_details = await _redis_pool.hgetall(f"snapshot_to_job:{snapshot_id}")
    if not job_details:
        logger.error(f"No job details found in Redis for amazon-reviews snapshot {snapshot_id}. Cannot proceed (job may have expired).")
        return

    job_id = job_details.get('job_id')
    source_type = job_details.get('source_type', 'amazon')
    brand_name = job_details.get("brand_name", "UnknownBrand")
    logger.info(f"Retrieved job details from Redis. Job ID: {job_id}, Brand: {brand_name}")
    
    payload_status = payload_data.get("status")

    if payload_status == "failed":
        logger.error(f"Amazon reviews scrape FAILED for snapshot {snapshot_id} (Job ID: {job_id})")
        source_result = {"error": "Bright Data reported a failure for the scraping job."}
        await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, source_result)
        await _redis_pool.delete(f"snapshot_to_job:{snapshot_id}")
        return

    if payload_status != "ready":
        logger.info(f"Webhook for snapshot {snapshot_id} has status '{payload_status}', not 'ready'. Ignoring.")
        return

    mongo_client = None
    try:
        logger.info(f"Fetching review data for snapshot {snapshot_id} directly from Bright Data.")
        scraped_data = await asyncio.to_thread(get_snapshot_results, snapshot_id)

        if scraped_data is None:
            raise Exception(f"Failed to retrieve results for snapshot {snapshot_id}")
        
        logger.info(f"Successfully fetched {len(scraped_data)} review records for snapshot {snapshot_id}")

        cleaned_reviews = await clean_amazon_reviews(scraped_data, brand_name, job_id)
        inserted_count = 0
        if cleaned_reviews:
            mongo_uri = os.getenv("MONGODB_URI")
            db_name = os.getenv("MONGO_DB_NAME")
            mongo_client = motor.motor_asyncio.AsyncIOMotorClient(mongo_uri)
            db = mongo_client[db_name]
            amazon_collection = db["reviews_amazon_gold"]
            result = await amazon_collection.insert_many(cleaned_reviews)
            inserted_count = len(result.inserted_ids)
            logger.info(f"Successfully inserted {inserted_count} cleaned Amazon reviews for job {job_id}.")
        else:
            logger.info(f"No valid reviews to insert after cleaning for job {job_id}.")

        source_result = {"source": source_type, "status": "completed", "inserted_count": inserted_count}
        await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, source_result)

    except Exception as e:
        logger.error(f"Error processing amazon-reviews webhook task for snapshot {snapshot_id}: {e}", exc_info=True)
        await ctx['redis'].enqueue_job('check_and_finalize_job_task', job_id, source_type, {"error": str(e)})
    finally:
        if mongo_client:
            mongo_client.close()
        await _redis_pool.delete(f"snapshot_to_job:{snapshot_id}")
        logger.info(f"Cleaned up Redis key for snapshot {snapshot_id}.")

async def scrape_google_task(ctx, job_id: str, source_data: dict, user_id: str, brand_name: str):
    """
    ARQ task to scrape Google reviews.
    """
    source_type = "google"
    logger.info(f"[{job_id}] Received task: '{source_type}' for brand '{brand_name}'. Starting...")
    
    redis_pool = ctx.get(SSE_REDIS_CONNECTION_KEY)
    if not redis_pool:
        logger.error(f"[{job_id}] Could not find '{SSE_REDIS_CONNECTION_KEY}' in worker context. Cannot dispatch SSE events.")

    # Optional: send an initial event from the worker itself
    await sse_dispatch_event(redis_pool, job_id, "scrape_tracking", data={
        "status": "progress", "source_type": source_type, "job_id": job_id,
        "message": f"Google: Worker task received. Initializing scrape..."
    })

    result_payload = {}
    try:
        # The reviews_google function from main_google.py handles all logic including
        # SSE dispatches, DB updates, and S3 saving.
        s3_paths_for_source = {}
        
        # Use brand_name as a fallback if the source-specific query is missing
        query_to_use = source_data.get('brand_name') or brand_name
        
        # Check for a specific list of places provided by the frontend
        places_to_scrape = source_data.get("places")

        await google_reviews_scraper(
            redis_pool=redis_pool,
            query=query_to_use,
            limit=int(source_data.get('limit', 100)),
            regions=source_data.get('regions', []),
            places=places_to_scrape,  # Pass the specific places to the scraper
            job_id=job_id,
            s3_paths=s3_paths_for_source,
            user_id=int(user_id),
            actual_brand_name=brand_name
        )

        final_s3_path = s3_paths_for_source.get(source_type)
        
        result_payload = {
            "status": "success",
            "source_type": source_type,
            "s3_path": final_s3_path
        }
        logger.info(f"[{job_id}] Google scraping finished. Result payload: {result_payload}")

    except Exception as e:
        error_message = f"Critical error in '{source_type}' task: {e}"
        logger.error(f"[{job_id}] {error_message}", exc_info=True)
        result_payload = {"status": "error", "source_type": source_type, "message": str(e)}
        await sse_dispatch_event(redis_pool, job_id, "scrape_tracking", data={
            "status": "error", "source_type": source_type, "job_id": job_id,
            "message": f"Google: Worker task failed. Error: {str(e)[:100]}..."
        })

    logger.info(f"[{job_id}] Enqueuing finalization task for source '{source_type}'.")
    redis = ctx.get('redis')
    if redis:
        await redis.enqueue_job('check_and_finalize_job_task', job_id, source_type, result_payload)
    else:
        logger.error(f"[{job_id}] Could not enqueue finalization task. ARQ Redis client not found in context.")

async def search_google_places_task(ctx, task_id: str, brand_name_or_query: str, countries: list, selected_provinces: list):
    """
    ARQ task to search for Google Places.
    """
    logger.info(f"[{task_id}] ARQ task 'search_google_places_task' started for query: '{brand_name_or_query}'.")

    if not _redis_pool:
        logger.error(f"[{task_id}] Cannot dispatch results. Redis pool for SSE is not available.")
        return

    # To fix a race condition, we wait until the client has subscribed to the SSE channel
    # before sending the first event. We'll poll for a subscriber for a few seconds.
    subscriber_found = False
    redis_channel = f"sse:{task_id}"
    logger.info(f"[{task_id}] Checking for SSE subscribers on channel '{redis_channel}'...")
    for _ in range(10):  # Poll for up to 5 seconds (10 * 0.5s)
        try:
            # PUBSUB NUMSUB returns a list of tuples: [(channel, count)]
            num_subscribers_tuple = await _redis_pool.pubsub_numsub(redis_channel)
            if num_subscribers_tuple and num_subscribers_tuple[0][1] > 0:
                logger.info(f"[{task_id}] SSE subscriber found. Proceeding with task.")
                subscriber_found = True
                break
        except Exception as e:
            logger.error(f"[{task_id}] Error checking for SSE subscribers: {e}", exc_info=True)
            break # Exit loop on error
        await asyncio.sleep(0.5)

    if not subscriber_found:
        logger.warning(f"[{task_id}] No SSE subscriber connected after waiting. The 'processing' message may be missed by the client.")

    try:
        await sse_dispatch_event(_redis_pool, task_id, "google_places_discovery", {
            "status": "processing",
            "message": f"Searching Google Places for: {brand_name_or_query}",
        })

        results = await search_google_places_detailed(
            brand_name_or_query=brand_name_or_query,
            target_country_codes=countries,
            target_provinces_from_req=selected_provinces
        )
        logger.info(f"[{task_id}] Google Places search completed. Found {len(results)} places.")

        await sse_dispatch_event(_redis_pool, task_id, "google_places_discovery", {
            "status": "completed",
            "message": f"Found {len(results)} places.",
            "results": results
        })

    except Exception as e:
        logger.error(f"[{task_id}] Task 'search_google_places_task' failed with error: {e}", exc_info=True)
        await sse_dispatch_event(_redis_pool, task_id, "google_places_discovery", {
            "status": "failed",
            "message": str(e),
            "error": str(e)
        })

async def check_and_finalize_job_task(ctx, job_id: str, source_type: str, source_result: dict):
    """
    This task is enqueued by other scraper tasks. It checks the overall job progress in Redis.
    """
    logger.info(f"[{job_id}] Finalization task running for source '{source_type}'.")
    # This task doesn't perform scraping, it just coordinates.
    # We need to implement the logic from main.py's `check_and_finalize_job` here,
    # but callable from a worker.
    
    # The original `check_and_finalize_job` uses a redis_pool. The worker has one.
    redis_pool = ctx['redis'] # This is an arq.ArqRedis, we might need a standard aioredis pool.
    
    # Let's reuse the logic from main.py `check_and_finalize_job`
    # We'll need access to a standard redis pool for HGETALL etc.
    # For now, let's assume `check_and_finalize_job` can be imported and used.
    # Note: It seems the original `check_and_finalize_job` is what we should call,
    # but it is not easily callable from worker.py. Let's make this one simpler.
    
    # The logic from `main.py` is needed here. Let's adapt it.
    if not _redis_pool:
        logger.error(f"[{job_id}] Cannot check job completion from worker. Redis pool for SSE is not available.")
        return

    try:
        job_data = await _redis_pool.hgetall(f"job:{job_id}")
        if not job_data:
            logger.warning(f"[{job_id}] No job data in Redis for completion check. Source '{source_type}' done.")
            return
            
        total_sources = int(job_data.get("total_sources", 0))

        async with _redis_pool.pipeline() as pipe:
            pipe.hincrby(f"job:{job_id}", "completed_count", 1)
            import json
            pipe.hset(f"job:{job_id}:results", source_type, json.dumps(source_result))
            await pipe.execute()
        
        completed_count = int(await _redis_pool.hget(f"job:{job_id}", "completed_count"))
        logger.info(f"[{job_id}] Source '{source_type}' completed. Progress: {completed_count}/{total_sources}.")

        await sse_dispatch_event(_redis_pool, job_id, "scrape_tracking", {
            "status": "source_complete", "source_type": source_type,
            "message": f"Source '{source_type}' finished.",
            "processed_sources": completed_count, "total_sources_to_track": total_sources
        })

        if total_sources > 0 and completed_count >= total_sources:
            logger.info(f"[{job_id}] All sources completed. Finalizing job.")
            all_results_raw = await _redis_pool.hgetall(f"job:{job_id}:results")
            all_results = {k: json.loads(v) for k, v in all_results_raw.items()}

            await sse_dispatch_event(_redis_pool, job_id, "scrape_tracking", {
                "status": "completed", "message": "All sources have completed.", "s3_paths": all_results,
                "processed_sources": completed_count, "total_sources_to_track": total_sources
            })
            await _redis_pool.delete(f"job:{job_id}", f"job:{job_id}:results")
            logger.info(f"[{job_id}] Cleaned up Redis keys for completed job.")
            
    except Exception as e:
        logger.error(f"[{job_id}] Error in worker's check_and_finalize_job_task for source '{source_type}': {e}", exc_info=True)

async def trigger_amazon_keyword_discovery_task(ctx, task_id: str, brand_name: str, country: str):
    """
    ARQ task to trigger Bright Data Amazon product discovery by keyword.
    """
    logger.info(f"[{task_id}] Worker task started: Amazon keyword discovery for '{brand_name}' in '{country}'.")
    redis_pool = ctx.get(SSE_REDIS_CONNECTION_KEY)
    if not redis_pool:
        logger.error(f"[{task_id}] Cannot proceed: Redis pool for SSE is not available in worker context.")
        return

    # Add delay to give frontend time to subscribe to SSE
    await asyncio.sleep(1.0)

    try:
        # Construct webhook URL
        app_base_url = os.getenv("APP_BASE_URL")
        webhook_secret = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")
        if not app_base_url or not webhook_secret:
            raise ValueError("APP_BASE_URL or BRIGHTDATA_WEBHOOK_SECRET is not configured.")

        webhook_url = f"{app_base_url.rstrip('/')}/api/webhooks/brightdata/amazon-discovery-complete"
        webhook_auth = f"Bearer {webhook_secret}"

        # Dispatch initial SSE event
        await sse_dispatch_event(redis_pool, task_id, "amazon_discovery_update", {
            "status": "processing",
            "message": f"Worker is triggering Bright Data for brand '{brand_name}'...",
        })
        
        # Trigger Bright Data API
        snapshot_id = trigger_amazon_keyword_discovery(brand_name, country, webhook_url, webhook_auth)

        if snapshot_id:
            logger.info(f"[{task_id}] Successfully triggered Bright Data. Snapshot ID: {snapshot_id}")
            # Map our task_id to the snapshot_id from Bright Data for webhook lookup
            await redis_pool.set(f"snapshot_to_task:{snapshot_id}", task_id, ex=86400) # 24hr expiry
            await sse_dispatch_event(redis_pool, task_id, "amazon_discovery_update", {
                "status": "triggered",
                "message": "Discovery initiated with Bright Data. Waiting for results...",
                "snapshot_id": snapshot_id
            })
        else:
            raise Exception("Failed to get snapshot_id from Bright Data.")

    except Exception as e:
        logger.error(f"[{task_id}] Amazon keyword discovery task failed: {e}", exc_info=True)
        await sse_dispatch_event(redis_pool, task_id, "amazon_discovery_update", {
            "status": "failed",
            "message": f"Error initiating discovery: {str(e)}"
        })

async def trigger_manual_product_lookup_task(ctx, task_id: str, identifiers: List[str], country: str, user_id: str):
    """
    ARQ task to trigger Bright Data manual product lookup.
    """
    logger.info(f"[{task_id}] Worker task started: Manual product lookup for {len(identifiers)} items in '{country}'.")
    redis_pool = ctx.get(SSE_REDIS_CONNECTION_KEY)
    if not redis_pool:
        logger.error(f"[{task_id}] Cannot proceed: Redis pool is not available.")
        return
        
    # Add delay to give frontend time to subscribe to SSE
    await asyncio.sleep(1.0)
        
    try:
        brand_name = get_marca_name_by_id(int(user_id))
        if not brand_name:
            raise ValueError(f"Could not find brand name for user_id {user_id}")

        await sse_dispatch_event(redis_pool, task_id, "manual_lookup_discovery", {
            "status": "processing", "message": "Worker is preparing to trigger lookup..."
        })
        
        # Store job metadata in Redis before triggering
        await redis_pool.hset(f"manual_lookup_job:{task_id}", mapping={
            "user_id": user_id,
            "brand_name": brand_name,
            "country": country,
            "identifier_count": len(identifiers)
        })

        app_base_url = os.getenv("APP_BASE_URL")
        webhook_secret = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")
        if not app_base_url or not webhook_secret:
            raise ValueError("Server configuration for webhooks is incomplete.")

        webhook_url = f"{app_base_url.rstrip('/')}/api/webhooks/brightdata/manual-lookup-complete"
        webhook_auth = f"Bearer {webhook_secret}"

        snapshot_id = trigger_manual_product_lookup(
            product_urls=identifiers, # The handler can take ASINs or URLs
            webhook_url=webhook_url,
            webhook_auth_header_value=webhook_auth
        )

        if snapshot_id:
            logger.info(f"[{task_id}] Triggered manual lookup. Snapshot ID: {snapshot_id}")
            await redis_pool.set(f"snapshot_to_task:{snapshot_id}", task_id, ex=86400) # Map snapshot to our task ID
            await sse_dispatch_event(redis_pool, task_id, "manual_lookup_discovery", {
                "status": "triggered", "message": "Lookup sent to provider. Waiting for completion webhook...", "snapshot_id": snapshot_id
            })
        else:
            raise Exception("Failed to trigger manual product lookup with Bright Data.")

    except Exception as e:
        logger.error(f"[{task_id}] Manual product lookup task failed: {e}", exc_info=True)
        await sse_dispatch_event(redis_pool, task_id, "manual_lookup_discovery", {
            "status": "failed", "message": f"Error initiating manual lookup: {str(e)}"
        })

async def scrape_amazon_task(ctx, job_id: str, source_data: dict, user_id: str, brand_name: str):
    """
    Triggers a Bright Data collector for Amazon reviews based on a list of ASINs or URLs.
    This task does not scrape directly but initiates the process. The results
    will be handled by a webhook that calls back to our API.
    """
    logger.info(f"[{job_id}] Starting Amazon reviews scraping task.")
    
    redis = ctx.get("redis")
    if not redis:
        logger.error(f"[{job_id}] No Redis connection available for Amazon task. Aborting.")
        # We need Redis to track the job, so we should fail gracefully if it's not there.
        # This will be caught by the finalization task logic.
        return

    # The old DB check is removed from here.

    identifiers_str = source_data.get("brand_name", "")
    if not identifiers_str:
        logger.warning(f"[{job_id}] No identifiers provided for Amazon task. Nothing to scrape.")
        await check_and_finalize_job_task(ctx, job_id, "amazon", {"status": "completed_empty"})
        return

    urls, asins = separate_urls_and_asins(identifiers_str)
    logger.info(f"[{job_id}] Found {len(urls)} URLs and {len(asins)} ASINs for Amazon scraping.")

    country_code = "com"
    countries = source_data.get("countries", [])
    if countries:
        country_iso = countries[0].lower()
        if country_iso in AMAZON_DOMAINS:
            country_code = AMAZON_DOMAINS[country_iso]
        else:
            logger.warning(f"[{job_id}] Unsupported country '{country_iso}' for Amazon. Defaulting to .com domain.")

    final_urls = list(urls)
    for asin in asins:
        final_urls.append(f"https://www.amazon.{country_code}/dp/{asin}")

    if not final_urls:
        logger.warning(f"[{job_id}] No valid URLs or ASINs to scrape for Amazon.")
        await check_and_finalize_job_task(ctx, job_id, "amazon", {"status": "skipped", "message": "No valid identifiers."})
        return

    webhook_base_url = os.getenv("APP_BASE_URL")
    if not webhook_base_url:
        raise Exception("Server configuration error: APP_BASE_URL is not set.")

    webhook_url = f"{webhook_base_url}/api/webhooks/brightdata/amazon-reviews-complete"
    webhook_secret = os.getenv("BRIGHTDATA_WEBHOOK_SECRET")
    webhook_auth = f"Bearer {webhook_secret}"

    snapshot_id = trigger_amazon_reviews_scrape(
        product_urls=final_urls,
        webhook_url=webhook_url,
        webhook_auth_header_value=webhook_auth
    )

    if not snapshot_id:
        raise Exception("Failed to trigger Bright Data Amazon reviews scrape (no snapshot_id returned).")

    logger.info(f"[{job_id}] Successfully triggered Amazon reviews scrape. Snapshot ID: {snapshot_id}")

    job_info = {
        "job_id": job_id,
        "user_id": user_id,
        "brand_name": brand_name,
        "source_type": "amazon"
    }
    # Store mapping in Redis with a 2-hour expiry
    await redis.hset(f"snapshot_to_job:{snapshot_id}", mapping=job_info)
    await redis.expire(f"snapshot_to_job:{snapshot_id}", 7200)

    logger.info(f"[{job_id}] Saved Amazon scrape job mapping to Redis: snapshot {snapshot_id} to job {job_id}.")

# --- Worker Configuration ---

# This defines the functions our worker knows how to run
functions = [
    func(scrape_trustpilot_task, keep_result=3600, timeout=3600),
    func(scrape_tripadvisor_task, keep_result=3600, timeout=3600),
    func(scrape_druni_task, keep_result=3600, timeout=3600),
    func(scrape_google_task, keep_result=3600, timeout=3600),
    func(search_google_places_task, keep_result=3600, timeout=3600),
    check_and_finalize_job_task,
    trigger_amazon_keyword_discovery_task,
    trigger_manual_product_lookup_task,
    scrape_amazon_task,
    process_amazon_reviews_webhook_task,
]

class WorkerSettings:
    functions = functions
    # You can configure Redis connection here
    redis_settings = arq.connections.RedisSettings.from_dsn(os.getenv("REDIS_URL", "redis://localhost:6379"))
    on_startup = startup
    on_shutdown = shutdown

def separate_urls_and_asins(identifier_string: str) -> Tuple[List[str], List[str]]:
    """
    Separates a comma-delimited string of identifiers into lists of URLs and ASINs.
    """
    urls = []
    asins = []
    
    if not identifier_string:
        return urls, asins

    identifiers = [item.strip() for item in identifier_string.split(',')]
    
    # Regex for a valid Amazon ASIN (B0 followed by 8 alphanumeric chars)
    asin_regex = re.compile(r'\bB0[A-Z0-9]{8}\b', re.IGNORECASE)

    for identifier in identifiers:
        if asin_regex.fullmatch(identifier):
            asins.append(identifier)
        # Basic check for something that looks like a URL
        elif 'https://' in identifier or 'http://' in identifier or '.com' in identifier:
            urls.append(identifier)
        else:
            # For now, we'll assume non-matching, non-URL identifiers could be ASINs
            # if they fit a general pattern, but the regex is more reliable.
            # This part can be enhanced if other identifier types are expected.
            logger.warn(f"Identifier '{identifier}' is not a recognized URL or ASIN format. It will be ignored.")

    return urls, asins

